import os
from glob import glob
import pickle
from data.configuration import code_base
from collections import defaultdict


def count_smell_occurences(base_function, smell_occurances, run_type):
    if base_function.smell_types is None:
        return None
    for smell_type in base_function.smell_types:
        if smell_type not in smell_occurances:
            smell_occurances[smell_type] = defaultdict(int)
        smell_occurances[smell_type][run_type] += base_function.smell_types[smell_type]


def count_refine_effectiveness(res_dir):
    all_projs = glob(res_dir + '/*')

    total_base_before_cov = []
    total_base_after_cov = []

    total_before_compile = []
    total_after_compile = []
    total_before_pass = []
    total_after_pass = []
    
    smell_occurances = defaultdict()

    for single_proj in all_projs:
        all_functions = glob(single_proj + '/*')
        
        all_before_covered_lines = set()
        all_after_covered_lines = set()
        before_compiled = []
        after_compiled = []
        before_passed = []
        after_passed = []
        
        all_lines = set()
        
        for base_function_file in all_functions:
            single_base_function = pickle.load(open(base_function_file, 'rb'))
            
            proj_name = single_base_function.project_id
            
            be_test_class_name = single_base_function.be_test_class_long_name
            
            if single_base_function.coverage_info is None:
                continue
                
            for i in single_base_function.coverage_info:
                line_identifier = (i[1], i[2])
                is_covered = i[3]

                all_lines.add(line_identifier)

                if is_covered:
                    all_before_covered_lines.add(line_identifier)

            count_smell_occurences(single_base_function, smell_occurances, 'Before')
            
            refined_functions = single_base_function.refined_test_functions
            is_compiled = False
            is_passed = False
            for one_refined in refined_functions:
                if one_refined.coverage_info is None:
                    continue
                
                for i in one_refined.coverage_info:
                    line_identifier = (i[1], i[2])
                    is_covered = i[3]

                    all_lines.add(line_identifier)
               
                    if is_covered:
                        all_after_covered_lines.add(line_identifier)
                
                if one_refined.compiled:
                    is_compiled = True
                if one_refined.passed:
                    is_passed = True
            
                count_smell_occurences(one_refined, smell_occurances, 'After')
            
            before_compiled.append(single_base_function.compiled)
            before_passed.append(single_base_function.passed)
            after_compiled.append(is_compiled)
            after_passed.append(is_passed)
        pass

        total_base_before_cov.append(len(all_before_covered_lines) / len(all_lines))
        total_base_after_cov.append(len(all_after_covered_lines) / len(all_lines))
        
        total_before_compile.append(before_compiled.count(True) / len(before_compiled))
        total_after_compile.append(after_compiled.count(True) / len(after_compiled))
        
        total_before_pass.append(before_passed.count(True) / len(before_passed))
        total_after_pass.append(after_passed.count(True) / len(after_passed))
        # print('=' * 20)
        # print(f'{proj_name}')
        # print(f'Before line rate: {len(all_before_covered_lines) / len(all_lines)} ({len(all_before_covered_lines)}/{len(all_lines)}), After line rate: {len(all_after_covered_lines) / len(all_lines)} ({len(all_after_covered_lines)}/{len(all_lines)})')
        # print(f'After compiled rate: {after_compiled.count(True) / len(after_compiled)} ({after_compiled.count(True)}/{len(after_compiled)})')
        # print(f'After passed rate: {after_passed.count(True) / len(after_passed)} ({after_passed.count(True)}/{len(after_passed)})')

    print('='*20)
    print('Summary of refinement effectiveness')
    print(f'Before line rate: {sum(total_base_before_cov) / len(total_base_before_cov)}, After line rate: {sum(total_base_after_cov) / len(total_base_after_cov)}')
    print(f'Before compiled rate: {sum(total_before_compile) / len(total_before_compile)}, After compiled rate: {sum(total_after_compile) / len(total_after_compile)}')
    print(f'Before passed rate: {sum(total_before_pass) / len(total_before_pass)}, After passed rate: {sum(total_after_pass) / len(total_after_pass)}')
    
    # pretty print smell_occurances
    print('='*20)
    print('Smell occurance count')
    for smell_type in smell_occurances:
        print(f'{smell_type}', end=', ')
        for run_type in smell_occurances[smell_type]:
            print(f'{smell_occurances[smell_type][run_type]}', end=', ')
        print()
    pass

