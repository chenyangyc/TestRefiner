
from collections import defaultdict
import json
from scripts.output_analyser import analyze_outputs
import json
import os
import pickle
import string
import random
from tqdm import tqdm
from glob import glob
from scripts.assemble_and_execute import assemble_test, delete_test_file, get_method_name, run_test, write_test
from utils import fast_multiprocessing
from collections import defaultdict
from core.test_function import construct_objects_from_json
from data.configuration import code_base, ts_detect_tmp, defects4j_projects_base, execution_tmp_dir, parser
from scripts.ts_detect import run_ts_detector
from scripts.dependency_analyser import add_dependencies
import time
import subprocess

import logging

# def get_method_name(method_content):
#     method_node = parser.parse(bytes(method_content, "utf8")).root_node
#     method_name = method_name_query.captures(method_node)[0][0].text.decode()
#     return method_name


def assembling_test_class(response_data, method_test_dict, method_response_dict):
    focal_method_content = response_data['focal_method_content']
    prompt = response_data['prompt']
    response = response_data['completion']
    # response = response.replace('\n', '')
    response = response.replace('<|EOT|>', '')
    response_lines = response.split('\n')
    response_lines = [line for line in response_lines if line.strip() != '']
    response = '\n'.join(response_lines)
    
    methods, imports, fields, classes = analyze_outputs(response)
    # methods = [method.split('@_@')[0] for method in methods if 'test' in get_method_name(method)]   
    methods = [method.split('@_@')[0] for method in methods]
    method_test_dict[focal_method_content].extend(methods)
    method_response_dict[focal_method_content] = response
    return method_test_dict, method_response_dict

def read_jsonl(file_path):
    data_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 解析每一行成字典，并添加到列表中
            data_dict = json.loads(line)
            data_list.append(data_dict)
    return data_list

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

    # # NOTE: return compiled, timed_out, passed, syntax_error, coverage_info, other output
    # compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(test_class_content, proj_dir, test_method_signature)
    
    # single_base_function.coverage_info = coverage_info
    # single_base_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage, error_result, test_method_signature)
    for single_refined_test_function in single_base_function.gen_from_refined_test_contents:
        # 构造新的测试类的内容
        add_test_content = single_refined_test_function
        add_method_name = get_method_name(add_test_content)
        new_test_method_signature, new_test_location, new_test_content = assemble_test(test_location, test_method_signature, test_class_content, test_content, add_test_content, add_method_name, diff_id, be_test_class_long_name)
        # new_test_content = test_class_content.replace(test_content, new_test_content)
        write_test(new_test_content, test_location)

        # 进行测试，return compiled, timed_out, passed, syntax_error, coverage_info, other output
        compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(new_test_content, proj_dir, new_test_method_signature, be_test_class_long_name)
        
        delete_test_file(new_test_location)
        
        with open(test_location, 'w') as f:
            f.write(test_class_content)

        new_test_function = single_base_function.copy_self(function_content=add_test_content, coverage_info=coverage_info)
        new_test_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage, error_result, new_test_method_signature)
        
        # NOTE: 加入refine
        single_base_function.add_rag_serve_as_seed_new_function(new_test_function)
    
    gen_from_origin_test_contents = single_base_function.gen_from_origin_test_contents
    for single_test_content in gen_from_origin_test_contents:
        # 构造新的测试类的内容
        add_test_content = single_test_content
        add_method_name = get_method_name(add_test_content)
        new_test_method_signature, new_test_location, new_test_content = assemble_test(test_location, test_method_signature, test_class_content, test_content, add_test_content, add_method_name, diff_id, be_test_class_long_name)
        # new_test_content = test_class_content.replace(test_content, new_test_content)
        write_test(new_test_content, test_location)

        # 进行测试，return compiled, timed_out, passed, syntax_error, coverage_info, other output
        compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(new_test_content, proj_dir, new_test_method_signature, be_test_class_long_name)
        
        delete_test_file(new_test_location)
        
        with open(test_location, 'w') as f:
            f.write(test_class_content)

        new_test_function = single_base_function.copy_self(function_content=add_test_content, coverage_info=coverage_info)
        new_test_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage, error_result, new_test_method_signature)
        
        # NOTE: 加入base
        single_base_function.add_serve_as_seed_new_function(new_test_function)
    
    save_path = os.path.join(save_dir, single_base_function.function_name + '.pkl')
    logger.debug(f'Saving at {save_path}')
    with open(save_path, 'wb') as f:
        pickle.dump(single_base_function, f)
    return single_base_function


