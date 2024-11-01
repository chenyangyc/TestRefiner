
from collections import defaultdict
from glob import glob
import json
import os
import pickle
import subprocess
from tree_sitter import Language, Parser
import tree_sitter_java as tsjava
from data.configuration import code_base

from run_coverage import process_cov_info

JAVA_LANGUAGE = Language(tsjava.language(), name='java')
parser = Parser()
# new tree-sitter parser
# parser.language = JAVA_LANGUAGE
# old tree-sitter parser
parser.set_language(JAVA_LANGUAGE)

method_declaration_text = '''
(method_declaration 
    name:(_)@name
)@method_declaration
'''
method_declaration_query = JAVA_LANGUAGE.query(method_declaration_text)

def get_test_content(test_class_content, test_method_name):
    root = parser.parse(bytes(test_class_content, "utf8")).root_node
    method_declaration = method_declaration_query.captures(root)
    for i in range(0, len(method_declaration), 2):
        name = method_declaration[i + 1][0].text.decode()
        if name == test_method_name:
            return method_declaration[i][0].text.decode()
    return None


def get_prompt_use_focal_methoid(single_base_function, proptm_info):
    return proptm_info[single_base_function.focal_method.method_content]['prompt']

def get_output_use_focal_method(single_base_function, prompt_info):
    return prompt_info[single_base_function.focal_method.method_content]['output']

def get_error_info(single_base_function, prompt_info):
    error_info = {
        'bug_id': single_base_function.project_id + '_' + single_base_function.bug_id,
        'function_name': single_base_function.function_name,
        'focal_method': single_base_function.focal_method.method_content,
        'prompt': get_prompt_use_focal_methoid(single_base_function, prompt_info),
        'output': get_output_use_focal_method(single_base_function, prompt_info),
        'rag_tests': [],
        'base_tests': [],
    }
    for rag_test in single_base_function.rag_serve_as_seed_new_functions:
        error_info['rag_tests'].append({
            'function_content': rag_test.function_content,
            'error_type': rag_test.error_result['error_type'],
            'error_output': rag_test.error_result['error_output'],
        })
    for base_test in single_base_function.serve_as_seed_new_functions:
        error_info['base_tests'].append({
            'function_content': base_test.function_content,
            'error_type': base_test.error_result['error_type'],
            'error_output': base_test.error_result['error_output'],
        })
    
    return error_info

def count_refine_effectiveness(res_dir, prompt_info):
    all_projs = glob(res_dir + '/*')
    error_result = []
    for single_proj in all_projs:
        proj_name = single_proj.split('/')[-1]
        all_functions = glob(single_proj + '/*')
        
        for single_func in all_functions:
            single_base_function = pickle.load(open(single_func, 'rb'))
            single_base_compiled = []
            single_refine_compiled = []
            single_base_passed = []
            single_refine_passed = []
            
            if single_base_function.coverage_info is None:
                continue
            
            refined_functions = single_base_function.refined_test_functions
            if not refined_functions:
                continue
            
            if not single_base_function.rag_serve_as_seed_new_functions:
                continue
            
            focal_method_content = single_base_function.focal_method.method_content
            
            # refine之前的test作为prompt
            for one_origin_rag_test in single_base_function.serve_as_seed_new_functions:
                single_base_compiled.append(one_origin_rag_test.compiled)
                single_base_passed.append(one_origin_rag_test.passed)
                
            # refine之后的test作为prompt生成的test
            for one_refined_rag_test in single_base_function.rag_serve_as_seed_new_functions:
                single_refine_compiled.append(one_refined_rag_test.compiled)
                single_refine_passed.append(one_refined_rag_test.passed)
                
            # NOTE： 这里统计 base compile了，但是refine没有compile的case
            if all(single_base_compiled) and not all(single_refine_compiled):
                error_info = get_error_info(single_base_function, prompt_info)
                error_result.append(error_info)
        
    return error_result

def get_origin_and_splited_test_content():
    '''处理拆分出错的代码，获取拆分前和拆分后的部分'''
    code_base = os.path.dirname(__file__)
    json_path = os.path.join(code_base, 'data', 'error_info_base_2024-09-02_test.jsonl')
    error_datas = []
    with open(json_path, 'r') as f:
        for line in f:
            error_datas.append(json.loads(line))
    
    project_test = {}
    sp_path = '/test_refine/data/split_d4j_tests_filtered.json'
    with open(sp_path, 'r') as fr:
        datas = json.load(fr)
    for data in datas:
        project_id = data['project_id']
        project_test[project_id] = data['source_dir']
    result = []
    for error_data in error_datas:
        project_dir = error_data['project_dir']
        test_method_signature = error_data['test_method_signature']
        test_class_path = test_method_signature.split('::')[0].replace('.', os.sep) + '.java'
        test_method_name = test_method_signature.split('::')[1]
        project_id = project_dir.split('/')[-2].split('_')[0]
        origin_method_name = test_method_name.split('_split')[0]
        test_class_content = error_data['test_content']
        test_content = get_test_content(test_class_content, test_method_name)
        
        # proj_id, bug_id = project_dir.split('/')[-2].split('_')
        # if os.path.exists(project_dir):
        #     os.system(f'rm -rf {project_dir}')
        # cmd = ['defects4j', 'checkout', '-p', proj_id, '-v', str(bug_id) + 'f', '-w', project_dir]
        # subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        origin_test_content = ''
        with open(os.path.join(project_dir,  project_test[project_id], test_class_path), 'r') as f:
            origin_test_content = f.read()
        origin_test_class_content = get_test_content(origin_test_content, origin_method_name)
        result.append({
            'test_content': test_content,
            'origin_test_content': origin_test_class_content,
            'error_output': error_data['error_output']
        })
    
    with open(os.path.join(code_base, 'data', 'error_info_base_2024-09-02_test_compair.jsonl'), 'w') as f:
        for r in result:
            f.write(json.dumps(r) + '\n')
    
if __name__ == '__main__':
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-05-fixed'
    prompt_path = '/test_refine/vllm_reference/all_rag_gen_refine_output_2024-09-04-2.jsonl'
    prompt_info = {}
    with open(prompt_path, 'r') as f:
        for id, line in enumerate(f):
            data = json.loads(line)
            if 'completion' in data:
                a = 1
            prompt_info[data['focal_method_content']] = {
                'prompt': data['prompt'],
                'output': data['completion']
            }
    error_result = count_refine_effectiveness(res_dir, prompt_info)
    with open(f'{code_base}/data/error_info_base_2024-09-05-fixed.json', 'w') as f:
        f.write(json.dumps(error_result))
    exit()