import json

with open('/data/yangchen/test_refine/data/all_d4j_tests_filtered.json', 'r') as fr:
    all_tests = json.load(fr)

multi_assertion_tests = []

for single_test in all_tests:
    func_content = single_test['function']
    func_lines = func_content.split('\n')
    assert_cnt = sum([1 for line in func_lines if 'assert' in line.lower()])
    
    if assert_cnt > 1:
        multi_assertion_tests.append(single_test)

print(len(multi_assertion_tests))

# with open('/data/yangchen/test_refine/data/task_testgen_multi_assertions.json', 'w') as fw:
#     json.dump(multi_assertion_tests, fw, indent=4)