def count_few_shot_effectiveness(res_dir):
    res_dir = f'{code_base}/data/evo_few_shot_res'
    # res_dir = f'{code_base}/data/evo_refine_res'
    all_projs = glob(res_dir + '/*')

    total_proj_before_compile_rate = []
    total_proj_before_pass_rate = []
    total_proj_before_line_rate = []
    total_proj_after_compile_rate = []
    total_proj_after_pass_rate = []
    total_proj_after_line_rate = []

    for single_proj in all_projs:
        all_functions = glob(single_proj + '/*')
        before_compiled = []
        after_compiled = []
        before_passed = []
        after_passed = []
        before_line_rate = []
        after_line_rate = []
        
        all_before_covered_lines = set()
        all_lines = set()
        all_after_covered_lines = set()
        
        for single_res in all_functions:
            base_function = pickle.load(open(single_res, 'rb'))
            
            after_refine_res_file = single_res.replace('evo_few_shot_res', 'evo_refine_seed_gen_res_deepseek')
            if not os.path.exists(after_refine_res_file):
                continue
            after_refine_function = pickle.load(open(after_refine_res_file, 'rb'))
            
            origin_new_generated_functions = base_function.serve_as_seed_new_functions
    
            after_new_generated_functions = []
            for i in after_refine_function.refined_test_functions:
                newly_generated_functions = i.serve_as_seed_new_functions
                after_new_generated_functions.extend(newly_generated_functions)
            if not after_new_generated_functions:
                # print('SKIP')
                continue

            proj_name = base_function.project_id
            package_name = '.'.join(base_function.be_test_class_long_name.split('.')[:-1])
            be_test_class_file = base_function.be_test_class_long_name.split('.')[-1] + '.java'
            be_test_class_name = base_function.be_test_class_long_name
            
            
            is_before_compiled = True
            is_before_passed = True
            for index, i in enumerate(origin_new_generated_functions):
                coverage_info = i.coverage_info
                if coverage_info is None:
                    line_rate = 'Not collected'
                else:
                    line_rate = i.line_coverage
                    for h in coverage_info:
                        # if h[0] != be_test_class_name:
                        #     continue
                        is_covered = h[3]
                        if is_covered:
                            all_before_covered_lines.add((h[0], h[1], h[2]))
                        all_lines.add((h[0], h[1], h[2]))
                    
                is_syntax_error = i.syntax_error
                
                if i.compiled == False:
                    is_before_compiled = False
                
                if i.passed == False:
                    is_before_passed = False

            before_compiled.append(is_before_compiled)
            before_passed.append(is_before_passed)

            is_after_compiled = True
            is_after_passed = True
            for index, i in enumerate(after_new_generated_functions):
                coverage_info = i.coverage_info
                if coverage_info is None:
                    line_rate = 'Not collected'
                else:
                    line_rate = i.line_coverage
                    for h in coverage_info:
                        is_covered = h[3]
                        if is_covered:
                            all_after_covered_lines.add((h[0], h[1], h[2]))
                        all_lines.add((h[0], h[1], h[2]))
                    
                is_syntax_error = i.syntax_error
                
                if i.compiled == False:
                    is_after_compiled = False
                
                if i.passed == False:
                    is_after_passed = False


            # base_covered_lines = set()
            # if base_function.coverage_info is None:
            #         continue
                
            # for i in base_function.coverage_info:
            #     line_identifier = (i[0], i[1], i[2])
            #     is_covered = i[3]

            #     if is_covered:
            #         base_covered_lines.add(line_identifier)
            #     all_lines.add(line_identifier)

            after_compiled.append(is_after_compiled)
            after_passed.append(is_after_passed)
            
            # all_before_covered_lines = all_before_covered_lines.union(base_covered_lines)
            # all_after_covered_lines = all_after_covered_lines.union(base_covered_lines)
            
            if len(all_lines) > 0:
                before_line_rate.append(len(all_before_covered_lines) / len(all_lines))
                after_line_rate.append(len(all_after_covered_lines) / len(all_lines))
            else:
                pass
            pass
        pass

        before_compiled_rate = before_compiled.count(True) / len(before_compiled)
        after_compiled_rate = after_compiled.count(True) / len(after_compiled)
        
        before_passed_rate = before_passed.count(True) / len(before_passed)
        after_passed_rate = after_passed.count(True) / len(after_passed)
        
        avg_before_line_rate = sum([i for i in before_line_rate]) / len(before_line_rate)
        avg_after_line_rate = sum([i for i in after_line_rate]) / len(after_line_rate)
        
        total_proj_before_compile_rate.append(before_compiled_rate)
        total_proj_after_compile_rate.append(after_compiled_rate)
        total_proj_before_pass_rate.append(before_passed_rate)
        total_proj_after_pass_rate.append(after_passed_rate)
        
        
        total_proj_before_line_rate.append(len(all_before_covered_lines) / len(all_lines))
        total_proj_after_line_rate.append(len(all_after_covered_lines) / len(all_lines))
        
        
        # print('=' * 20)
        # print(f'{proj_name}')
        # print(f'Before compiled rate: {before_compiled_rate} ({before_compiled.count(True)}/{len(before_compiled)}), After compiled rate: {after_compiled_rate} ({after_compiled.count(True)}/{len(after_compiled)})')
        # print(f'{proj_name} Before passed rate: {before_passed_rate} ({before_passed.count(True)}/{len(before_passed)}), After passed rate: {after_passed_rate} ({after_passed.count(True)}/{len(after_passed)})')
        # print(f'{proj_name} Before line rate: {avg_before_line_rate} ({len(before_line_rate)}), After line rate: {avg_after_line_rate} ({len(after_line_rate)})')

    print('='*20)
    print('Summary of prompting effectiveness')
    print(f'Before compiled rate: {sum(total_proj_before_compile_rate) / len(total_proj_before_compile_rate)}, After compiled rate: {sum(total_proj_after_compile_rate) / len(total_proj_after_compile_rate)}')
    print(f'Before passed rate: {sum(total_proj_before_pass_rate) / len(total_proj_before_pass_rate)}, After passed rate: {sum(total_proj_after_pass_rate) / len(total_proj_after_pass_rate)}')
    print(f'Before line rate: {sum(total_proj_before_line_rate) / len(total_proj_before_line_rate)}, After line rate: {sum(total_proj_after_line_rate) / len(total_proj_after_line_rate)}')
    

res_dir = f'{code_base}/data/evo_process_refine_seed_gen_res_deepseek'
count_refine_effectiveness(res_dir)
count_few_shot_effectiveness(res_dir)