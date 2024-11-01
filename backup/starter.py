import os
import pickle
import string
import random
import datetime
from tqdm import tqdm
from utils import fast_multiprocessing
from collections import defaultdict
from core.test_function import construct_objects_from_json
from core.chatbot import ChatBot
from data.configuration import code_base, ts_detect_tmp, defects4j_projects_base
from scripts.ts_detect import run_ts_detector
from scripts.llm_utils import construct_few_shot_prompt
from scripts.output_analyser import analyze_outputs
from scripts.d4j_utils import run_d4j_test
from scripts.dependency_analyser import add_dependencies
import time

import logging

# Configure logger
logger = logging.getLogger('current_file_logger')
logger.setLevel(logging.DEBUG)  # 设置日志级别
 
# 创建handler，用于输出到控制台
# console_handler = logging.StreamHandler()
console_handler = logging.FileHandler(f'{code_base}/data/few_shot_math_0729.log')
console_handler.setLevel(logging.DEBUG)
 
# 创建formatter，并添加到handler
formatter = logging.Formatter('[%(asctime)s - %(filename)s - %(funcName)s] - %(message)s')
console_handler.setFormatter(formatter)
 
# 将handler添加到logger
logger.addHandler(console_handler)


def get_checkout_path(project_id, bug_id):
    checkout_path = os.path.join(defects4j_projects_base, f'{project_id}_{str(bug_id)}', 'fixed')
    return checkout_path

def generate_random_string(length):
    characters = string.ascii_letters + string.digits  # 包含大写字母、小写字母和数字
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def detect_smells_multiprocess(all_functions):
    all_smell_dict = defaultdict(int)
    tasks = []
    for single_function in all_functions:
        ts_tmp_dir = os.path.join(ts_detect_tmp, generate_random_string(8))
        tasks.append((single_function, ts_tmp_dir))
    
    processed_data = fast_multiprocessing(run_ts_detector, tasks)
    
    for single_res_dict in processed_data:
        if not single_res_dict['is_success']:
            continue
        all_smell_dict[single_res_dict['func_id']] = single_res_dict['smells']
    return all_smell_dict


def setup_all_base_functions():
    all_base_test_functions = construct_objects_from_json(f'{code_base}/data/task_testgen_filtered.json')
    print(len(all_base_test_functions))
    all_base_test_functions = all_base_test_functions

    all_smell_dict = detect_smells_multiprocess(all_base_test_functions)

    for i in all_base_test_functions:
        i.set_smell_types(all_smell_dict.get(i.function_id, None))
    return all_base_test_functions
    # all_smell_occurance = defaultdict(int)
    # for i in tqdm(all_base_test_functions):
    #     if i.smell_types is None:
    #         continue
    #     for smell_type in i.smell_types:
    #         all_smell_occurance[smell_type] += i.smell_types[smell_type]

    # for smell_type in all_smell_occurance:
    #     print(f'{smell_type}: {all_smell_occurance[smell_type]}')




