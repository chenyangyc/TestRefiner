import json
import os
import pickle
import string
import random
from scripts.assemble_and_execute import assemble_test, delete_test_file, get_method_name, run_test, write_test
from utils import fast_multiprocessing
from collections import defaultdict
from core.test_function import construct_objects_from_json
from data.configuration import code_base, ts_detect_tmp, defects4j_projects_base, execution_tmp_dir
from scripts.ts_detect import run_ts_detector
from scripts.d4j_utils import run_d4j_test
from scripts.dependency_analyser import add_dependencies
import time
import subprocess

import logging


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
    
    all_smell_dict = detect_smells_multiprocess(all_base_test_functions)

    for i in all_base_test_functions:
        i.set_smell_types(all_smell_dict.get(i.function_id, None))
    return all_base_test_functions


def run_one_test_function(single_base_function, base_res_dir):
    proj_id = single_base_function.project_id
    bug_id = single_base_function.bug_id
    
    save_dir = os.path.join(base_res_dir, f'{proj_id}_{bug_id}')
    os.makedirs(save_dir, exist_ok=True)
    
    # 构造一个 tmp dir
    diff_id = generate_random_string(16)
    os.makedirs(execution_tmp_dir, exist_ok=True)
    tmp_execution_base = os.path.join(execution_tmp_dir, date + '_' + single_base_function.function_name)
    os.makedirs(tmp_execution_base, exist_ok=True)

    # get checkout path and add dependency
    proj_dir = os.path.join(tmp_execution_base, f'{proj_id}_{str(bug_id)}', 'fixed')

    if os.path.exists(proj_dir):
        os.system(f'rm -rf {proj_dir}')
    cmd = ['defects4j', 'checkout', '-p', proj_id, '-v', str(bug_id) + 'f', '-w', proj_dir]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    add_dependencies(tmp_execution_base, f'{proj_id}_{bug_id}')
    
    # NOTE:直接利用原本的测试类内容
    be_test_class_long_name = single_base_function.be_test_class_long_name
    test_location = os.path.join(proj_dir, single_base_function.location)
    test_class_content = single_base_function.source
    test_content = single_base_function.function_content
    test_method_signature = single_base_function.testmethods[0]

    # NOTE: return compiled, timed_out, passed, syntax_error, coverage_info, other output
    compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(test_class_content, proj_dir, test_method_signature, be_test_class_long_name)
    
    single_base_function.coverage_info = coverage_info
    single_base_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage, error_result, test_method_signature)

    for single_splitted_test_content in single_base_function.splitted_test_function_contents:
        # 构造新的测试类的内容
        add_test_content = single_splitted_test_content
        add_method_name = get_method_name(add_test_content)
        new_test_method_signature, new_test_location, new_test_content = assemble_test(test_location, test_method_signature, test_class_content, test_content, add_test_content, add_method_name, diff_id)
        write_test(new_test_content, test_location)

        # 进行测试，return compiled, timed_out, passed, syntax_error, coverage_info, other output
        compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(new_test_content, proj_dir, new_test_method_signature, be_test_class_long_name)
        
        delete_test_file(new_test_location)
        
        with open(test_location, 'w') as f:
            f.write(test_class_content)

        new_test_function = single_base_function.copy_self(function_content=single_splitted_test_content, coverage_info=coverage_info)
        new_test_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage, error_result, new_test_method_signature)
        
        single_base_function.add_split_test_function(new_test_function)
    
    save_path = os.path.join(save_dir, single_base_function.function_name + '.pkl')
    logger.debug(f'Saving at {save_path}')
    with open(save_path, 'wb') as f:
        pickle.dump(single_base_function, f)
    return single_base_function