if __name__ == '__main__':
    # data = read_jsonl('/test_refine/vllm_reference/all_rag_gen_base_output_2024-09-04-2.jsonl')
    # data = read_jsonl('/test_refine/vllm_reference/CodeLlama-7b-Instruct-hf_all_rag_gen_base_output_2024-09-05-code_llama.jsonl')
    # data = read_jsonl('/test_refine/vllm_reference/CodeLlama-13b-Instruct-hf_all_rag_gen_base_output_2024-09-06-code_llama_13b.jsonl')
    # data = read_jsonl('/test_refine/vllm_reference/deepseek-coder-33b-instruct_all_rag_gen_base_output_2024-09-04-2.jsonl')
    # data = read_jsonl('/test_refine/vllm_reference/Phind-CodeLlama-34B-v2_all_rag_gen_base_output_2024-09-06-phind.jsonl')
    data = read_jsonl('/test_refine/vllm_reference/CodeLlama-34b-Instruct-hf_all_rag_gen_base_output_2024-09-04-2.jsonl')
    
    
    # data = read_jsonl('/test_refine/vllm_reference/all_rag_gen_base_output.jsonl')
    
    base_method_test_dict = defaultdict(list)
    base_method_response_dict = defaultdict(str)
    for response_data in data:
        base_method_test_dict, base_method_response_dict = assembling_test_class(response_data, base_method_test_dict, base_method_response_dict)
    
    # refine_data = read_jsonl('/test_refine/vllm_reference/all_rag_gen_refine_output_2024-09-04-2.jsonl')
    # refine_data = read_jsonl('/test_refine/vllm_reference/CodeLlama-7b-Instruct-hf_all_rag_gen_refine_output_2024-09-05-code_llama.jsonl')
    # refine_data = read_jsonl('/test_refine/vllm_reference/CodeLlama-13b-Instruct-hf_all_rag_gen_refine_output_2024-09-06-code_llama_13b.jsonl')
    # refine_data = read_jsonl('/test_refine/vllm_reference/deepseek-coder-33b-instruct_all_rag_gen_refine_output_2024-09-04-2.jsonl')
    # refine_data = read_jsonl('/test_refine/vllm_reference/Phind-CodeLlama-34B-v2_all_rag_gen_refine_output_2024-09-06-phind.jsonl')
    refine_data = read_jsonl('/test_refine/vllm_reference/CodeLlama-34b-Instruct-hf_all_rag_gen_refine_output_2024-09-04-2.jsonl')
    
    # refine_data = read_jsonl('/test_refine/vllm_reference/all_rag_gen_refine_output.jsonl')
    refine_method_test_dict = defaultdict(list)
    refine_method_response_dict = defaultdict(str)
    for response_data in refine_data:
        refine_method_test_dict, refine_method_response_dict = assembling_test_class(response_data, refine_method_test_dict, refine_method_response_dict)
    
    # get current date using time
    date = time.strftime("%Y-%m-%d", time.localtime())
    date = date + '-codellama-34b'
    
    all_cases = glob(f'{code_base}/data/d4j_refine_function_2024-09-04/*/*.pkl')
    
    log_file = f'{code_base}/data/logs/set_up_rag_function_d4j_{date}.log'
    
    base_res_dir = f'{code_base}/data/d4j_rag_function_{date}'
    
    all_base_test_functions = [pickle.load(open(i, 'rb')) for i in all_cases]
    
    selected_test_functions = all_base_test_functions
    tasks = []
    processed_task_focal = set()
    for single_base_function in tqdm(selected_test_functions):
        focal_content = single_base_function.focal_method.method_content
        if focal_content in processed_task_focal:
            continue
        single_base_function.gen_from_origin_response = base_method_response_dict[focal_content]
        single_base_function.gen_from_origin_test_contents = base_method_test_dict[focal_content]
        single_base_function.gen_from_refined_response = refine_method_response_dict[focal_content]
        single_base_function.gen_from_refined_test_contents = refine_method_test_dict[focal_content]
        tasks.append((single_base_function, base_res_dir))
        processed_task_focal.add(focal_content)
    
    workers = 60

    if os.path.exists(log_file):
        os.system(f'rm -rf {log_file}')
        
    if os.path.exists(base_res_dir):
        os.system(f'rm -rf {base_res_dir}')
    os.makedirs(base_res_dir, exist_ok=True)
    
    if os.path.exists(execution_tmp_dir):
        os.system(f'rm -rf {execution_tmp_dir}')
    os.makedirs(execution_tmp_dir, exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger('current_file_logger')
    logger.setLevel(logging.DEBUG)  # 设置日志级别
    console_handler = logging.FileHandler(log_file)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s - %(filename)s - %(funcName)s] - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.debug(f'All basic test functions loaded, total {len(all_base_test_functions)}')
    logger.debug(f'All tasks {len(tasks)}')

    start_time = time.time()
    
    # for task in tasks:
    #     run_one_test_function(task[0], task[1])
    #     break
    # exit()
    logger.debug(f'Parallel processing with {workers} workers')
    processed_data = fast_multiprocessing(run_one_test_function, tasks, max_workers=workers)
    
    base_error_info_path = os.path.join(code_base, 'data', f'error_info_base_rag_{date}.jsonl')
    refine_error_info_path = os.path.join(code_base, 'data', f'error_info_refine_rag_{date}.jsonl')
    success_info_path = os.path.join(code_base, 'data', f'success_info_rag_{date}.jsonl')
    
    with open(base_error_info_path, 'w') as f:
        f.write('')
    with open(refine_error_info_path, 'w') as f:
        f.write('')
    with open(success_info_path, 'w') as f:
        f.write('')
    
    for single_base_function in processed_data:
        for single_refined_test_function in single_base_function.serve_as_seed_new_functions:
            error_result = single_refined_test_function.error_result
            if error_result['error_type'] is not None:
                with open(base_error_info_path, 'a') as f:
                    json.dump(error_result, f)
                    f.write('\n')
            else:
                with open(success_info_path, 'a') as f:
                    result = {'compile': single_refined_test_function.compiled, 'timed_out': single_refined_test_function.timeout, 'passed': single_refined_test_function.passed, 'syntax_error': single_refined_test_function.syntax_error, 'test_signature': single_refined_test_function.test_method_signature}
                    json.dump(result, f)
                    f.write('\n')

        
        for single_refined_test_function in single_base_function.rag_serve_as_seed_new_functions:
            error_result = single_refined_test_function.error_result
            if error_result['error_type'] is not None:
                with open(refine_error_info_path, 'a') as f:
                    json.dump(error_result, f)
                    f.write('\n')
            else:
                with open(success_info_path, 'a') as f:
                    result = {'compile': single_refined_test_function.compiled, 'timed_out': single_refined_test_function.timeout, 'passed': single_refined_test_function.passed, 'syntax_error': single_refined_test_function.syntax_error, 'test_signature': single_refined_test_function.test_method_signature}
                    json.dump(result, f)
                    f.write('\n')
