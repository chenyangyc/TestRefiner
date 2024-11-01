import os
import time
import subprocess
from multiprocessing import Queue, Process
from data.configuration import defects4j_bin_dir, code_base, defects4j_projects_base
import fnmatch
import json
import pickle


def read_bug_versions(file_path):
    """
    Reads a file containing software component names and their bug version numbers.
    Returns a dictionary where keys are component names and values are lists of version numbers.
    """
    versions_dict = {}
    with open(file_path, 'r') as file:
        for line in file:
            # Split the line by colon to separate the component name from the version numbers
            parts = line.strip().split(':')
            if len(parts) == 2:
                component, versions = parts
                # Convert the version numbers from string to integers and store them in the dictionary
                versions_dict[component] = [int(v) for v in versions.split(',')]
    return versions_dict



def log(log_file, content):
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write(content + '\n')
    with open(log_file, 'a+') as f:
        f.write(content + '\n')


def uncompress_tar_bz2(file_path, name, version, out_dir='./data/unzip/'):
    if not os.path.exists(file_path):
        print("File does not exist")
        return

    out_dir = os.path.join(out_dir, 'evosuite', name, str(version))
    os.makedirs(out_dir, exist_ok=True)
    command = f'tar -jxvf {file_path} -C {out_dir}'
    print(command)
    result = subprocess.run(command, shell=True)


def gen_for_single_proj(todo_queue, success_queue, fail_queue, row_output_dir, unzip_output_dir, tmp_base, log_file):
    while not todo_queue.empty():
        try:
            name, bug_id = todo_queue.get()
            tmp_dir = f'{tmp_base}/{name}_{bug_id}'
            os.makedirs(tmp_dir, exist_ok=True)
            command = f'{defects4j_bin_dir}gen_tests.pl -g evosuite -t {tmp_dir} -p {name} -v {bug_id}f -b 600 -n 1 -o {row_output_dir}'
            log(log_file, f'{command}')

            result = subprocess.run(command, shell=True)
            
            file_path = f'{row_output_dir}/{name}/evosuite/1/{name}-{bug_id}f-evosuite.1.tar.bz2'
            
            # 输出结果
            if result.returncode == 0:
                print("generate test cases successfully")
                uncompress_tar_bz2(file_path, name, bug_id, unzip_output_dir)
                success_queue.put(1)
            else:
                print("generate test cases failed")
                print(result.stderr.decode('utf-8'))
                fail_queue.put(f"{name} {bug_id} failed")
                fail_queue.put(1)
        except Exception as e:
            print(str(e))
            log(log_file, str(e))
            print(f"{name} {bug_id} crashed.")
            fail_queue.put(f"{name} {bug_id} crashed")


def run_evo_gen(infos, row_output_dir, unzip_output_dir, tmp_base, n_process=70):
    todo_queue = Queue()
    for (project_id, bug_id) in infos:
        todo_queue.put((project_id, bug_id))
    
    total_num = todo_queue.qsize()
    
    log_file = f'{code_base}/data/run_evosuite.log'
    
    log(log_file, f'Todo size {todo_queue.qsize()}')

    success_queue = Queue()
    fail_queue = Queue()
    
    processes = []
    for core_num in range(n_process):
        p = Process(target=gen_for_single_proj,
                    args=(todo_queue, success_queue, fail_queue,row_output_dir, unzip_output_dir, tmp_base,log_file,))
        p.daemon=False
        p.start()
        processes.append(p)

    completed = success_queue.qsize() + fail_queue.qsize()
    all_done = completed == total_num
    while not all_done:
        log(log_file, f"wait info: {success_queue.qsize()}/{total_num} case(s) have been done! {fail_queue.qsize()}/{total_num} case(s) have crashed!")
        completed = success_queue.qsize() + fail_queue.qsize()
        all_done = completed == total_num
        time.sleep(10)

    log(log_file, f'Success size {success_queue.qsize()}')
    log(log_file, f'Fail size {fail_queue.qsize()}')
    for i in fail_queue:
        log(log_file, f'Fail bug id {i}')


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


if __name__ == '__main__':
    
    row_output_dir = f'{code_base}/data/evosuite_gen_0730'
    unzip_output_dir = f'{code_base}/data/evosuite_gen_unzip_0730'
    tmp_base = f'{code_base}/data/tmp_evosuite_gen'
    
    os.makedirs(row_output_dir, exist_ok=True)
    os.makedirs(unzip_output_dir, exist_ok=True)
    os.makedirs(tmp_base, exist_ok=True)
    
    d4j_info = json.load(open(os.path.join(code_base, "data", "d4j_info.json"), "r"))
    
    project_bug_ids = []

    project_ids = get_project_ids()
    for project_id in project_ids:
        if project_id not in ["Chart", "Closure", "Lang", "Math", "Time"]:
            continue
        bug_ids = get_bug_ids(project_id)
        project_bug_ids.extend([(project_id, bug_id) for bug_id in bug_ids[-1:]])    


    # n_process = 60
    # os.makedirs(row_output_dir, exist_ok=True)
    # run_evo_gen(project_bug_ids, row_output_dir, unzip_output_dir, tmp_base, n_process)
    evo_test_name_dict = {}
    for (project_id, bug_id) in project_bug_ids:
        print(project_id, bug_id)

        generated_tests_dir = os.path.join(unzip_output_dir, 'evosuite', project_id, str(bug_id))
        generated_tests = find_java_files(generated_tests_dir)
        
        test_name = [i.replace(generated_tests_dir, '')[1:].replace('.java', '').replace('/', '.') for i in generated_tests if 'scaffolding' not in i]
        evo_test_name_dict[f'{project_id}_{bug_id}'] = test_name
        pass
    with open(f'{code_base}/data/evo_test_name_dict.pkl', 'wb') as fr:
        pickle.dump(evo_test_name_dict, fr)
        
    pass
