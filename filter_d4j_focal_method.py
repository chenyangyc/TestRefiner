import json

with open('/test_refine/data/all_d4j_tests.json', 'r') as fr:
    all_tests = json.load(fr)
    

filtered_tests = []

more_than_one_match = 0
exact_match = 0
no_match = 0

focal_method = set()
for single_test in all_tests:
    test_name = single_test['function_name'].lower()

    match_methods = []
    for single_tested_method in single_test['classmethods']:
        tested_method_name = single_tested_method['be_test_function_name'].lower()
        
        if tested_method_name in test_name:
            match_methods.append(single_tested_method)

    total_match_num = len(match_methods)
    if total_match_num > 1:
        more_than_one_match += 1
    if total_match_num == 0:
        no_match += 1
    
    if total_match_num == 1:
        exact_match += 1
        single_test['focal_method'] = match_methods[0]
        filtered_tests.append(single_test)
        identidier = match_methods[0]['be_test_function_name'] + match_methods[0]['be_test_function_signature']
        if identidier not in focal_method:
            focal_method.add(identidier)
        # else:
        #     print()

print(more_than_one_match)
print(no_match)
print(exact_match)
print(len(filtered_tests))

print(len(focal_method))
with open('/test_refine/data/all_d4j_tests_filtered.json', 'w') as fw:
    json.dump(filtered_tests, fw, indent=4, ensure_ascii=False)
    