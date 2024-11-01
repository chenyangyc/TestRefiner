import os
import time
import json
import random
import string
import fnmatch
import datetime
import threading
import subprocess
from tqdm import tqdm
from multiprocessing import Manager
from concurrent.futures import ProcessPoolExecutor
import xml.etree.ElementTree as ET
import logging

from data.configuration import code_base, defects4j_projects_base
from code_parser import Code_AST
from utils import read_file
import logging

# Configure logger
logger = logging.getLogger('current_file_logger')
logger.setLevel(logging.DEBUG)  # 设置日志级别
 
# 创建handler，用于输出到控制台
# console_handler = logging.StreamHandler()
console_handler = logging.FileHandler(f'{code_base}/data/extract_info.log')
console_handler.setLevel(logging.DEBUG)
 
# 创建formatter，并添加到handler
formatter = logging.Formatter('[%(asctime)s - %(filename)s - %(funcName)s] - %(message)s')
console_handler.setFormatter(formatter)
 
# 将handler添加到logger
logger.addHandler(console_handler)



TMP_DIR = f'{code_base}/tmp/'
os.makedirs(TMP_DIR, exist_ok=True)


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
    # print("Searching for .java files in " + folder_path)
    search_files(folder_path)
    return java_files

def get_project_ids():
    cmd = ['defects4j', 'pids']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    project_ids = result.stdout.splitlines()
    return project_ids

def get_bug_ids(project_id):
    cmd = ['defects4j', 'bids', '-p', project_id]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    bug_ids = result.stdout.splitlines()
    return bug_ids

def get_checkout_path(project_id, bug_id):
    checkout_path = os.path.join(defects4j_projects_base, f'{project_id}_{str(bug_id)}', 'fixed')
    return checkout_path

