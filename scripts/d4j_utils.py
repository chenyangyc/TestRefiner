import os
import javalang
import subprocess
import time
import re
import xml.etree.ElementTree as ET
import signal
from data.configuration import code_base, defects4j_projects_base
import fnmatch
from collections import defaultdict
import json


def get_checkout_path(project_id, bug_id, version):
    if version == "fixed":
        checkout_path = os.path.join(defects4j_projects_base, f'{project_id}_{str(bug_id)}', 'fixed')
    elif version == "buggy":
        checkout_path = os.path.join(defects4j_projects_base, f'{project_id}_{str(bug_id)}', 'buggy')
    return checkout_path


def find_java_files(folder_path):
    java_files = []

    # Recursive function to search for .java files.
    def search_files(path):
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)

            if os.path.isdir(entry_path):
                search_files(entry_path)
            elif fnmatch.fnmatch(entry_path, '*.java'):
                java_files.append(entry_path)
    # logger.debug("Searching for .java files in " + folder_path)
    search_files(folder_path)
    return java_files


def _compress_bz_files(test_content, project_id, bug_id, unzip_output_dir, tmp_execution_base):
    generated_tests_dir = os.path.join(unzip_output_dir, 'evosuite', project_id, str(bug_id))
    generated_tests = find_java_files(generated_tests_dir)
    
    test_file_path = [i for i in generated_tests if 'scaffolding' not in i][0]
    scaffolding_file = [i for i in generated_tests if 'scaffolding' in i][0]
    
    test_relative_path = test_file_path.replace(generated_tests_dir, '')[1:]
    scaffolding_relative_path = scaffolding_file.replace(generated_tests_dir, '')[1:]
    
    target_test = os.path.join(tmp_execution_base, test_relative_path)
    target_scaffolding = os.path.join(tmp_execution_base, scaffolding_relative_path)

    target_test_dir = '/'.join(target_test.split('/')[:-1])
    os.makedirs(target_test_dir, exist_ok=True)
    
    cur_root = os.getcwd()
    os.chdir(tmp_execution_base)
    with open(target_test, 'w') as fw:
        fw.write(test_content)
    os.system(f'cp {scaffolding_file} {target_scaffolding}')
    
    command = f"tar -vcjf LLMGeneratedTests.tar.bz {test_relative_path} {scaffolding_relative_path} 2>/dev/null"
    subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.chdir(cur_root)
    return os.path.join(tmp_execution_base, "LLMGeneratedTests.tar.bz")


def to_jave_bytecode_types(c_str: str):
    # ["B", "C", "D", "F", "I", "J", "Z", "S"]
    if c_str == "B":
        return "java.lang.byte"
    elif c_str == "C":
        return "java.lang.character"
    elif c_str == "D":
        return "java.lang.double"
    elif c_str == "F":
        return "java.lang.float"
    elif c_str == "I":
        return "java.lang.integer"
    elif c_str == "J":
        return "java.lang.long"
    elif c_str == "Z":
        return "java.lang.boolean"
    elif c_str == "S":
        return "java.lang.short"
    elif c_str.startswith("L"):
        return c_str[1:].replace("/", ".")
    elif c_str.startswith("["):
        return to_jave_bytecode_types(c_str[1:]) + "[]"
    else:
        raise NotImplementedError("class type %s not implemented yet" % c_str)



def parse_coverage_xml(coverage_report):
    """
    Load and parse the JaCoCo XML coverage report

    Args:
        coverage_report (str): jacoco生成的覆盖率报告路径

    Raises:
        NotImplementedError: 不支持的变量类型，请联系开发人员

    Returns:
        dict: 经过分析之后的jacoco覆盖率指标
    """
    tree = ET.parse(coverage_report)
    root = tree.getroot()

    coverage_data = defaultdict()
    # Iterate over the packages in the XML and collect data
    for package in root.findall(".//package"):
        package_name = package.attrib["name"]
        package_name = package_name.replace('/', '.')
        coverage_data[package_name] = defaultdict()

        '''
        <line nr="52" mi="5" ci="0" mb="0" cb="0"/>
        nr 属性：表示代码中的行号。
        mi 属性：missed instruction
        ci 属性：covered instruction
        mb 属性：missed branch
        cb 属性：covered branch
        '''
        for sourcefile in package.findall(".//sourcefile"):
            sourcefile_name = sourcefile.attrib["name"]
            if sourcefile.findall(".//line"):
                coverage_data[package_name][sourcefile_name] = {
                    "line" : defaultdict(),
                    "branch" : defaultdict()
                }
                
                coverage_data[package_name][sourcefile_name]
                coverage_line = []
                total_line = []
                
                covered_branch = []
                total_branch = []
                for line in sourcefile.findall(".//line"):
                    nr = int(line.attrib["nr"])
                    mi = int(line.attrib["mi"])
                    ci = int(line.attrib["ci"])
                    mb = int(line.attrib["mb"])
                    cb = int(line.attrib["cb"])
                    if ci > 0:
                        coverage_line.append(nr)
                    total_line.append(nr)
                    
                    if mb > 0 or cb > 0:
                        coverage_data[package_name][sourcefile_name]["branch"][nr] = {
                            "total": mb + cb,
                            "covered": cb
                        }

                coverage_data[package_name][sourcefile_name]["line"]['coverage_line'] = coverage_line
                coverage_data[package_name][sourcefile_name]["line"]['total_line'] = total_line
                
        for clazz in package.findall(".//class"):
            clazz_name = clazz.attrib["name"]
            if clazz.findall(".//method"):
                coverage_data[package_name][clazz_name] = defaultdict()

                for method in clazz.findall(".//method"):
                    method_name = method.attrib["name"]
                    pattern = r"\(.*?\)"
                    parameters = re.findall(pattern, method.attrib["desc"])[0][1:-1]
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
                        if "/" in i:
                            tmp_list.append(i.split("/")[-1])
                        else:
                            tmp_list.append(i)
                    parameter_tuple = tuple(tmp_list)

                    if method_name not in coverage_data[package_name][clazz_name]:
                        coverage_data[package_name][clazz_name][
                            method_name
                        ] = defaultdict()
                    coverage_data[package_name][clazz_name][method_name][
                        parameter_tuple
                    ] = defaultdict()
                    if method.find('.//counter[@type="LINE"]') is not None:
                        coverage_data[package_name][clazz_name][method_name][
                            parameter_tuple
                        ]["line_coverage"] = method.find(
                            './/counter[@type="LINE"]'
                        ).attrib
                    else:
                        coverage_data[package_name][clazz_name][method_name][
                            parameter_tuple
                        ]["line_coverage"] = None
                    if method.find('.//counter[@type="BRANCH"]') is not None:
                        coverage_data[package_name][clazz_name][method_name][
                            parameter_tuple
                        ]["branch_coverage"] = method.find(
                            './/counter[@type="BRANCH"]'
                        ).attrib
                    else:
                        coverage_data[package_name][clazz_name][method_name][
                            parameter_tuple
                        ]["branch_coverage"] = None
    return coverage_data



