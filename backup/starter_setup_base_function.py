import os
import pickle
import string
import random
import datetime
from utils import fast_multiprocessing
from collections import defaultdict
from core.test_function import construct_objects_from_json
from data.configuration import code_base, ts_detect_tmp, defects4j_projects_base, execution_tmp_dir
from scripts.ts_detect import run_ts_detector
from scripts.d4j_utils import run_d4j_test
from scripts.dependency_analyser import add_dependencies
import time

import logging

# Configure logger
logger = logging.getLogger('current_file_logger')
logger.setLevel(logging.DEBUG)  # 设置日志级别
 
# 创建handler，用于输出到控制台
# console_handler = logging.StreamHandler()
console_handler = logging.FileHandler(f'{code_base}/data/logs/evo_set_up_base_function.log')
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


def setup_all_base_functions(base_function_cache):
    all_base_test_functions = construct_objects_from_json(base_function_cache)
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
    date = '0730'
    api_base = "http://172.28.102.8:6668/v1"
    unzip_output_dir = f'{code_base}/data/evosuite_gen_unzip_0730'
    
    evo_base_res_dir = f'{code_base}/data/evo_base_function_res'
    os.makedirs(evo_base_res_dir, exist_ok=True)
    
    base_function_json = f'{code_base}/data/task_testgen_filtered_evo.json'
    
    all_base_test_functions = setup_all_base_functions(base_function_json)

    logger.debug(f'All basic test functions loaded, total {len(all_base_test_functions)}')
    selected_test_functions = all_base_test_functions
    
    logger.debug(f'Selected basic test functions, total {len(selected_test_functions)}')
    
    start_time = time.time()
    for cnt_index, single_base_function in enumerate(selected_test_functions):
        logger.debug(f'Processing {single_base_function.function_id}, {cnt_index} / {len(selected_test_functions)}')
        
        proj_id = single_base_function.project_id
        bug_id = single_base_function.bug_id
        
        save_dir = os.path.join(evo_base_res_dir, f'{proj_id}_{bug_id}')
        os.makedirs(save_dir, exist_ok=True)
        
        proj_dir = get_checkout_path(proj_id, bug_id)
        
        add_dependencies(defects4j_projects_base, f'{proj_id}_{bug_id}')
        
        base_test_class_content = single_base_function.assemble_test_file()
        
        test_method = ''
        
        tmp_execution_base = os.path.join(
            execution_tmp_dir, date, f'{proj_id}_{bug_id}', single_base_function.function_name, str(cnt_index)
        )
        os.makedirs(tmp_execution_base, exist_ok=True)

        # 打包测试用例,测试,收集覆盖
        # return compiled, timed_out, passed, syntax_error, coverage_info
        compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage = run_d4j_test(base_test_class_content, proj_id, bug_id, proj_dir, test_method, unzip_output_dir, tmp_execution_base)

        single_base_function.coverage_info = coverage_info
        single_base_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage)
       
        logger.debug(f"{'='*10} {datetime.datetime.now()} {'='*10}")
        logger.debug(f"Finished {single_base_function.function_id}")
        used_time = (time.time() - start_time)
        hour = int(used_time / 3600)
        minute = int((used_time % 3600) / 60)
        second = int(used_time % 60)
        logger.debug(f"Used Time Cost: {hour}h {minute}m {second}s")
        total_time = (time.time() - start_time) / (cnt_index+1) * len(selected_test_functions)
        hour = int(total_time / 3600)
        minute = int((total_time % 3600) / 60)
        second = int(total_time % 60)
        logger.debug(f"Total Time Cost: {hour}h {minute}m {second}s")
        save_path = os.path.join(save_dir, single_base_function.function_name + '.pkl')
        logger.debug(f'Saving at {save_path}')
        with open(save_path, 'wb') as f:
            pickle.dump(single_base_function, f)