
import json
import os
import pickle
import signal
import subprocess
import sys
import javalang
import xml.etree.ElementTree as ET
from loguru import logger
from tree_sitter import Language, Parser
import tree_sitter_java as tsjava

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from core.test_function import *


JAVA_LANGUAGE = Language(tsjava.language(), name='java')
parser = Parser()
parser.set_language(JAVA_LANGUAGE)

d4j_home = "/data/defects4j"
d4j_proj_base = f"{d4j_home}/d4j_fixed_projects"
d4j_command = f'{d4j_home}/framework/bin/defects4j'

def read_data_from_json(json_file):
    with open(json_file, 'r') as fr:
        datas = json.load(fr)
    return datas

def checkout_proj(tmp_project_path, project_id, bug_id):
    '''使用d4j checkout bugid项目到临时文件夹'''
    subprocess.run(['rm', '-rf', tmp_project_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd = ['defects4j', 'checkout', '-p', project_id, '-v', str(bug_id) + 'f', '-w', tmp_project_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def write_test(test_content, test_location):
    '''组装测试文件内容，写入文件'''
    parent_dir = os.path.dirname(test_location)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    with open(test_location, 'w') as fw:
        fw.write(test_content)

def assemble_test(test_location, test_method_signature, test_class_content, test_content, add_test_content, add_method_name, diff_id, be_test_class_long_name):
    test_class_signature = test_method_signature.split('::')[0] # 'org.jfree.chart.axis.junit.CategoryAxisTests'    
    test_class_name = test_class_signature.split('.')[-1] # 'CategoryAxisTests'
    test_method_name = test_method_signature.split('::')[-1] # 'testEquals'
    
    new_add_method_name = add_method_name + str(diff_id) # 'testEquals1'
    new_add_test_content = add_test_content.replace(add_method_name, new_add_method_name) # 'public void testEquals1() {'
    add_method_name = new_add_method_name
    add_test_content = new_add_test_content
    
    # new_test_class_name = test_class_name + str(diff_id) # 'CategoryAxisTests1'
    new_test_class_name = test_class_name
    new_test_method_signature = test_method_signature.replace(test_class_name, new_test_class_name) # 'org.jfree.chart.axis.junit.CategoryAxisTests1::testEquals'
    new_test_method_signature = new_test_method_signature.replace(test_method_name, add_method_name) # 'org.jfree.chart.axis.junit.CategoryAxisTests1::testEquals1'
    new_test_location = test_location.replace(test_class_name, new_test_class_name) # 'tests/org/jfree/chart/axis/junit/CategoryAxisTests1.java'
    new_test_class_content = test_class_content.replace(test_class_name, new_test_class_name)
    new_test_class_content = new_test_class_content.replace(test_content, add_test_content)
    
    new_import = 'import ' + '.'.join(be_test_class_long_name.split('.')[:-1] + ['*']) + ';'
    all_origin_lines = new_test_class_content.split('\n')
    new_lines = []
    flag = True
    for line in all_origin_lines:
        if line.startswith('import ') and flag:
            line = new_import + '\n' + line
            flag = False
        new_lines.append(line)
    new_test_class_content = '\n'.join(new_lines)
    return new_test_method_signature, new_test_location, new_test_class_content

def old_assemble_test(data, diff_id):
    bug_id = data['project_id'] + "_" + data['bug_id'] + '_' + 'fixed' # 'Chart_1'
    fixed_path = os.path.join(d4j_proj_base, bug_id)
    
    test_location = data['location'] # 'tests/org/jfree/chart/axis/junit/CategoryAxisTests.java'
    test_import_context = data['test_import_context']
    test_class_head = data['test_class_signature'] # 'public class CategoryAxisTests extends TestCase '
    test_class_field_context = data['test_class_field_context']
    test_function_content = data['function']
    
    test_method_signature = data['testmethods'][0] # 'org.jfree.chart.axis.junit.CategoryAxisTests::testEquals'
    test_class_signature = test_method_signature.split('::')[0] # 'org.jfree.chart.axis.junit.CategoryAxisTests'    
    test_class_name = test_class_signature.split('.')[-1] # 'CategoryAxisTests'
    
    new_test_class_name = test_class_name + str(diff_id) # 'CategoryAxisTests1'
    new_test_class_signature = test_class_signature.replace(test_class_name, new_test_class_name) # 'org.jfree.chart.axis.junit.CategoryAxisTests1'
    new_test_method_signature = test_method_signature.replace(test_class_name, new_test_class_name) # 'org.jfree.chart.axis.junit.CategoryAxisTests1::testEquals'
    new_test_class_head = test_class_head.replace(test_class_name, new_test_class_name) # 'public class CategoryAxisTests1 extends TestCase '
    new_test_class_content = f'{test_import_context}\n\n{new_test_class_head}{{\n{test_class_field_context}\n{test_function_content}\n}}'
    
    new_test_location = test_location.replace(test_class_name, new_test_class_name) # 'tests/org/jfree/chart/axis/junit/CategoryAxisTests1.java'
    new_test_file_path = os.path.join(fixed_path, new_test_location) # '/data/defects4j/evo_projects/Chart_1/fixed/tests/org/jfree/chart/axis/junit/CategoryAxisTests1.java'
    if os.path.exists(new_test_file_path):
        logger.info(f"File {new_test_file_path} already exists")
    
    if not os.path.exists(os.path.dirname(new_test_file_path)):
        os.makedirs(os.path.dirname(new_test_file_path))
    with open(new_test_file_path, 'w') as fw:
        fw.write(new_test_class_content)
    
    return fixed_path, new_test_method_signature, new_test_class_content, new_test_file_path

def record_error_info(error_file_path, error_result):
    parent_dir = os.path.dirname(error_file_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    with open(error_file_path, 'a', encoding='utf-8') as f:
        json.dump(error_result, f)
        f.write('\n')  

def run_test(test_content, project_dir, test_method_signature, be_test_class_long_name):
    '''
    return compiled, timed_out, passed, syntax_error, coverage
    '''

    compiled = False
    timed_out = False
    passed = False
    syntax_error = False
    coverage_info = None
    line_coverage = None
    condition_coverage = None
    
    error_result = {
        'error_type': None,
        'error_output': None,
        'project_dir': project_dir,
        'test_method_signature': test_method_signature,
        'test_content': test_content
    }

    try:
        tokens = javalang.tokenizer.tokenize(test_content)
        parser = javalang.parser.Parser(tokens)
        parser.parse()
    except:
        syntax_error = True
        error_result['error_type'] = 'syntax_error'
        return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result

    increment_path = os.path.join(project_dir, "increment.txt")
    with open(increment_path, 'w') as f:
        f.write(be_test_class_long_name)
    
    # timeout 180 defects4j coverage -w /data/defects4j/d4j_fixed_projects/Chart_26_fixed -t org.jfree.chart.axis.junit.CategoryAxisTests0::testEquals
    test_cmd = f'timeout 180 defects4j coverage -w {project_dir} -t {test_method_signature} -i {increment_path}'
    
    process = subprocess.Popen(test_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        stdout, stderr = process.communicate(timeout=180)
        return_code = process.returncode
        if return_code == 124:
            passed = False
            timed_out = True
            error_result['error_type'] = 'timeout'
            return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result
        
    except subprocess.TimeoutExpired as te:
        os.kill(process.pid, signal.SIGKILL)
        passed = False
        timed_out = True
        error_result['error_type'] = 'timeout'
        return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result
    
    if stdout is not None:
        cmd_output = stdout.decode(encoding="utf-8").strip()
    else:
        cmd_output = ''
    if stderr is not None:
        cmd_err = stderr.decode(encoding="utf-8").strip()
    else:
        cmd_err = ''
    
    all_output = cmd_output + cmd_err
    # 编译错误
    if 'error:' not in all_output:
        compiled = True
    else:
        error_result['error_type'] = 'compile_error'
        error_result['error_output'] = all_output
        
    # 执行通过
    if cmd_output != '' and 'Some tests failed' not in all_output:
        passed = True
    else:
        if error_result['error_type'] is None:
            error_result['error_type'] = 'run_error'
            error_result['error_output'] = all_output

    if cmd_output != '':
        log = cmd_output.split('\n')
        if "Line coverage:" in log[-2]:
            line_coverage = log[-2].split(":")[-1].strip().replace("%", "")
            line_coverage = float(line_coverage) / 100.0
        if "Condition coverage:" in log[-1]:
            condition_coverage = log[-1].split(":")[-1].strip().replace("%", "")
            condition_coverage = float(condition_coverage) / 100.0
        
        xml_file_path = os.path.join(project_dir, "coverage.xml")
        coverage_info = analysis_coverage(xml_file_path)
        os.system(f'rm {xml_file_path}')
    
    return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result

def analysis_coverage(xml_file_path):
    # Load and parse the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    all_lines_info = []
    for package in root.findall(".//package"):
        for class_element in package.findall(".//class"):
            be_test_class_name = class_element.attrib["name"]
            be_test_class_file = class_element.attrib["filename"]
            # print(be_test_class_name, be_test_class_file)
            for line_element in class_element.findall(".//line"):
                # print(line_element.attrib["number"], line_element.attrib["hits"])
                all_lines_info.append((be_test_class_name, be_test_class_file, 
                                        line_element.attrib["number"],
                                        int(line_element.attrib["hits"]) > 0))

    return all_lines_info

def delete_test_file(test_file_path):
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    else:
        logger.error(f"The file {test_file_path} does not exist")

def get_method_name_node(node):
    if node.type == 'method_declaration':
        return node.child_by_field_name('name')
    for child in node.children:
        name_node = get_method_name_node(child)
        if name_node is not None:
            return name_node
    return None

def get_method_name(code):
    tree = parser.parse(bytes(code, "utf8"))
    root = tree.root_node
    return get_method_name_node(root).text.decode()


def main():
    code_base = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(code_base, 'split_d4j_tests_filtered.json')
    tmp_execution_base = os.path.join(code_base, 'tmp_execution_base')
    tmp_project_base = os.path.join(code_base, 'tmp_projects')
    output_jsonl_path = os.path.join(code_base, 'result.jsonl')
    done_path = os.path.join(code_base, 'done_list.txt')
    
    test_datas = read_data_from_json(json_file)
    
    
    for id, data in enumerate(test_datas):
        project_id = data['project_id']
        bug_id = data['bug_id']
        fixed_path = data['project_id'] + "_" + data['bug_id'] + '_' + 'fixed' # 'Chart_1'
        fixed_path = os.path.join(d4j_proj_base, fixed_path)
        
        tmp_project_path = os.path.join(tmp_project_base, project_id, bug_id)
        # checkout_proj(tmp_project_path, project_id, bug_id)
        
        test_location = data['location'] # 'tests/org/jfree/chart/axis/junit/CategoryAxisTests.java'
        test_content = data['source']
        test_method_signature = data['testmethods'][0] # 'org.jfree.chart.axis.junit.CategoryAxisTests::testEquals'
        for spid, sp_test in enumerate(data['split_assertion_code']):
            add_test_content = sp_test
            add_method_name = get_method_name(add_test_content)
            # new_test_method_signature, new_test_location, new_test_content = assemble_test(test_location, test_method_signature, test_class_content,  test_content, add_test_content, add_method_name, str(id) + '_' + str(spid))
            # new_test_location = os.path.join(fixed_path, new_test_location)
            # write_test(new_test_content, new_test_location)
            # delete_test_file(new_test_location)
            # continue
            # logger.info(f"Start processing {id} : {new_test_method_signature}")
            # run_result = run_test(new_test_content, fixed_path, new_test_method_signature)
            # logger.info(f"Finish processing {id} : Compile: {run_result['compiled']}, Passed: {run_result['passed']}, Syntax Error: {run_result['syntax_error']}, Timed Out: {run_result['timed_out']}")
            
            # delete_test_file(new_test_location)
            # append_to_jsonl(run_result, output_jsonl_path)
        with open(done_path, 'a') as fw:
            fw.write(f"{test_method_signature}\n")


def append_to_jsonl(data, output_file):
    parent_dir = os.path.dirname(output_file)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    with open(output_file, 'a', encoding='utf-8') as f:
        json.dump(data, f)
        f.write('\n')  
            
def read_error_test_and_run():
    project_test = {}
    sp_path = '/test_refine/data/split_d4j_tests_filtered.json'
    with open(sp_path, 'r') as fr:
        datas = json.load(fr)
    for data in datas:
        project_id = data['project_id']
        project_test[project_id] = data['source_dir']
    
    error_josnl_path = '/test_refine/data/error_info.jsonl'
    with open(error_josnl_path, 'r') as fr:
        for line in fr:
            data = json.loads(line)
            test_content = data['test_content']
            project_dir = data['project_dir']
            test_method_signature = data['test_method_signature']
            project_id = project_dir.split('/')[-2].split('_')[0]
            test_location = os.path.join(project_dir, project_test[project_id], test_method_signature.split('::')[0].replace('.', '/') + '.java')
            
            write_test(test_content, test_location)
            # compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage, error_result = run_test(test_content, project_dir, test_method_signature)
            # failed_path = os.path.join(project_dir, 'failing_tests')
            # print(test_method_signature)
            # print(failed_path)
            # print(test_location)
            delete_test_file(test_location)

def find_pkl_files(directory):
    pkl_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".pkl"):
                pkl_files.append(os.path.join(root, file))

    return pkl_files

def read_pkl():
    pkl_dir_path = '/test_refine/data/d4j_base_function_2024-08-29'
    pkl_files = find_pkl_files(pkl_dir_path)
    _0, _1 = 0, 0
    for pkl_path in pkl_files:
        with open(pkl_path, 'rb') as fr:
            data = pickle.load(fr)
        if data.line_coverage > 0:
            _1 += 1
        else:
            _0 += 1
    print(_0, _1)

if __name__ == '__main__':
    # main()
    # read_error_test_and_run()
    read_pkl()
    pass