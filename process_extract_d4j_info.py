import os
import json
import random
import logging
from tqdm import tqdm
from data.configuration import code_base, defects4j_projects_base
from code_parser import Code_AST
from utils import (read_file, get_indent, fast_multiprocessing)
import re

import logging

# Configure logger
logger = logging.getLogger('current_file_logger')
logger.setLevel(logging.DEBUG)  # 设置日志级别
 
# 创建handler，用于输出到控制台
console_handler = logging.StreamHandler()
console_handler = logging.FileHandler(f'{code_base}/data/logs/process_extract_d4j_info.log')
console_handler.setLevel(logging.DEBUG)
 
# 创建formatter，并添加到handler
formatter = logging.Formatter('[%(asctime)s - %(filename)s - %(funcName)s] - %(message)s')
console_handler.setFormatter(formatter)
 
# 将handler添加到logger
logger.addHandler(console_handler)


def check_is_test_function(node):
    if node.path.endswith("class_body|method_declaration"):
        return True
    if node.path.endswith("enum_body_declarations|method_declaration"):
        return True
    if node.path.endswith("class_body|constructor_declaration"):
        return True
    return False

def get_checkout_path(project_id, bug_id):
    checkout_path = os.path.join(defects4j_projects_base, f'{project_id}_{str(bug_id)}', 'fixed')
    return checkout_path

def get_location_function(functions, line):
    modified_functions = []
    for function in functions:
        if line >= function.start_line and line <= function.end_line:
            modified_functions.append(function)
    
    if len(modified_functions) == 0:
        return None
    
    modified_function = modified_functions[0]
    for function in modified_functions:
        if modified_function.source in function.source:
            modified_function = function
    
    return modified_function

def get_function(class_file_path, function_name, lines=None, debug=False):
    
    class_file = read_file(class_file_path)
    try:
        class_ast = Code_AST(code=class_file, lang="java").ast
    except:
        return None, None, None
    functions = [function for function in class_ast.get_functions() if function.get_function_name() == function_name]
    
    if lines is not None:
        function = get_location_function(functions, line=int(lines[-1]))
    else:
        function = functions[0]
    
    comment = function.get_function_comment() if function is not None else None
    
    if debug:
        print("class_file_path", class_file_path)
        print("function_name", function_name)
        print("lines", lines)
        print("functions", functions)
        print("functions lines", [(function.start_line, function.end_line) for function in functions])
        print("function", function)
    
    return function, comment, class_file, class_ast


def process_extract_mapping(project_ids):

    processed_data = []
    
    for project_id in project_ids:
        func_test_map_path = os.path.join(code_base, 'data', "func_test_map", project_id+".jsonl")
        func_test_map = []
        with open(func_test_map_path, 'r') as f:
            for line in f:
                func_test_map.append(json.loads(line))
        
        merged_func_test_map = {
            "project_id": func_test_map[0]["project_id"],
            "bug_id": func_test_map[0]["bug_id"],
            "src_classes": func_test_map[0]["src_classes"],
            "src_tests": func_test_map[0]["src_tests"],
            "src_class_files": func_test_map[0]["src_class_files"],
            "src_test_files": func_test_map[0]["src_test_files"],
            "test_relevant_methods": []
        }
        for func_test in func_test_map:
            merged_func_test_map["test_relevant_methods"].extend(func_test["test_relevant_methods"])
            
        test_to_function = {}
        for mapping in merged_func_test_map["test_relevant_methods"]:
            if "<" in mapping["be_test_function_name"]: continue
            key = "::".join([
                mapping["test_file"],
                mapping["test_function"],
            ])
            if key not in test_to_function:
                test_to_function[key] = []
            test_to_function[key].append(mapping)
        merged_func_test_map["test_to_function"] = test_to_function
        
        processed_data.append(merged_func_test_map)
    return processed_data

def get_code_prefix(code_ast, function_code):
    # return "", "", ""
    functions = code_ast.get_functions()
    function = None
    for func in functions:
        if func.source_line == function_code:
            function = func
            break
    
    if function is None: raise Exception("Cannot find function")
    
    functino_body = function.get_function_body()
    function_prefix_with_signature = str(bytes(code_ast.source, 'utf8')[:functino_body.start_byte], encoding="utf-8")
    function_prefix_with_comment = "\n".join(code_ast.source.splitlines()[:function.start_line])
    function_signature = str(bytes(code_ast.source, 'utf8')[function.start_byte:functino_body.start_byte], encoding="utf-8")
    return function_prefix_with_signature, function_prefix_with_comment, function_signature


def get_func_param_tuple(func):
    param_child = [child.source[1:-1].replace('\n', '').strip() for child in func.children if child.type == 'formal_parameters'][0]

    if param_child == '':
        func_param = tuple([])
    elif ',' not in param_child:
        param_type = param_child.split(' ')[-2].lower()
        if '<' in param_type:
            param_type = param_type.split('<')[0]
        func_param = tuple([param_type])
    else:
        all_params = []
        for i in param_child.split(','):
            param_type = i.strip().split(' ')[-2].lower()
            if '<' in param_type:
                param_type = param_type.split('<')[0]
            all_params.append(param_type)
        func_param = tuple(all_params)
    return func_param


