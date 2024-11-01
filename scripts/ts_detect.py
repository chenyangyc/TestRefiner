from data.configuration import TSDETECTOR_PATH, SMELL_TYPES
import pandas as pd
from glob import glob
import os
import csv
import subprocess


def load_result(fold_path, func_id):
    files = glob(fold_path + '/Output_TestSmellDetection*')
    assert len(files) == 1
    df = pd.read_csv(files[0])
    res_dict = dict(df.to_dict(orient='records')[0])
    for key in list(res_dict.keys()):
        if key not in SMELL_TYPES:
            del res_dict[key]
    return res_dict

def run_ts_detector(test_function, ts_tmp_dir):
    os.makedirs(ts_tmp_dir, exist_ok=True)
    
    test_file_content = test_function.assemble_test_file()
    be_test_class_path = test_function.be_test_class_path
    
    # ts_tmp_file = os.path.join(ts_tmp_dir, f"{test_function.function_id}.java")
    ts_tmp_file = os.path.join(ts_tmp_dir, f"test.java")
    with open(ts_tmp_file, "w") as f:
        f.write(test_file_content)
    
    # 确保路径是列表
    test_path = [ts_tmp_file]
    class_path = [be_test_class_path]
    
    # 创建输入CSV文件
    input_csv_path = os.path.join(ts_tmp_dir, "input.csv")
    with open(input_csv_path, 'w', newline='') as file:
        writer = csv.writer(file)

        # 假设同一索引的测试路径和类路径相对应
        for t_path, c_path in zip(test_path, class_path):
            writer.writerow(['myCoolApp', t_path, c_path])

    # 构建并执行JAR命令
    command = f"java -jar {TSDETECTOR_PATH} {input_csv_path}"
    # print(f"Running TS Detector with command: {command}")
    # execute the command in temp folder
    result = subprocess.run(command, cwd=ts_tmp_dir, shell=True, capture_output=True)
    
    res_dict = {
        "func_id": test_function.function_id,
        'smells': None,
        "is_success": None,
    }
    # 输出结果
    if result.returncode == 0:
        # print("TS Detector ran successfully.")
        final_result = load_result(ts_tmp_dir, test_function.function_id)
        res_dict['smells'] = final_result
        os.system(f'rm -rf {ts_tmp_dir}')
        res_dict["is_success"] = True
    else:
        print("Error running TS Detector:")
        print(result.stderr)
        os.system(f'rm -rf {ts_tmp_dir}')
        res_dict["is_success"] = False
    return res_dict