if __name__ == "__main__":
    api_base = "http://172.28.102.8:6668/v1"
    
    origin_few_shot_res_dir = f'{code_base}/data/origin_few_shot_res'
    os.makedirs(origin_few_shot_res_dir, exist_ok=True)
    
    execution_tmp_dir = f"{code_base}/data/temp_dirs/tmp_execute_tests"
    os.makedirs(execution_tmp_dir, exist_ok=True)
    
    # all_base_test_functions = setup_all_base_functions()
    # with open(f'{code_base}/data/all_base_test_functions.pkl', 'wb') as f:
    #     pickle.dump(all_base_test_functions, f)
    
    with open(f'{code_base}/data/all_base_test_functions.pkl', 'rb') as f:
        all_base_test_functions = pickle.load(f)
        
    logger.debug(f'All basic test functions loaded, total {len(all_base_test_functions)}')
    selected_test_functions = [i for i in all_base_test_functions if i.project_id == 'Math']
    
    logger.debug(f'Selected basic test functions in Math, total {len(selected_test_functions)}')
    
    start_time = time.time()
    for index, single_base_function in enumerate(selected_test_functions):
        logger.debug(f'Processing {single_base_function.function_id}, {index} / {len(selected_test_functions)}')
        
        proj_id = single_base_function.project_id
        bug_id = single_base_function.bug_id
        
        save_dir = os.path.join(origin_few_shot_res_dir, f'{proj_id}_{bug_id}')
        os.makedirs(save_dir, exist_ok=True)
        
        proj_dir = get_checkout_path(proj_id, bug_id)
        
        be_test_classes = list(set([tested_method.be_test_class_name for tested_method in single_base_function.tested_methods]))
        
        origin_test_file = os.path.join(proj_dir, single_base_function.location)
        test_location_dir = os.path.join(proj_dir, '/'.join(single_base_function.location.split('/')[:-1]))
        
        add_dependencies(defects4j_projects_base, f'{proj_id}_{bug_id}')
        
        # construct few-shot test generation prompt
        few_shot_prompt_base = construct_few_shot_prompt(single_base_function)
        chatbot = ChatBot(api_base)
        
        response = chatbot.chat(few_shot_prompt_base)

        # get the generated tests and their coverage
        methods, imports, fields, classes = analyze_outputs(response)
        
        for single_method in list(methods):
            ori_method_content = single_method.split('@_@')[0]
            method_name = single_method.split('@_@')[-1]
            new_method_name = method_name + 'LLM'
            
            method_content = ori_method_content.replace(method_name, new_method_name)
            new_test_class_content = single_base_function.source.replace(single_base_function.function_content, method_content)
            
            tmp_folder = os.path.join(execution_tmp_dir, f'{proj_id}-{bug_id}-{generate_random_string(8)}')
            os.makedirs(tmp_folder, exist_ok=True)
            tmp_test_backup = os.path.join(tmp_folder, 'tmp_test_backup.java')
            os.system(f'cp {origin_test_file} {tmp_test_backup}')
            
            with open(origin_test_file, 'w') as fw:
                fw.write(new_test_class_content)
            test_class = single_base_function.testmethods[0].split('::')[0]
            test_method = test_class + f'::{new_method_name}'
            
            compile_fail, timed_out, bugg, line_coverage, condition_coverage, syntax_error, lines_coverage_info = run_d4j_test(new_test_class_content, test_method, tmp_folder, be_test_classes, proj_dir)

            os.system(f'cp {tmp_test_backup} {origin_test_file}')
            os.system(f'rm -rf {tmp_folder}')
            
            new_test_function = single_base_function.copy_self(function_content=ori_method_content, coverage_info=lines_coverage_info)
            
            new_test_function.set_execution_res(compile_fail, bugg, syntax_error, timed_out, condition_coverage, line_coverage)
            
            single_base_function.add_serve_as_seed_new_function(new_test_function)
        pass
        
        logger.debug(f"{'='*10} {datetime.datetime.now()} {'='*10}")
        logger.debug(f"Finished {single_base_function.function_id}")
        used_time = (time.time() - start_time)
        hour = int(used_time / 3600)
        minute = int((used_time % 3600) / 60)
        second = int(used_time % 60)
        logger.debug(f"Used Time Cost: {hour}h {minute}m {second}s")
        total_time = (time.time() - start_time) / (index+1) * len(selected_test_functions)
        hour = int(total_time / 3600)
        minute = int((total_time % 3600) / 60)
        second = int(total_time % 60)
        logger.debug(f"Total Time Cost: {hour}h {minute}m {second}s")
        with open(os.path.join(save_dir, single_base_function.function_name + '.pkl'), 'wb') as f:
            pickle.dump(single_base_function, f)
        
        # TODO: construct smell repair prompt
        # TODO: construct renaming and comment prompt
        # TODO: get the refined test functions and evaluate the coverage
        # TODO: use the refined test function to construct few-shot prompt again