import json
import os
from glob import glob
import pickle
from data.configuration import code_base
from collections import defaultdict


def process_cov_info(coverage_info):
    all_lines = set()
    covered_lines = set()
    for i in coverage_info:
        line_identifier = (i[1], i[2])
        is_covered = i[3]

        all_lines.add(line_identifier)

        if is_covered:
            covered_lines.add(line_identifier)
    return covered_lines, all_lines


def count_split_effectiveness(res_dir):
    all_projs = glob(res_dir + '/*')

    res_dict = defaultdict(dict)
    
    different_result = {}
    for single_proj in all_projs:
        proj_name = single_proj.split('/')[-1]
        all_functions = glob(single_proj + '/*')
        
        all_before_covered_lines = set()
        all_split_covered_lines = set()
        all_refine_covered_lines = set()
        all_lines = set()
        
        before_compiled = []
        split_compiled = []
        refined_compiled = []
        
        before_passed = []
        split_passed = []
        refined_passed= []
        
        for single_func in all_functions:
            single_base_function = pickle.load(open(single_func, 'rb'))
            
            # if 'SplineInterpolatorTest' in single_base_function.be_test_class_long_name:
            #     continue
            
            if single_base_function.coverage_info is None:
                continue
            
            splitted_functions = single_base_function.splitted_test_functions
            if not splitted_functions:
                continue
            
            refined_functions = single_base_function.refined_test_functions
            if not refined_functions:
                continue
            
            single_covered_lines, single_lines = process_cov_info(single_base_function.coverage_info)
            
            all_lines = all_lines.union(single_lines)
            all_before_covered_lines = all_before_covered_lines.union(single_covered_lines)
            
            before_compiled.append(single_base_function.compiled)
            before_passed.append(single_base_function.passed)
            
            single_before_covered_lines = single_covered_lines
            single_before_lines = single_lines
            single_split_covered_lines = set()
            single_split_lines = set()
            for one_splitted in splitted_functions:
                if one_splitted.coverage_info is None:
                    continue
                
                single_covered_lines, single_lines = process_cov_info(one_splitted.coverage_info)
                all_lines = all_lines.union(single_lines)
                all_split_covered_lines = all_split_covered_lines.union(single_covered_lines)
                single_split_covered_lines = single_split_covered_lines.union(single_covered_lines)
                single_split_lines = single_split_lines.union(single_lines)
            
            
            if len(single_split_covered_lines) != len(single_before_covered_lines):
                different_result[single_func] = {
                    'bug_id': single_base_function.project_id + '_' + single_base_function.bug_id,
                    'before': len(single_before_covered_lines),
                    'split': len(single_split_covered_lines),
                    'test_content' : single_base_function.function_content,
                    'splitted_content': [i.function_content for i in splitted_functions], 
                }


            is_compiled = all([i.compiled for i in splitted_functions])
            is_passed = all([i.passed for i in splitted_functions])
            if not is_compiled:
                pass
            split_compiled.append(is_compiled)
            split_passed.append(is_passed)
            
            for one_refined in refined_functions:
                if not one_refined.compiled:
                    error_info_path = os.path.join(code_base, 'data', f'error_info_refine_2024-09-03.jsonl')
                    error_result = one_refined.error_result
                    if error_result['error_type'] is not None and 'compile' in error_result['error_type']:
                        print('')
                        with open(error_info_path, 'a') as f:
                            json.dump(error_result, f)
                            f.write('\n')
                    pass
                
                if one_refined.coverage_info is None:
                    continue
                
                single_covered_lines, single_lines = process_cov_info(one_refined.coverage_info)
                all_lines = all_lines.union(single_lines)
                all_refine_covered_lines = all_refine_covered_lines.union(single_covered_lines)

            
            is_compiled = all([i.compiled for i in refined_functions])
            is_passed = all([i.passed for i in refined_functions])
            if not is_compiled:
                print()
                pass
            refined_compiled.append(is_compiled)
            refined_passed.append(is_passed)

        print(f"Project: {proj_name}")
        print(f"Base coverage lines: {len(all_before_covered_lines)}")
        print(f"Split coverage lines: {len(all_split_covered_lines)}")
        print(f"Base total lines: {len(all_lines)}")
        print(f"Split total lines: {len(all_lines)}")
        print('=='*25)
        res_dict[proj_name]['base_cov'] = len(all_before_covered_lines) / len(all_lines)
        res_dict[proj_name]['split_cov'] = len(all_split_covered_lines) / len(all_lines)
        res_dict[proj_name]['refine_cov'] = len(all_refine_covered_lines) / len(all_lines)

        res_dict[proj_name]['base_compile'] = before_compiled.count(True) / len(before_compiled)
        res_dict[proj_name]['split_compile'] = split_compiled.count(True) / len(split_compiled)
        res_dict[proj_name]['refine_compile'] = refined_compiled.count(True) / len(refined_compiled)

        res_dict[proj_name]['base_pass'] = before_passed.count(True) / len(before_passed)
        res_dict[proj_name]['split_pass'] = split_passed.count(True) / len(split_passed)
        res_dict[proj_name]['refine_pass'] = refined_passed.count(True) / len(refined_passed)
        pass
    
    with open(f'{code_base}/data/different_coverage_lines.json', 'w') as f:
        json.dump(different_result, f, indent=4)
    return res_dict


