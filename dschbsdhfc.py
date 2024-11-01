from glob import glob
import json
import pickle
from data.configuration import code_base
import os

all_refined_cases = glob(f'{code_base}/data/d4j_refine_function_2024-08-29/*/*.pkl')

selected_test_functions = [pickle.load(open(i, 'rb')) for i in all_refined_cases]

date = '2024-08-29'
error_info_path = os.path.join(code_base, 'data', f'error_info_refine_{date}.jsonl')
success_info_path = os.path.join(code_base, 'data', f'success_info_refine_{date}.jsonl')

with open(error_info_path, 'w') as f:
    f.write('')
with open(success_info_path, 'w') as f:
    f.write('')
    
for single_base_function in selected_test_functions:
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
    
    for single_refined_test_function in single_base_function.refined_test_functions:
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

# all_refined_cases = glob(f'{code_base}/data/evo_process_refine_seed_gen_res_deepseek/*/*.pkl')

# syntax_err_num = 0
# compiled_num = 0
# total = 0

# eager_test = []
# exception_throwing = []

# refined_caused_compile_error = []
# for h in all_refined_cases:
#     origin_func = pickle.load(open(h, 'rb'))
#     compiled = False
#     syntax_error = False
#     for refined_func in origin_func.refined_test_functions:
        
#         if origin_func.compiled and not refined_func.compiled:
#             refined_caused_compile_error.append((origin_func, refined_func))
        
#         if origin_func.smell_types['Eager Test'] > 0 and refined_func.smell_types['Eager Test'] > 0:
#             eager_test.append((origin_func, refined_func))
            
#         if origin_func.smell_types['Exception Catching Throwing'] > 0 and refined_func.smell_types['Exception Catching Throwing'] > 0:
#             exception_throwing.append((origin_func, refined_func))
        
#         total += 1


# for i in refined_caused_compile_error[-5:]:
#     print(f'// Origin test case, compiled: {i[0].compiled}, passed: {i[0].passed} ')
#     print(i[0].function_content)
#     print()
#     print(f'// Refined test case, compiled: {i[1].compiled}, passed: {i[1].passed} ')
#     print(i[1].function_content)
#     print('=' * 50)
    


# for i in exception_throwing[:5]:
#     print(f'// Origin test case, compiled: {i[0].compiled}, passed: {i[0].passed} ')
#     print(i[0].function_content)
#     print(f'// Refined test case, compiled: {i[1].compiled}, passed: {i[1].passed} ')
#     print(i[1].function_content)
#     print('=' * 50)
    
    
# def find_all_todo_functions(previous_res_dir, current_res_dir):
#     all_projs = glob(previous_res_dir + '/*')
#     todo_functions = []
#     for single_proj in all_projs:
#         proj_id = single_proj.split('/')[-1]
#         all_functions = glob(single_proj + '/*')
#         for single_res in all_functions:
#             base_function = pickle.load(open(single_res, 'rb'))
            
#             todo_functions.append(base_function)
#     return todo_functions
        


# cnt = 0
# if __name__ == "__main__":
#     unzip_output_dir = f'{code_base}/data/evosuite_gen_unzip_0730'
    
#     evo_refine_res_dir = f'{code_base}/data/evo_refine_res'
    
#     evo_refine_seed_gen_res_dir = f'{code_base}/data/evo_refine_seed_gen_res'
#     os.makedirs(evo_refine_seed_gen_res_dir, exist_ok=True)
    
#     base_function_pkl = f'{code_base}/data/all_base_test_functions_evo.pkl'
    
#     # if not os.path.exists(base_function_pkl):
#     #     all_base_test_functions = setup_all_base_functions(base_function_json)
#     #     with open(base_function_pkl, 'wb') as f:
#     #         pickle.dump(all_base_test_functions, f)
    
#     with open(base_function_pkl, 'rb') as f:
#         all_base_test_functions = pickle.load(f)
#     # all_base_test_functions = find_all_todo_functions(evo_refine_res_dir, evo_refine_seed_gen_res_dir)
#     used_smells = {}
#     for single_base_function in all_base_test_functions:
#         proj_id = single_base_function.project_id
#         bug_id = single_base_function.bug_id
        
        
#         if single_base_function.smell_types is not None:
#             for smell_type, occurance in single_base_function.smell_types.items():
#                 if occurance > 0:
#                     if smell_type not in used_smells:
#                         used_smells[smell_type] = 1
#                     else:
#                         used_smells[smell_type] += 1
    
        
#     for smell_type in used_smells:
#         print(f'{smell_type}: {used_smells[smell_type]}')