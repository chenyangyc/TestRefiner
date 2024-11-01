import os
import pickle
import string
import random
import datetime
from tqdm import tqdm
from glob import glob
from utils import fast_multiprocessing
from collections import defaultdict
from core.test_function import construct_objects_from_json
from core.chatbot import ChatBot
from data.configuration import code_base, ts_detect_tmp, defects4j_projects_base, process_function_tmp_dir
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
console_handler = logging.FileHandler(f'{code_base}/data/logs/evo_process_function_res_0815.log')
console_handler.setLevel(logging.DEBUG)
 
# 创建formatter，并添加到handler
formatter = logging.Formatter('[%(asctime)s - %(filename)s - %(funcName)s] - %(message)s')
console_handler.setFormatter(formatter)
 
# 将handler添加到logge
logger.addHandler(console_handler)


def get_checkout_path(project_id, bug_id):
    checkout_path = os.path.join(defects4j_projects_base, f'{project_id}_{str(bug_id)}', 'fixed')
    return checkout_path

def generate_random_string(length):
    characters = string.ascii_letters + string.digits  # 包含大写字母、小写字母和数字
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def find_all_todo_functions(previous_res_dir, current_res_dir):
    all_projs = glob(previous_res_dir + '/*')
    todo_functions = []
    for single_proj in all_projs:
        proj_id = single_proj.split('/')[-1]
        all_functions = glob(single_proj + '/*')
        for single_res in all_functions:
            func_name = single_res.split('/')[-1]
            base_function = pickle.load(open(single_res, 'rb'))
            
            if not os.path.exists(os.path.join(current_res_dir, proj_id, func_name)):
                todo_functions.append(base_function)
    return todo_functions
        


if __name__ == "__main__":
    date = '0730'
    unzip_output_dir = f'{code_base}/data/evosuite_gen_unzip_0730'
    
    evo_refine_seed_gen_res_dir = f'{code_base}/data/evo_refine_seed_gen_res_deepseek'
    
    evo_process_function_res_dir = f'{code_base}/data/evo_process_refine_seed_gen_res_deepseek'
    os.makedirs(evo_process_function_res_dir, exist_ok=True)
    
    all_base_test_functions = find_all_todo_functions(evo_refine_seed_gen_res_dir, evo_process_function_res_dir)

    logger.debug(f'All basic test functions loaded, total {len(all_base_test_functions)}')
    selected_test_functions = all_base_test_functions
    
    logger.debug(f'Selected basic test functions, total {len(selected_test_functions)}')
    
    start_time = time.time()
    for index, single_base_function in enumerate(selected_test_functions):
        logger.debug(f'Processing {single_base_function.function_id}, {index} / {len(selected_test_functions)}')
        
        proj_id = single_base_function.project_id
        bug_id = single_base_function.bug_id
        
        save_dir = os.path.join(evo_process_function_res_dir, f'{proj_id}_{bug_id}')
        os.makedirs(save_dir, exist_ok=True)
        
        # previously_processed_base = os.path.join(code_base, 'data/evo_process_function_res', f'{proj_id}_{bug_id}', single_base_function.function_id.split('|')[-3] + '.pkl')
        
        # with open(previously_processed_base, 'rb') as fr:
        #     previous_processed_func = pickle.load(fr)
        
        # compiled = previous_processed_func.compiled
        # passed = previous_processed_func.passed
        # syntax_error = previous_processed_func.syntax_error
        # timed_out = previous_processed_func.timed_out
        # line_coverage = previous_processed_func.line_coverage
        # condition_coverage = previous_processed_func.condition_coverage
        
        # single_base_function.coverage_info = previous_processed_func.coverage_info
        # single_base_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage)
        
        proj_dir = get_checkout_path(proj_id, bug_id)
        
        add_dependencies(defects4j_projects_base, f'{proj_id}_{bug_id}')

        new_test_class_content = single_base_function.assemble_test_file()
        
        test_method = ''
        
        tmp_execution_base = os.path.join(
            process_function_tmp_dir, date, f'{proj_id}_{bug_id}', single_base_function.function_name, str(index)
        )
        os.makedirs(tmp_execution_base, exist_ok=True)

        # 打包测试用例,测试,收集覆盖
        # return compiled, timed_out, passed, syntax_error, coverage_info
        compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage = run_d4j_test(new_test_class_content, proj_id, bug_id, proj_dir, test_method, unzip_output_dir, tmp_execution_base)

        single_base_function.coverage_info = coverage_info
        single_base_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage)
        
        for refined_function in single_base_function.refined_test_functions:
            ts_tmp_dir = os.path.join(ts_detect_tmp, generate_random_string(8))
            ts_detec_res = run_ts_detector(refined_function, ts_tmp_dir)
            
            if ts_detec_res['is_success']:
                refined_function.set_smell_types(ts_detec_res['smells'])
        
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
        save_path = os.path.join(save_dir, single_base_function.function_name + '.pkl')
        logger.debug(f'Saving at {save_path}')
        with open(save_path, 'wb') as f:
            pickle.dump(single_base_function, f)
        
        # TODO: construct smell repair prompt
        # TODO: construct renaming and comment prompt
        # TODO: get the refined test functions and evaluate the coverage
        # TODO: use the refined test function to construct few-shot prompt again