def to_jave_bytecode_types(c_str: str):
    # ["B", "C", "D", "F", "I", "J", "Z", "S"]
    if c_str == "B":
        return "byte"
    elif c_str == "C":
        return "char"
        # return "character"
    elif c_str == "D":
        return "double"
    elif c_str == "F":
        return "float"
    elif c_str == "I":
        return "int"
        # return "integer"
    elif c_str == "J":
        return "long"
    elif c_str == "Z":
        return "boolean"
    elif c_str == "S":
        return "short"
    elif c_str.startswith("L"):
        return c_str[1:].replace("/", ".")
    elif c_str.startswith("["):
        return to_jave_bytecode_types(c_str[1:]) + "[]"
    else:
        raise NotImplementedError("class type %s not implemented yet" % c_str)


def get_param_list(method_sig):
    pattern = r"\(.*?\)"
    parameters = re.findall(pattern, method_sig)[0][1:-1]
    raw_param_list = parameters.split(";")
    parameter_list = []

    for param_str in raw_param_list:
        if param_str == "":
            continue
        else:
            param_stack = []

            for i in range(len(param_str)):
                c_str = param_str[i]
                if c_str == "[":
                    param_stack.append(c_str)
                    continue
                elif c_str == "L":
                    param_stack.append(param_str[i:])
                    res = "".join(param_stack)
                    parameter_list.append(
                        to_jave_bytecode_types(res).lower()
                    )
                    param_stack.clear()
                    break
                elif c_str in ["B", "C", "D", "F", "I", "J", "Z", "S"]:
                    param_stack.append(c_str)
                    pass
                else:
                    raise NotImplementedError(
                        "Class Type %s not implemented yet." % c_str
                    )
                res = "".join(param_stack)
                parameter_list.append(
                    to_jave_bytecode_types(res).lower()
                )
                param_stack.clear()

    tmp_list = []
    for i in parameter_list:
        final_param = i
        if "." in i:
            final_param = i.split(".")[-1]
        if '$' in i:
            final_param = final_param.split("$")[-1]
        else:
            final_param = final_param
        tmp_list.append(final_param)
    parameter_tuple = tuple(tmp_list)
    return parameter_tuple