def export_info(project_id, bug_id):
    checkout_path = get_checkout_path(project_id, bug_id)
    print(checkout_path)
    cmd = ['defects4j', 'export', '-p', 'tests.trigger', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    tests_trigger = result.stdout.splitlines()
    cmd = ['defects4j', 'export', '-p', 'dir.src.classes', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    src_classes = result.stdout.splitlines()[-1].strip()
    cmd = ['defects4j', 'export', '-p', 'dir.src.tests', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    src_tests = result.stdout.splitlines()[-1].strip()
    cmd = ['defects4j', 'export', '-p', 'tests.relevant', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    tests_relevant = result.stdout.splitlines()
    cmd = ['defects4j', 'export', '-p', 'tests.all', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    tests_all = result.stdout.splitlines()
    cmd = ['defects4j', 'export', '-p', 'classes.modified', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    classes_modified = result.stdout.splitlines()
    cmd = ['defects4j', 'export', '-p', 'classes.relevant', '-w', checkout_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    classes_relevant = result.stdout.splitlines()
    
    src_class_dir = os.path.join(checkout_path, src_classes)
    src_class_files = find_java_files(src_class_dir)
    src_class_files = [file.replace(src_class_dir, '').replace('.java', '').replace('/', '.')[1:] for file in src_class_files]
    
    src_tests_dir = os.path.join(checkout_path, src_tests)
    src_test_files = find_java_files(src_tests_dir)
    src_test_files = [file.replace(src_tests_dir, '').replace('.java', '').replace('/', '.')[1:] for file in src_test_files if "test" in file.lower()]
    
    return {
        "project_id": project_id,
        "bug_id": bug_id,
        "src_classes": src_classes,
        "src_tests": src_tests,
        "src_class_files": src_class_files,
        "src_test_files": src_test_files,
        "tests_trigger": tests_trigger,
        "tests_relevant": tests_relevant,
        "tests_all": tests_all,
        "classes_modified": classes_modified,
        "classes_relevant": classes_relevant
    }

def process_results(result_queue, all_task_count):
    count = 0
    start_time = time.time()
    while True:
        time.sleep(0.5)
        result = result_queue.get()  # 阻塞直到从队列中获取一个结果
        count += 1
        if count % 5 == 0:
            # 打印完成数量
            logger.debug(f"{'='*10} {datetime.datetime.now()} {'='*10}")
            logger.debug(f"Finished: {count}/{all_task_count} ({count / all_task_count * 100:.2f}%)")
            # 计算剩余时间
            used_time = (time.time() - start_time)
            hour = int(used_time / 3600)
            minute = int((used_time % 3600) / 60)
            second = int(used_time % 60)
            logger.debug(f"Used Time Cost: {hour}h {minute}m {second}s")
            total_time = (time.time() - start_time) / count * all_task_count
            hour = int(total_time / 3600)
            minute = int((total_time % 3600) / 60)
            second = int(total_time % 60)
            logger.debug(f"Total Time Cost: {hour}h {minute}m {second}s")
        if isinstance(result, dict):
            with open(result["path"], "a", encoding="utf-8") as f:
                f.write(json.dumps(result["data"], ensure_ascii=False) + "\n")
        if count >= 0.95*all_task_count:
            logger.debug(f"{'='*10} {datetime.datetime.now()} {'='*10}")
            logger.debug(f"Finished: {count}/{all_task_count} ({count / all_task_count * 100:.2f}%)")
            break  # 如果收到 ENDING，表示没有更多的结果需要处理


def get_test_relevant_methods_worker(item):
    def generate_random_string(length):
        characters = string.ascii_letters + string.digits  # 包含大写字母、小写字母和数字
        random_string = ''.join(random.choice(characters) for _ in range(length))
        return random_string
    item_data, test_file, file_dir, result_queue = item
    test_src = item_data["src_tests"]
    project_id, bug_id = item_data["project_id"], item_data["bug_id"]
    tmp_project_path = os.path.join(TMP_DIR, f"{project_id}-{bug_id}", generate_random_string(16))

    try:
        subprocess.run(['rm', '-rf', tmp_project_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cmd = ['defects4j', 'checkout', '-p', project_id, '-v', str(bug_id) + 'f', '-w', tmp_project_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        increment_path = os.path.join(tmp_project_path, "increment.txt")
        with open(increment_path, 'w') as f:
            f.writelines([file+"\n" for file in item_data["src_class_files"]])
        
        test_relevant_methods = []
        test_file_path = test_file.replace(".", "/") + ".java"
        test_code = read_file(os.path.join(tmp_project_path, test_src, test_file_path))
        test_ast = Code_AST(code=test_code, lang="java").ast
        test_functions = test_ast.get_functions()
        test_functions_name = [func.get_function_name() for func in test_functions]
        
        # test_functions_name = random.sample(test_functions_name, 100) \
        #                         if len(test_functions_name) > 100 else test_functions_name
        
        # for test_function_name in tqdm(test_functions_name, desc="Test Function"):
        for test_function_name in test_functions_name:
            cmd = ["defects4j", "coverage", "-w", tmp_project_path, "-t", f"{test_file}::{test_function_name}", 
                "-i", increment_path]
            # logger.debug(" ".join(cmd))
            # exit()
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # logger.debug("Run finished!")
            # Specify the path to the 'coverage.xml' file
            xml_file_path = os.path.join(tmp_project_path, "coverage.xml")

            # Load and parse the XML file
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            # Iterate through the coverage data, searching for the target class and method
            for package in root.findall(".//package"):
                for class_element in package.findall(".//class"):
                    be_test_class_name = class_element.attrib["name"]
                    be_test_class_file = class_element.attrib["filename"]
                    
                    for method_element in class_element.findall(".//method"):
                        method_name = method_element.attrib["name"]
                        method_signature = method_element.attrib["signature"]
                        method_line_rate = method_element.attrib["line-rate"]
                        if float(method_line_rate) > 0:
                            line_numbers = []
                            for line_element in method_element.findall(".//line"):
                                line_numbers.append(line_element.attrib["number"])
                            if len(line_numbers) == 0: continue
                            test_relevant_methods.append({"test_file":test_file,            "test_function":test_function_name, 
                                                        "be_test_class_name":be_test_class_name,
                                                        "be_test_class_file":be_test_class_file,
                                                        "be_test_function_name":method_name,
                                                        "be_test_function_signature":method_signature,
                                                        "line_numbers": line_numbers, 
                                                        "method_line_rate":float(method_line_rate)})
        item_data["test_relevant_methods"] = test_relevant_methods
        
        # logger.debug("Finish one file!")
        result_queue.put({"path":os.path.join(file_dir, "data", "func_test_map", project_id+".jsonl"), "data":item_data})
    except Exception as e:
        logger.debug(f"Error: {e}")
    finally:
        subprocess.run(['rm', '-rf', tmp_project_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def extract_test_coverage(d4j_info):
    os.makedirs(os.path.join(code_base, "data", "func_test_map"), exist_ok=True)
    data = d4j_info
    
    tasks = []
    manager = Manager()
    result_queue = manager.Queue()
    for item in data:
        test_files = item["src_test_files"]
        
        for test_file in test_files:
            tasks.append((item, test_file, code_base, result_queue))
            
        with open(os.path.join(code_base, "data", "func_test_map", item["project_id"]+".jsonl"), "w") as f:
            f.write("")
    
    # tasks = tasks[:20]
    random.shuffle(tasks)
    
    result_thread = threading.Thread(target=process_results, args=(result_queue, len(tasks)))
    result_thread.start()

    # results = []
    # for task in tqdm(tasks, desc="Processing Test Files"):
    #     results.append(get_test_relevant_methods_worker(task))    
    
    with ProcessPoolExecutor(max_workers=max(os.cpu_count()//4, 1)) as executor:
        # 提交任务到线程池并传递队列
        [executor.submit(get_test_relevant_methods_worker, task) for task in tasks]

    # 所有任务提交后，向队列发送一个 None 以通知结果处理线程停止
    result_thread.join()  # 等待结果处理线程完成


if __name__ == "__main__":
    project_bug_ids = []

    project_ids = get_project_ids()
    for project_id in project_ids:
        if project_id not in ["Chart", "Closure", "Lang", "Math", "Time"]:
            continue
        bug_ids = get_bug_ids(project_id)
        project_bug_ids.extend([(project_id, bug_id) for bug_id in bug_ids[-1:]])    

    with ProcessPoolExecutor(max_workers=max(os.cpu_count()//2, 1)) as executor:
        d4j_info = list(tqdm(executor.map(export_info, *zip(*project_bug_ids)), total=len(project_bug_ids), desc="Export"))
    
    if d4j_info:
        os.makedirs(os.path.join(code_base, "data"), exist_ok=True)
        json.dump(d4j_info, open(os.path.join(code_base, "data", "d4j_info.json"), "w"), indent=2)
    
    d4j_info = json.load(open(os.path.join(code_base, "data", "d4j_info.json"), "r"))
    
    # for info in d4j_info:
    #     print(info["project_id"], info["bug_id"])
    #     print("src_classes", info["src_classes"])
    #     print("src_tests", info["src_tests"])
    #     print("tests_relevant", info["tests_relevant"])
    #     print("classes_modified", info["classes_modified"])
    #     break
    
    extract_test_coverage(d4j_info)
    print("Done")
    