def get_error_info(single_base_function):
    error_info = {
        'bug_id': single_base_function.project_id + '_' + single_base_function.bug_id,
        'rag_tests': [],
        'base_tests': [],
    }
    for rag_test in single_base_function.serve_as_seed_new_functions:
        error_info['rag_tests'].append({
            'test_name': rag_test.test_class_context,
            'compiled': rag_test.compiled,
            'passed': rag_test.passed,
            'error_result': rag_test.error_result,
        })
    
    return error_info

def count_refine_effectiveness(res_dir):
    all_projs = glob(res_dir + '/*')

    res_dict = defaultdict(dict)
    
    for single_proj in all_projs:
        proj_name = single_proj.split('/')[-1]
        all_functions = glob(single_proj + '/*')
        
        total_case_num = 0
        bad_case_num = 0
        same_case_num = 0
        better_case_num = 0
        
        # if 'chart' not in proj_name.lower():
        #     continue
        
        all_before_covered_lines = set()
        all_refine_covered_lines = set()
        all_lines = set()
        
        before_compiled = []
        refined_compiled = []
        method_level_before_compiled = defaultdict(list)
        method_level_refined_compiled = defaultdict(list)
        
        before_passed = []
        refined_passed= []
        method_level_before_passed = defaultdict(list)
        method_level_refined_passed = defaultdict(list)
        
        for single_func in all_functions:
            # ds-6.7
            # if any([i in single_func for i in ['testDrawSeriesWithZeroItems', 'testGetKey', 'testGetSetValue', 'testGetLegendItemSeriesIndex']]):
            #     continue
            # phind-34
            # if any([i in single_func for i in ['testParseLocalTime_simple', 'testFormatAppendFormatter', 'testSetIntoPeriod_Object3', 'testPublicGetNameMethod', 'testIsSingular', 'testGetContent', 'testGetBaseSectionPaint', 'testDrawWithNullLegendLabels', 'testContains']]):
            #     continue

            single_base_function = pickle.load(open(single_func, 'rb'))
            
            single_func_base_covered = set()
            single_func_refine_covered = set()
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
                before_compiled.append(one_origin_rag_test.compiled)
                before_passed.append(one_origin_rag_test.passed)
                
                method_level_before_compiled[focal_method_content].append(one_origin_rag_test.compiled)
                method_level_before_passed[focal_method_content].append(one_origin_rag_test.passed)

                single_base_compiled.append(one_origin_rag_test.compiled)
                single_base_passed.append(one_origin_rag_test.passed)
                
                if one_origin_rag_test.coverage_info is None:
                    continue
                
                single_covered_lines, single_lines = process_cov_info(one_origin_rag_test.coverage_info)
                
                all_lines = all_lines.union(single_lines)
                all_before_covered_lines = all_before_covered_lines.union(single_covered_lines)
                
                single_func_base_covered = single_func_base_covered.union(single_covered_lines)

                
            # refine之后的test作为prompt生成的test
            for one_refined_rag_test in single_base_function.rag_serve_as_seed_new_functions:
                refined_compiled.append(one_refined_rag_test.compiled)
                refined_passed.append(one_refined_rag_test.passed)
                
                method_level_refined_compiled[focal_method_content].append(one_refined_rag_test.compiled)
                method_level_refined_passed[focal_method_content].append(one_refined_rag_test.passed)

                single_refine_compiled.append(one_refined_rag_test.compiled)
                single_refine_passed.append(one_refined_rag_test.passed)
                
                if one_refined_rag_test.coverage_info is None:
                    continue
                
                single_covered_lines, single_lines = process_cov_info(one_refined_rag_test.coverage_info)
                
                all_lines = all_lines.union(single_lines)
                all_refine_covered_lines = all_refine_covered_lines.union(single_covered_lines)
                
                single_func_refine_covered = single_func_refine_covered.union(single_covered_lines)
                

            if len(single_func_base_covered) > len(single_func_refine_covered):
                if len(single_func_base_covered) - len(single_func_refine_covered) > 30:
                    # print(f"origin covered: {len(single_func_base_covered)}, refined covered: {len(single_func_refine_covered)}")
                    # print(single_func)
                    pass
            #     bad_case_num += 1
            
            # NOTE：这里统计base pass了，但是refine没有pass的casee
            # if all(single_base_passed) and not all(single_refine_passed):
            #     print(single_func)
            #     bad_case_num += 1
            
            # NOTE： 这里统计 base compile了，但是refine没有compile的case
            if all(single_base_compiled) and not all(single_refine_compiled):
                print(single_func)
                error_info = get_error_info(single_base_function)
                pass

        res_dict[proj_name]['base_cov'] = len(all_before_covered_lines) / len(all_lines)
        res_dict[proj_name]['refine_cov'] = len(all_refine_covered_lines) / len(all_lines)

        res_dict[proj_name]['base_compile'] = before_compiled.count(True) / len(before_compiled)
        res_dict[proj_name]['refine_compile'] = refined_compiled.count(True) / len(refined_compiled)

        res_dict[proj_name]['base_pass'] = before_passed.count(True) / len(before_passed)
        res_dict[proj_name]['refine_pass'] = refined_passed.count(True) / len(refined_passed)
        
        total_focal_number = max(len(method_level_before_compiled), len(method_level_refined_compiled))
        total_before_compiled = sum([1 for i in method_level_before_compiled.values() if all([h for h in i])]) / total_focal_number
        total_refined_compiled = sum([1 for i in method_level_refined_compiled.values() if all([h for h in i])]) / total_focal_number
        
        total_before_passed = sum([1 for i in method_level_before_passed.values() if all([h for h in i])]) / total_focal_number
        total_refined_passed = sum([1 for i in method_level_refined_passed.values() if all([h for h in i])]) / total_focal_number
        
        res_dict[proj_name]['total_base_compile'] = total_before_compiled
        res_dict[proj_name]['total_refine_compile'] = total_refined_compiled
        res_dict[proj_name]['total_base_pass'] = total_before_passed
        res_dict[proj_name]['total_refine_pass'] = total_refined_passed
        
    return res_dict

