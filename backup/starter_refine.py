import os
import pickle
import string
import random
import datetime
from glob import glob
from core.refine_codebot import ChatBot
from data.configuration import code_base, defects4j_projects_base, refine_tmp_dir, ts_detect_tmp
from scripts.llm_utils import construct_refine_prompt
from scripts.output_analyser import analyze_outputs
from scripts.d4j_utils import run_d4j_test
from scripts.ts_detect import run_ts_detector
from scripts.dependency_analyser import add_dependencies
import time

import logging

# Configure logger
logger = logging.getLogger('current_file_logger')
logger.setLevel(logging.DEBUG)  # 设置日志级别
 
# 创建handler，用于输出到控制台
# console_handler = logging.StreamHandler()
console_handler = logging.FileHandler(f'{code_base}/data/logs/evo_refine_deepseek.log')
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
    api_base = "https://api.deepseek.com/v1"
    date = '0730'

    unzip_output_dir = f'{code_base}/data/evosuite_gen_unzip_0730'
    
    evo_few_shot_res_dir = f'{code_base}/data/evo_few_shot_res'
    
    evo_refine_res_dir = f'{code_base}/data/evo_refine_res_deepseek'
    os.makedirs(evo_refine_res_dir, exist_ok=True)
    
    # base_function_pkl = f'{code_base}/data/all_base_test_functions_evo.pkl'

    # assert os.path.exists(base_function_pkl), f'{base_function_pkl} not exists.'
    
    # with open(base_function_pkl, 'rb') as f:
    #     all_base_test_functions = pickle.load(f)
    
    all_base_test_functions = find_all_todo_functions(evo_few_shot_res_dir, evo_refine_res_dir)
    
    logger.debug(f'All basic test functions loaded, total {len(all_base_test_functions)}')
    selected_test_functions = [i for i in all_base_test_functions]
    
    logger.debug(f'Selected basic test functions, total {len(selected_test_functions)}')

    start_time = time.time()
    
    for cnt_index, single_base_function in enumerate(selected_test_functions):
        logger.debug(f'Processing {single_base_function.function_id}, {cnt_index} / {len(selected_test_functions)}')
 
        proj_id = single_base_function.project_id
        bug_id = single_base_function.bug_id
        
        save_dir = os.path.join(evo_refine_res_dir, f'{proj_id}_{bug_id}')
        os.makedirs(save_dir, exist_ok=True)
        
        proj_dir = get_checkout_path(proj_id, bug_id)
        
        add_dependencies(defects4j_projects_base, f'{proj_id}_{bug_id}')
        
        # construct few-shot test generation prompt
        refine_prompt_base = construct_refine_prompt(single_base_function)
        chatbot = ChatBot(api_base)
        
        logger.debug(f'Invoking the LLM...')
        
        response = chatbot.chat(refine_prompt_base)
        # response = ''
        
        logger.debug(f'Get the response, executing tests...')
        # get the generated tests and their coverage
        methods, imports, fields, classes = analyze_outputs(response)
        
        candidate_test_file_content = single_base_function.assemble_test_file()
#         methods = ["""
# @Test(timeout = 4000)
#   public void test06()  throws Throwable  {
#       CategoryAxis categoryAxis0 = new CategoryAxis();
#       categoryAxis0.setTickMarkOutsideLength(10);
#       assertEquals(10.0F, categoryAxis0.getTickMarkOutsideLength(), 0.01F);
#   }@_@test06
# """,
# """
#   @Test(timeout = 4000)
#   public void test08()  throws Throwable  {
#       CyclicNumberAxis cyclicNumberAxis0 = new CyclicNumberAxis(392.91651, "YX");
#       cyclicNumberAxis0.setLabelToolTip("YX");
#       assertTrue(cyclicNumberAxis0.isTickLabelsVisible());
#       assertTrue(cyclicNumberAxis0.isVisible());
#       assertTrue(cyclicNumberAxis0.isTickMarksVisible());
#       assertEquals(0.0, cyclicNumberAxis0.getLabelAngle(), 0.01);
#       assertEquals(0.0F, cyclicNumberAxis0.getTickMarkInsideLength(), 0.01F);
#       assertEquals(2.0F, cyclicNumberAxis0.getTickMarkOutsideLength(), 0.01F);
#       assertTrue(cyclicNumberAxis0.isAxisLineVisible());
#   }@_@test08
# """
# ]
        logger.debug(f'{len(methods)} methods generated.')
        for index, single_method in enumerate(list(methods)):
            
            method_content = single_method.split('@_@')[0]
            method_name = single_method.split('@_@')[-1]
            
            new_test_class_content = candidate_test_file_content.replace(single_base_function.function_content, method_content)
            
            test_class = single_base_function.testmethods[0].split('::')[0]
            test_method = test_class + f'::{method_name}'
            
            tmp_execution_base = os.path.join(
                refine_tmp_dir, date, f'{proj_id}_{bug_id}', single_base_function.function_name, str(index)
            )
            os.makedirs(tmp_execution_base, exist_ok=True)

            # 打包测试用例,测试,收集覆盖
            # return compiled, timed_out, passed, syntax_error, coverage_info
            compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage = run_d4j_test(new_test_class_content, proj_id, bug_id, proj_dir, test_method, unzip_output_dir, tmp_execution_base)

            logger.debug(f"{index}-th refined test case compiled: {compiled}, passed: {passed}")
            
            new_test_function = single_base_function.copy_self(function_content=method_content, coverage_info=coverage_info)
            
            new_test_function.set_execution_res(compiled, passed, syntax_error, timed_out, line_coverage, condition_coverage)
            
            single_base_function.add_refined_test_function(new_test_function)
            
            ts_tmp_dir = os.path.join(ts_detect_tmp, generate_random_string(8))
            ts_detec_res = run_ts_detector(new_test_function, ts_tmp_dir)
            
            if ts_detec_res['is_success']:
                new_test_function.set_smell_types(ts_detec_res['smells'])
        
        pass
        
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
        
        # TODO: construct smell repair prompt
        # TODO: construct renaming and comment prompt
        # TODO: get the refined test functions and evaluate the coverage
        # TODO: use the refined test function to construct few-shot prompt again