"""
本脚本的作用是，对于给定的代码，统计其中的assertion数量、method invocation数量、variable assignment数量、代码行数、in-line-comment数量、block-comment数量
"""
import os
import pickle
from glob import glob

from data.configuration import parser, code_base
from scripts.tree_sitter_query import *

'''
1.提取test中的assertion数量
2.提取test中的method invocation数量
3.提取test中的variable assignment数量（包括变量声明）
4.代码行数
5.in-line-comment数量
6.block-comment数量
'''


def count_assertions(code):
    """ 统计代码中的assertion数量 """
    root = parser.parse(bytes(code, "utf8")).root_node
    method_invocations = method_invocation_query.captures(root)

    assert_count = 0
    for method_invocation, _ in method_invocations:
        name_node = method_invocation.child_by_field_name("name")
        if 'assert' in name_node.text.decode():
            assert_count += 1
    return assert_count


def count_method_invocations(code):
    """ 统计代码中的method invocation数量 """
    root = parser.parse(bytes(code, "utf8")).root_node
    method_invocations = process_method_invocation_query.captures(root)
    return len(method_invocations)


def count_variable_assignments(code):
    """ 统计代码中的变量声明和变量赋值语句的数量 """
    root = parser.parse(bytes(code, "utf8")).root_node
    assignments = process_assignment_query.captures(root)
    declarations = process_declaration_query.captures(root)
    return len(assignments) + len(declarations)


def count_line_comment(code):
    """ 统计代码中的行注释数量 """
    root = parser.parse(bytes(code, "utf8")).root_node
    line_comments = line_comment_query.captures(root)
    return len(line_comments)


def count_block_comment(code):
    """ 统计代码中的块注释数量 """
    root = parser.parse(bytes(code, "utf8")).root_node
    block_comments = block_comment_query.captures(root)
    return len(block_comments)


def count_branches(code):
    root = parser.parse(bytes(code, "utf8")).root_node
    if_statements = if_statement_query.captures(root)
    while_statements = while_statement_query.captures(root)
    for_statements = for_statement_query.captures(root)
    do_statements = do_statement_query.captures(root)
    branch_statements = if_statements + while_statements + for_statements + do_statements
    return len(branch_statements)


def statistical_statement_count(codes):
    statistical_result = []
    for single_code in codes:
        single_code = '\n'.join([line for line in single_code.split('\n') if line.strip() != ''])
        statistical_result.append({
            'test_code': single_code,
            'assertion_count': count_assertions(single_code),
            'method_invocation_count': count_method_invocations(single_code),
            'variable_assignment_count': count_variable_assignments(single_code),
            'line_count': len(single_code.split('\n')),
            'line_comment_count': count_line_comment(single_code),
            'block_comment_count': count_block_comment(single_code),
            'branch_count': count_branches(single_code),
        })

    return statistical_result


def get_compiled_tests(res_dir):
    all_projects = glob(res_dir + '/*')
    base_compiled_tests = []
    refine_compiled_tests = []
    for single_proj in all_projects:
        proj_name = single_proj.split('/')[-1]
        all_functions = glob(single_proj + '/*')

        for single_function in all_functions:
            single_base_function = pickle.load(open(single_function, 'rb'))
            if single_base_function.coverage_info is None:
                continue
            if not single_base_function.serve_as_seed_new_functions:
                continue
            if not single_base_function.rag_serve_as_seed_new_functions:
                continue

            for single_test in single_base_function.serve_as_seed_new_functions:
                if single_test.compiled:
                    base_compiled_tests.append(single_test.function_content)
            for single_test in single_base_function.rag_serve_as_seed_new_functions:
                if single_test.compiled:
                    refine_compiled_tests.append(single_test.function_content)
    return base_compiled_tests, refine_compiled_tests