def process_worker(project_id, bug_id, src_classes, src_tests, mappings):
    if len(mappings) < 1: return None
    
    proj_path = get_checkout_path(project_id, bug_id)
    mapping = mappings[0]
    class_file_path = os.path.join(proj_path, src_tests, mapping['test_file'].replace(".", "/")+".java")
    
    function, comment, class_file, class_ast = get_function(class_file_path, mapping["test_function"], lines=None)
    
    if function is None: return None
    if function.get_function_body() is None: return None
    if not check_is_test_function(function): return None
    if len(function.source) < 256: return None
    # NOTE: 不对注释进行过滤
    # if len(comment) < 128 or (not "/*" in comment) or (not "*/" in comment): return None
    
    function_prefix_with_signature, _, function_signature = get_code_prefix(class_ast, function.source_line)
    
    function_name = mapping["test_function"]
    location = os.path.join(src_tests, mapping['test_file'].replace(".", "/")+".java")
    testmethods = [f"{mapping['test_file']}::{mapping['test_function']}" for mapping in mappings if "test" in mapping['test_function'].lower()]
    testmethods = list(set(testmethods))
    if len(testmethods) == 0: return None
    
    classmethods = []
    for mapping in mappings:
        if "<" in mapping['be_test_function_name']: continue
        class_name = mapping['test_file'].split(".")[-1].replace("Tests", "").replace("Test", "").replace("tests", "").replace("test", "")
        # NOTE: 这个地方的过滤有点狠了，比如 ClassTest.java 测 ClassImpl.Java
        if class_name != mapping["be_test_class_name"].split(".")[-1]: continue
        classmethods.append(
            {
                "be_test_class_file": mapping["be_test_class_file"],
                "be_test_class_name": mapping["be_test_class_name"],
                "be_test_function_name": mapping["be_test_function_name"],
                "be_test_function_signature": mapping["be_test_function_signature"],
                "line_numbers": mapping["line_numbers"],
                "method_line_rate": mapping["method_line_rate"]
            }
        )
    if len(set([method["be_test_class_name"] for method in classmethods])) != 1: return None
    # if len(classmethods) == 0: return None
    
    be_test_class_path = os.path.join(proj_path, src_classes, classmethods[0]["be_test_class_file"])
    
    be_test_class_file = read_file(be_test_class_path)
    be_test_class_ast = Code_AST(code=be_test_class_file, lang="java").ast
    be_test_class_context = be_test_class_ast.get_class_context_source()
    be_test_import_context = be_test_class_ast.get_import_context_source()
    be_test_class_signature = be_test_class_ast.get_class_signature_context_source()
    be_test_class_field_context = be_test_class_ast.get_class_field_context_source()
    be_test_class_function_signature_context = be_test_class_ast.get_class_functions_signature_context_source()
    be_test_class_content = be_test_class_file
    
    be_test_class_methods = be_test_class_ast.get_functions()
    for single_tested_method in classmethods:
        be_test_method_name = single_tested_method["be_test_function_name"]
        be_test_method_sig = single_tested_method["be_test_function_signature"]
        be_test_method_param_list = get_param_list(be_test_method_sig)
        be_test_method_contents = [func.source for func in be_test_class_methods if func.get_function_name() == be_test_method_name and get_func_param_tuple(func) == be_test_method_param_list]
        
        # [func.source for func in be_test_class_methods if func.get_function_name() == be_test_method_name]
        # a = [func for func in be_test_class_methods if func.get_function_name() == be_test_method_name][0]
        # get_func_param_tuple(a)
        
        try:
            assert len(be_test_method_contents) == 1
        except:
            if '$' in be_test_method_name:
                continue
            else: 
                print(f'skipped method name: {be_test_method_name}')
            continue
        be_test_method_content = be_test_method_contents[0]
        single_tested_method["method_content"] = be_test_method_content
    
    test_class_context = class_ast.get_class_context_source()
    test_import_context = class_ast.get_import_context_source()
    test_class_signature = class_ast.get_class_signature_context_source()
    test_class_field_context = class_ast.get_class_field_context_source()
    test_class_function_signature_context = class_ast.get_class_functions_signature_context_source()
    indent = get_indent(function.source_line)
    
    # be_test_function, be_test_comment, be_test_class_file, be_test_class_ast = get_function(be_test_class_path, 
    #                                                                     classmethods[0]["be_test_function_name"], 
    #                                                                     classmethods[0]["line_numbers"],
    #                                                                     debug=False)
    # if be_test_function is None: return None
    
    function_example = {
        "task_id": f"testgen|{project_id}|{bug_id}|{location}|{function_name}|{function.start_line}|{function.end_line}",
        "project_id": project_id,
        "bug_id": bug_id,
        "testmethods": testmethods,
        "source_dir": src_tests,
        "location": location,
        "function_star_line": function.start_line,
        "function_end_line": function.end_line,
        "function": function.source_line,
        "function_name": function_name,
        "function_comment": comment,
        "function_prefix_with_signature": function_prefix_with_signature,
        "function_signature": function_signature, 
        "source": class_file,
        "classmethods": classmethods,
        "be_test_class_content": be_test_class_content,
        "be_test_class_context": be_test_class_context,
        "be_test_import_context": be_test_import_context,
        "be_test_class_signature": be_test_class_signature,
        "be_test_class_field_context": be_test_class_field_context,
        "be_test_class_function_signature_context": be_test_class_function_signature_context,
        "be_test_class_name": classmethods[0]["be_test_class_name"].split(".")[-1],
        "be_test_class_long_name": classmethods[0]["be_test_class_name"],
        "be_test_class_path": be_test_class_path,
        "test_class_context": test_class_context,
        "test_import_context": test_import_context,
        "test_class_signature": test_class_signature,
        "test_class_field_context": test_class_field_context,
        "test_class_function_signature_context": test_class_function_signature_context,
        "indent": indent
    }
    return function_example


def process_extract_function(mapping_data):
    processed_data = []
    tasks = []
    for item in tqdm(mapping_data):
        print(item["project_id"])
        for function_key in tqdm(item["test_to_function"]):
            tasks.append((item["project_id"], item["bug_id"], item["src_classes"], item["src_tests"], item["test_to_function"][function_key]))
            # process_worker(item["project_id"], item["bug_id"], item["src_classes"], item["src_tests"], item["test_to_function"][function_key])
    random.shuffle(tasks)
    # tasks = tasks[:3000]
    # print(tasks)
    print("Start processing...")
    # for task in tqdm(tasks):
    #     processed_data.append(process_worker(*task))
        
    # processed_data = fast_multiprocessing(process_worker, tasks, max_workers=1)
    processed_data = fast_multiprocessing(process_worker, tasks)
    
    processed_data = [example for example in processed_data if example is not None]
    
    function_name_set = set()
    filtered_data_dict = {}
    for example in processed_data:
        if example["function_name"] in function_name_set:
            continue
        function_name_set.add(example["function_name"])
        
        if example["function_star_line"]-example["function_end_line"] > 30: continue
        
        if example["project_id"] not in filtered_data_dict:
            filtered_data_dict[example["project_id"]] = []
        filtered_data_dict[example["project_id"]].append(example)
    
    filtered_data = []
    for project in filtered_data_dict:
        filtered_data.extend(filtered_data_dict[project])
    # filtered_data = filtered_data[:10]
    print("Total number of tasks after filtering: ", len(filtered_data))
    json.dump(filtered_data, open(os.path.join(code_base, 'data', 'all_d4j_tests.json'), 'w'), indent=4, ensure_ascii=False)


if __name__ == '__main__':
    # project_ids = get_project_ids()
    # project_ids = ["Chart", "Closure", "Lang", "Math", "Time"]
    project_ids = ["Chart", "Lang", "Math", "Time"]
    mapping_data = process_extract_mapping(project_ids)
    process_extract_function(mapping_data)