def _check_coverage(project_dir, proj_id, bug_id, report_dir):
    """
    执行完测试之后，收集coverage数据

    Args:
        directory_path (str): 目标项目的路径
        bug_id (str): 具体的defects4j bug
        report_dir (str): jacoco生成的报告路径

    Returns:
        dict: 经过分析后的jacoco覆盖率指标
    """
    # 加载对应项目的src和test的路径
    with open(f"{code_base}/data/test_src.json", "r") as f:
        content_path = json.load(f)

    project_name = f'{proj_id}_{bug_id}'
    if content_path[project_name.lower()]["src_class"][0] != "/":
        class_base = content_path[project_name.lower()]["src_class"]
    else:
        class_base = content_path[project_name.lower()]["src_class"][1:]
    class_base_dir = os.path.join(project_dir, class_base)

    if content_path[project_name.lower()]["src"][0] != "/":
        src_base = content_path[project_name.lower()]["src"]
    else:
        src_base = content_path[project_name.lower()]["src"][1:]
    src_base_dir = os.path.join(project_dir, src_base)

    cur_dir = os.getcwd()
    os.chdir(project_dir)

    row_report = f"{report_dir}/report.exec"
    report_file = f"{report_dir}/report.xml"

    commands = [
        "java",
        "-jar",
        f"{code_base}/data/jacoco/lib/jacococli.jar",
        "report",
        f"{row_report}",
        f"--classfiles {class_base_dir}",
        f"--sourcefiles {src_base_dir}",
        f"--xml {report_file}",
    ]
    cmd = " ".join(commands)
    print(cmd)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(
            f"Failed in analyzing the coverage results for {bug_id}."
        )
    os.chdir(cur_dir)
    coverage_data = parse_coverage_xml(report_file)
    return coverage_data


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
                                       int(line_element.attrib["hits"])>0))

    return all_lines_info


def run_d4j_test(test_content, project_id, bug_id, project_dir, testmethod, unzip_output_dir, tmp_execution_base):
    '''
    return compiled, timed_out, passed, syntax_error, coverage
    '''
    passed = False
    compiled = False
    timed_out = False
    syntax_error = False
    coverage_info = None
    line_coverage = None
    condition_coverage = None
    error_file_path = os.path.join(tmp_execution_base, 'stderr.txt')
    
    try:
        tokens = javalang.tokenizer.tokenize(test_content)
        parser = javalang.parser.Parser(tokens)
        parser.parse()
    except:
        syntax_error = True
        # print("Syntax Error")
        return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage


    # environ = f"-javaagent:{code_base}/data/jacoco/lib/jacocoagent.jar=destfile={tmp_execution_base}/report.exec"
    # os.environ["JAVA_TOOL_OPTIONS"] = environ
    bz_file_path = _compress_bz_files(test_content, project_id, bug_id, unzip_output_dir, tmp_execution_base)
    
    test_cmd = f'timeout 180 defects4j coverage -w {project_dir} -s {bz_file_path}'
    print(test_cmd)
    
    process = subprocess.Popen(test_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        stdout, stderr = process.communicate(timeout=180)
        return_code = process.returncode
        if return_code == 124:
            passed = False
            timed_out = True
            with open(error_file_path, 'a') as fw:
                fw.write('timeout')
            return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage
        
    except subprocess.TimeoutExpired as te:
        os.kill(process.pid, signal.SIGKILL)
        passed = False
        timed_out = True
        with open(error_file_path, 'a') as fw:
            fw.write('timeout')
        return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage
    
    if stdout is not None:
        cmd_output = stdout.decode(encoding="utf-8").strip()
    else:
        cmd_output = ''
    if stderr is not None:
        cmd_err = stderr.decode(encoding="utf-8").strip()
    else:
        cmd_err = ''
    
    with open(error_file_path, 'a') as fw:
        fw.write(cmd_err)

    all_output = cmd_output + cmd_err
    if 'error:' not in all_output:
        compiled = True
    
    if cmd_output != '' and 'Some tests failed' not in all_output:
        passed = True

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
    return compiled, timed_out, passed, syntax_error, coverage_info, line_coverage, condition_coverage
    