if __name__ == '__main__':
    # res_dir = f'{code_base}/data/d4j_base_function_2024-09-02_test'
    # res_dir = f'{code_base}/data/d4j_refine_function_2024-09-04'
    # split_res_dict = count_split_effectiveness(res_dir)
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-05-fixed'
    res_file = f'{code_base}/data/refine_coverage_fixed.csv'
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-06-seperate'
    res_file = f'{code_base}/data/refine_coverage_seperate.csv'
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-06-codellama-7b'
    res_file = f'{code_base}/data/refine_coverage_codellama_7b.csv'
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-06-codellama-13b'
    res_file = f'{code_base}/data/refine_coverage_codellama_13b.csv'
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-06-deepseek-33b'
    res_file = f'{code_base}/data/refine_coverage_deepseek_33b.csv'
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-06-phind-34b'
    res_file = f'{code_base}/data/refine_coverage_phind_34b.csv'
    
    res_dir = f'{code_base}/data/d4j_rag_function_2024-09-11-codellama-34b'
    res_file = f'{code_base}/data/refine_coverage_codellama_34b.csv'
    
    
    write_file = False
    
    refine_res_dict = count_refine_effectiveness(res_dir)
    
    # print the result
    for proj_name, proj_res in refine_res_dict.items():
        print(f"Project: {proj_name}")
        print(f"Base coverage: {proj_res['base_cov']}")
        print(f"Refine coverage: {proj_res['refine_cov']}")
        # print(f"Base compile: {proj_res['base_compile']}")
        # print(f"Refine compile: {proj_res['refine_compile']}")
        # print(f"Base pass: {proj_res['base_pass']}")
        # print(f"Refine pass: {proj_res['refine_pass']}")
        
        print(f"Total Base compile: {proj_res['total_base_compile']}")
        print(f"Total Refine compile: {proj_res['total_refine_compile']}")
        print(f"Total Base pass: {proj_res['total_base_pass']}")
        print(f"Total Refine pass: {proj_res['total_refine_pass']}")
        print("="*50)
    
    if not write_file:
        print('Project,    Base coverage,    Refine coverage,    Base compile,    Refine compile,    Base pass,    Refine pass\n')
        for proj_name, proj_res in refine_res_dict.items():
            proj_res['base_cov'] = f"{proj_res['base_cov']*100:.2f}%"
            proj_res['refine_cov'] = f"{proj_res['refine_cov']*100:.2f}%"
            proj_res['total_base_compile'] = f"{proj_res['total_base_compile']*100:.2f}%"
            proj_res['total_refine_compile'] = f"{proj_res['total_refine_compile']*100:.2f}%"
            proj_res['total_base_pass'] = f"{proj_res['total_base_pass']*100:.2f}%"
            proj_res['total_refine_pass'] = f"{proj_res['total_refine_pass']*100:.2f}%"

            # Format the print output with left alignment and spacing
            print(f"{proj_name:<10}    {proj_res['base_cov']:<15}    {proj_res['refine_cov']:<15}    "
            f"{proj_res['total_base_compile']:<15}    {proj_res['total_refine_compile']:<15}    "
            f"{proj_res['total_base_pass']:<10}    {proj_res['total_refine_pass']:<10}")
            # print(f"{proj_name},{proj_res['base_cov']},{proj_res['refine_cov']},{proj_res['total_base_compile']},{proj_res['total_refine_compile']},{proj_res['total_base_pass']},{proj_res['total_refine_pass']}\n")
        pass
    pass

    if write_file:
        with open(res_file, 'w') as fw:
            fw.write('Project,Base coverage, Refine coverage,Base compile, Refine compile,Base pass, Refine pass\n')
            for proj_name, proj_res in refine_res_dict.items():
                proj_res['base_cov'] = f"{proj_res['base_cov']*100:.2f}%"
                proj_res['refine_cov'] = f"{proj_res['refine_cov']*100:.2f}%"
                proj_res['total_base_compile'] = f"{proj_res['total_base_compile']*100:.2f}%"
                proj_res['total_refine_compile'] = f"{proj_res['total_refine_compile']*100:.2f}%"
                proj_res['total_base_pass'] = f"{proj_res['total_base_pass']*100:.2f}%"
                proj_res['total_refine_pass'] = f"{proj_res['total_refine_pass']*100:.2f}%"
                fw.write(f"{proj_name},{proj_res['base_cov']},{proj_res['refine_cov']},{proj_res['total_base_compile']},{proj_res['total_refine_compile']},{proj_res['total_base_pass']},{proj_res['total_refine_pass']}\n")

        
    exit()
    # print the result
    for proj_name, proj_res in split_res_dict.items():
        print(f"Project: {proj_name}")
        print(f"Base coverage: {proj_res['base_cov']}")
        print(f"Split coverage: {proj_res['split_cov']}")
        print(f"Refine coverage: {proj_res['refine_cov']}")
        print(f"Base compile: {proj_res['base_compile']}")
        print(f"Split compile: {proj_res['split_compile']}")
        print(f"Refine compile: {proj_res['refine_compile']}")
        print(f"Base pass: {proj_res['base_pass']}")
        print(f"Split pass: {proj_res['split_pass']}")
        print(f"Refine pass: {proj_res['refine_pass']}")
        print("="*50)