def statistical_projects_statement_count(res_dir):
    base_compiled_tests, refine_compiled_tests = get_compiled_tests(res_dir)
    base_statistical_result = statistical_statement_count(base_compiled_tests)
    refine_statistical_result = statistical_statement_count(refine_compiled_tests)

    base_line_count, refine_line_count = 0, 0
    base_assertion_count, refine_assertion_count = 0, 0
    base_method_invocation_count, refine_method_invocation_count = 0, 0
    base_variable_assignment_count, refine_variable_assignment_count = 0, 0
    base_line_comment_count, refine_line_comment_count = 0, 0
    base_block_comment_count, refine_block_comment_count = 0, 0
    base_branch_count, refine_branch_count = 0, 0

    for single_base_result in base_statistical_result:
        base_line_count += single_base_result['line_count']
        base_assertion_count += single_base_result['assertion_count']
        base_method_invocation_count += single_base_result['method_invocation_count']
        base_variable_assignment_count += single_base_result['variable_assignment_count']
        base_line_comment_count += single_base_result['line_comment_count']
        base_block_comment_count += single_base_result['block_comment_count']
        base_branch_count += single_base_result['branch_count']

    for single_refine_result in refine_statistical_result:
        refine_line_count += single_refine_result['line_count']
        refine_assertion_count += single_refine_result['assertion_count']
        refine_method_invocation_count += single_refine_result['method_invocation_count']
        refine_variable_assignment_count += single_refine_result['variable_assignment_count']
        refine_line_comment_count += single_refine_result['line_comment_count']
        refine_block_comment_count += single_refine_result['block_comment_count']
        refine_branch_count += single_refine_result['branch_count']

    base_line_count /= len(base_statistical_result)
    base_assertion_count /= len(base_statistical_result)
    base_method_invocation_count /= len(base_statistical_result)
    base_variable_assignment_count /= len(base_statistical_result)
    base_line_comment_count /= len(base_statistical_result)
    base_block_comment_count /= len(base_statistical_result)
    base_branch_count /= len(base_statistical_result)

    refine_line_count /= len(refine_statistical_result)
    refine_assertion_count /= len(refine_statistical_result)
    refine_method_invocation_count /= len(refine_statistical_result)
    refine_variable_assignment_count /= len(refine_statistical_result)
    refine_line_comment_count /= len(refine_statistical_result)
    refine_block_comment_count /= len(refine_statistical_result)
    refine_branch_count /= len(refine_statistical_result)

    avg_base_statistical_result = {
        'line_count': base_line_count,
        'assertion_count': base_assertion_count,
        'method_invocation_count': base_method_invocation_count,
        'variable_assignment_count': base_variable_assignment_count,
        'line_comment_count': base_line_comment_count,
        'block_comment_count': base_block_comment_count,
        'branch_count': base_branch_count,
    }
    avg_refine_statistical_result = {
        'line_count': refine_line_count,
        'assertion_count': refine_assertion_count,
        'method_invocation_count': refine_method_invocation_count,
        'variable_assignment_count': refine_variable_assignment_count,
        'line_comment_count': refine_line_comment_count,
        'block_comment_count': refine_block_comment_count,
        'branch_count': refine_branch_count,
    }
    return avg_base_statistical_result, avg_refine_statistical_result


def print_statistical_result(statistical_result):
    for key, value in statistical_result.items():
        print(f'{key}: {value}')



def main():
    res_dir_list = [
        os.path.join(code_base, 'data', 'd4j_rag_function_2024-09-05-fixed'),
        os.path.join(code_base, 'data', 'd4j_rag_function_2024-09-06-codellama-7b'),
        os.path.join(code_base, 'data', 'd4j_rag_function_2024-09-06-codellama-13b'),
        os.path.join(code_base, 'data', 'd4j_rag_function_2024-09-06-deepseek-33b'),
        os.path.join(code_base, 'data', 'd4j_rag_function_2024-09-06-phind-34b'),
    ]
    for res_dir in res_dir_list:
        print(res_dir.split('/')[-1])
        avg_base_statistical_result, avg_refine_statistical_result = statistical_projects_statement_count(res_dir)
        print('Base:')
        print_statistical_result(avg_base_statistical_result)
        print('Refine:')
        print_statistical_result(avg_refine_statistical_result)
        print('\n')


if __name__ == '__main__':
    main()