if __name__ == "__main__":
    # get current date using time
    date = time.strftime("%Y-%m-%d", time.localtime())
    
    log_file = f'{code_base}/data/logs/set_up_base_function_d4j_{date}_test.log'
    if os.path.exists(log_file):
        os.system(f'rm -rf {log_file}')
    
    base_res_dir = f'{code_base}/data/d4j_base_function_{date}_test'
    if os.path.exists(base_res_dir):
        os.system(f'rm -rf {base_res_dir}')
    os.makedirs(base_res_dir, exist_ok=True)
    
    if os.path.exists(execution_tmp_dir):
        os.system(f'rm -rf {execution_tmp_dir}')
    os.makedirs(execution_tmp_dir, exist_ok=True)
    
    base_function_json = f'{code_base}/data/split_d4j_tests_filtered.json'
    all_base_test_functions = setup_all_base_functions(base_function_json)

    # Configure logger
    logger = logging.getLogger('current_file_logger')
    logger.setLevel(logging.DEBUG)  # 设置日志级别
    
    # 创建handler，用于输出到控制台
    # console_handler = logging.StreamHandler()
    console_handler = logging.FileHandler(log_file)
    console_handler.setLevel(logging.DEBUG)
    
    # 创建formatter，并添加到handler
    formatter = logging.Formatter('[%(asctime)s - %(filename)s - %(funcName)s] - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 将handler添加到logger
    logger.addHandler(console_handler)

    logger.debug(f'All basic test functions loaded, total {len(all_base_test_functions)}')
    selected_test_functions = all_base_test_functions
    
    logger.debug(f'Selected basic test functions, total {len(selected_test_functions)}')
    
    start_time = time.time()
    
    tasks = []
    for single_base_function in selected_test_functions:
        tasks.append((single_base_function, base_res_dir))
    workers = 60
    
    logger.debug(f'Parallel processing with {workers} workers')
    processed_data = fast_multiprocessing(run_one_test_function, tasks, max_workers=workers)
    
    error_info_path = os.path.join(code_base, 'data', f'error_info_base_{date}_test.jsonl')
    success_info_path = os.path.join(code_base, 'data', f'success_info_base_{date}_test.jsonl')
    
    with open(error_info_path, 'w') as f:
        f.write('')
    with open(success_info_path, 'w') as f:
        f.write('')
    
    for single_base_function in processed_data:
        error_result = single_base_function.error_result
        if error_result['error_type'] is not None:
            with open(error_info_path, 'a') as f:
                json.dump(error_result, f)
                f.write('\n')
        else:
            with open(success_info_path, 'a') as f:
                result = {'compile': single_base_function.compiled, 'timed_out': single_base_function.timeout, 'passed': single_base_function.passed, 'syntax_error': single_base_function.syntax_error, 'test_signature': single_base_function.test_method_signature}
                json.dump(result, f)
                f.write('\n')
        
        for single_refined_test_function in single_base_function.splitted_test_functions:
            error_result = single_refined_test_function.error_result
            if error_result['error_type'] is not None:
                with open(error_info_path, 'a') as f:
                    json.dump(error_result, f)
                    f.write('\n')
            else:
                with open(success_info_path, 'a') as f:
                    result = {'compile': single_refined_test_function.compiled, 'timed_out': single_refined_test_function.timeout, 'passed': single_refined_test_function.passed, 'syntax_error': single_refined_test_function.syntax_error, 'test_signature': single_refined_test_function.test_method_signature}
                    json.dump(result, f)
                    f.write('\n')

    # error_info_path = os.path.join(code_base, 'data', 'error_info.jsonl')
    # success_info_path = os.path.join(code_base, 'data', 'success_info.jsonl')
    # for cnt_index, single_base_function in enumerate(selected_test_functions):
    #     logger.debug(f'Processing {single_base_function.function_id}, {cnt_index} / {len(selected_test_functions)}')
        
    #     proj_id = single_base_function.project_id
    #     bug_id = single_base_function.bug_id
        
    #     save_dir = os.path.join(evo_base_res_dir, f'{proj_id}_{bug_id}')
    #     os.makedirs(save_dir, exist_ok=True)
        
    #     # 构造一个 tmp dir
    #     diff_id = generate_random_string(16)
    #     tmp_execution_base = os.path.join(execution_tmp_dir, date + '_' + diff_id)
    #     os.makedirs(tmp_execution_base, exist_ok=True)

    #     # get checkout path and add dependency
    #     proj_dir =os.path.join(tmp_execution_base, f'{proj_id}_{str(bug_id)}', 'fixed')

    #     if not os.path.exists(proj_dir):
    #         cmd = ['defects4j', 'checkout', '-p', proj_id, '-v', str(bug_id) + 'f', '-w', proj_dir]
    #         subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    #     add_dependencies(tmp_execution_base, f'{proj_id}_{bug_id}')
        
    #     # NOTE:直接利用原本的测试类内容
    #     test_location = os.path.join(proj_dir, single_base_function.location)
    #     test_class_content = single_base_function.source
    #     test_content = single_base_function.function_content
    #     test_method_signature = single_base_function.testmethods[0]

    #     # NOTE: return compiled, timed_out, passed, syntax_error, coverage_info, other output
    #     compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(test_class_content, proj_dir,test_method_signature)
        
    #     if error_result['error_type'] is not None:
    #         with open(error_info_path, 'a') as f:
    #             json.dump(error_result, f)
    #             f.write('\n')
    #     else:
    #         with open(success_info_path, 'a') as f:
    #             result = {'compile': compiled, 'timed_out': timed_out, 'passed': passed, 'syntax_error': syntax_error, 'test_signature': test_method_signature}
    #             json.dump(result, f)
    #             f.write('\n')

    #     single_base_function.coverage_info = coverage_info
    #     single_base_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage)


    #     for single_refined_test_content in single_base_function.refined_test_function_contents:
    #         # 构造新的测试类的内容
    #         add_test_content = single_refined_test_content
    #         add_method_name = get_method_name(add_test_content)
    #         new_test_method_signature, new_test_location, new_test_content = assemble_test(test_location, test_method_signature, test_class_content, test_content, add_test_content, add_method_name, diff_id)
    #         write_test(new_test_content, new_test_location)

    #         # 进行测试，return compiled, timed_out, passed, syntax_error, coverage_info, other output
    #         compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(new_test_content, proj_dir,new_test_method_signature)
            
    #         delete_test_file(new_test_location)
            
    #         if error_result['error_type'] is not None:
    #             with open(error_info_path, 'a') as f:
    #                 json.dump(error_result, f)
    #                 f.write('\n')
    #         else:
    #             with open(success_info_path, 'a') as f:
    #                 result = {'compile': compiled, 'timed_out': timed_out, 'passed': passed, 'syntax_error': syntax_error, 'test_signature': new_test_method_signature}
    #                 json.dump(result, f)
    #                 f.write('\n')

    #         new_test_function = single_base_function.copy_self(function_content=single_refined_test_content, coverage_info=coverage_info)
    #         new_test_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage)
    #         single_base_function.add_refined_test_function(new_test_function)
        

    #     logger.debug(f"{'='*10} {datetime.datetime.now()} {'='*10}")
    #     logger.debug(f"Finished {single_base_function.function_id}")
    #     used_time = (time.time() - start_time)
    #     hour = int(used_time / 3600)
    #     minute = int((used_time % 3600) / 60)
    #     second = int(used_time % 60)
    #     logger.debug(f"Used Time Cost: {hour}h {minute}m {second}s")
    #     total_time = (time.time() - start_time) / (cnt_index+1) * len(selected_test_functions)
    #     hour = int(total_time / 3600)
    #     minute = int((total_time % 3600) / 60)
    #     second = int(total_time % 60)
    #     logger.debug(f"Total Time Cost: {hour}h {minute}m {second}s")
        
    #     save_path = os.path.join(save_dir, single_base_function.function_name + '.pkl')
    #     logger.debug(f'Saving at {save_path}')
    #     with open(save_path, 'wb') as f:
    #         pickle.dump(single_base_function, f)