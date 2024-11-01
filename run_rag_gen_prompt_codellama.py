from glob import glob
from tqdm import tqdm
import pickle
from data.configuration import code_base, google_formatter
import time
import os
from collections import defaultdict
from rank_bm25 import BM25Okapi
import json
import subprocess
from transformers import AutoTokenizer


def format_java_code_with_google_format(java_code):
    # Replace 'path/to/google-java-format.jar' with the path to your jar file
    jar_path = google_formatter
    input_code = 'public class Example {\n' + java_code + '\n}'
    
    # Step 1: Run the Google Java Format command with input from stdin
    result = subprocess.run(
        ['java', '-jar', jar_path, '-'],  # The '-' option tells Google Java Format to read from stdin
        input=input_code.encode('utf-8'),  # Provide the Java code as input
        stdout=subprocess.PIPE,  # Capture stdout for the formatted output
        stderr=subprocess.PIPE
    )
    
    # Check for errors
    if result.returncode != 0:
        print(f"Error: {result.stderr.decode('utf-8')}")
        return None

    # Step 2: Decode and return the formatted code
    formatted_code = result.stdout.decode('utf-8').strip()
    formatted_code = formatted_code.replace('public class Example {\n', '')[:-1]
    return formatted_code


def construct_focal_to_test(all_cases):
    focal_to_test_base = defaultdict(set)
    focal_to_test_refine = defaultdict(set)

    for i in tqdm(all_cases):
        single_test_function = pickle.load(open(i, 'rb'))

        focal_method_content = single_test_function.focal_method.method_content
        if focal_method_content is None:
            continue
        
        test_function_content = single_test_function.function_content

        focal_to_test_base[focal_method_content].add(test_function_content)
        
        for single_refined_test in single_test_function.refined_test_functions:
            focal_to_test_refine[focal_method_content].add(single_refined_test.function_content)
    return focal_to_test_base, focal_to_test_refine


def find_retrieved_test_function(query, bm25, all_focal_methods):
    tokenized_query = query.split(" ")
    top_docs = bm25.get_top_n(tokenized_query, all_focal_methods, n=2)
    retrieved_focal_method = top_docs[-1]
    return retrieved_focal_method


def format_prompt(prompts, model_path):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenized_chat = tokenizer.apply_chat_template(prompts, tokenize=True, add_generation_prompt=True, return_tensors="pt")
    formatted_prompt = tokenizer.decode(tokenized_chat[0])
    # print()
    return formatted_prompt
    

def construct_rag_gen_prompt(single_test_function, retrieved_focal_method, retrived_tests, reformatted_dict):
    focal_method_content = single_test_function.focal_method.method_content
    
    if focal_method_content in reformatted_dict:
        focal_method_content = reformatted_dict[focal_method_content]
    else:
        focal_method_content = reformatted_focal_method
    
    retrived_test_content = "\n\n".join(retrived_tests)
    
    code_context = "The focal method you are going to test belongs to the class:\n```java\n// Abstract Java Tested Class\n{be_test_import_context}\n\n{be_test_class_signature} {{\n{be_test_class_field_context}\n\n{be_test_class_function_signature_context}\n}}\n```\n The unit test should be in the test class:\n```java\n// Abstract Java Test Class\n{test_import_context}\n\n{test_class_signature} {{\n{test_class_field_context}\n\n}}\n```"
    
    example_prompt = f"Here is an example of another focal method and its unit tests:\n```java\n// Focal method\n{retrieved_focal_method}\n// Unit tests\n{retrived_test_content}\n```"
    
    task_prompt = f"Please generate unit tests for the focal method:\n```java\n{focal_method_content}\n```"
    
    generation_prompt = f"The generated unit tests are:\n```java\n{single_test_function.test_import_context}"
    
    code_context = code_context.format(
        be_test_import_context=single_test_function.be_test_import_context,
        be_test_class_signature=single_test_function.be_test_class_signature,
        be_test_class_field_context=single_test_function.be_test_class_field_context,
        be_test_class_function_signature_context=single_test_function.be_test_class_function_signature_context,
        test_import_context=single_test_function.test_import_context,
        test_class_signature=single_test_function.test_class_signature,
        test_class_field_context=single_test_function.test_class_field_context,
        test_class_function_signature_context=single_test_function.test_class_function_signature_context
    )
    
    message = [
        {"role": "system", "content": "You are an intelligent programming assistant to help user write Java unit tests."},
        {"role": "user", "content": "\n".join([code_context, example_prompt, task_prompt])},
        {"role": "assistant", "content": generation_prompt}
    ]
    
    return message


if __name__ == "__main__":
    date = time.strftime("%Y-%m-%d", time.localtime())
    date = date + '-code_llama_13b'
    
    model_path = f"{code_base}/vllm_reference/codellama_13b"
    
    all_cases = glob(f'{code_base}/data/d4j_refine_function_2024-09-04/*/*.pkl')
    
    base_res_dir = f'{code_base}/data/d4j_rag_gen_prompt_{date}'
    if os.path.exists(base_res_dir):
        os.system(f'rm -rf {base_res_dir}')
    os.makedirs(base_res_dir, exist_ok=True)

    base_prompt_file = f'{code_base}/vllm_reference/all_rag_gen_base_prompt_{date}.jsonl'
    with open(base_prompt_file, 'w') as fw:
        fw.write('')
    
    refine_prompt_file = f'{code_base}/vllm_reference/all_rag_gen_refine_prompt_{date}.jsonl'
    with open(refine_prompt_file, 'w') as fw:
        fw.write('')
    
    reformatted_res = f'{code_base}/data/reformatted_res_2024-09-04-2.json'
    with open(reformatted_res, 'r') as fr:
        reformatted_dict = json.load(fr)

    focal_to_test_base, focal_to_test_refine = construct_focal_to_test(all_cases)
    
    all_focal_methods = list(focal_to_test_base.keys())
    
    # tokenizer = AutoTokenizer.from_pretrained(model_path)
    # Tokenize the documents
    tokenized_corpus = [doc.split(" ") for doc in all_focal_methods]
    bm25 = BM25Okapi(tokenized_corpus)

    processed_focal_method = set()
    
    for i in tqdm(all_cases):
        single_test_function = pickle.load(open(i, 'rb'))
        function_id = single_test_function.function_id
        
        focal_method_content = single_test_function.focal_method.method_content

        if focal_method_content is None:
            continue
        
        reformatted_focal_method = format_java_code_with_google_format(focal_method_content)
        if reformatted_focal_method is not None:
            reformatted_dict[focal_method_content] = reformatted_focal_method
        else:
            reformatted_dict[focal_method_content] = focal_method_content

        retrieved_focal_method = find_retrieved_test_function(focal_method_content, bm25, all_focal_methods)
        
        if retrieved_focal_method in reformatted_dict:
            reformatted_retrieved_focal_method = reformatted_dict[retrieved_focal_method]
        else:
            reformatted_retrieved_focal_method = format_java_code_with_google_format(retrieved_focal_method)    
            if reformatted_retrieved_focal_method is None:
                reformatted_retrieved_focal_method = retrieved_focal_method   
            reformatted_dict[retrieved_focal_method] = reformatted_retrieved_focal_method

        base_retrived_tests = focal_to_test_base[retrieved_focal_method]
        for tmp_example in base_retrived_tests:
            if tmp_example in reformatted_dict:
                tmp_example = reformatted_dict[tmp_example]
            else:
                reformatted_example = format_java_code_with_google_format(tmp_example)
                if reformatted_example is not None:
                    reformatted_dict[tmp_example] = reformatted_example
                    tmp_example = reformatted_example
                else:
                    reformatted_dict[tmp_example] = tmp_example
        
        refine_retrieved_tests = focal_to_test_refine[retrieved_focal_method]
        for tmp_example in refine_retrieved_tests:
            if tmp_example in reformatted_dict:
                tmp_example = reformatted_dict[tmp_example]
            else:
                reformatted_example = format_java_code_with_google_format(tmp_example)
                if reformatted_example is not None:
                    reformatted_dict[tmp_example] = reformatted_example
                    tmp_example = reformatted_example
                else:
                    reformatted_dict[tmp_example] = tmp_example
        base_prompt = construct_rag_gen_prompt(single_test_function, retrieved_focal_method, base_retrived_tests, reformatted_dict)
        refine_prompt = construct_rag_gen_prompt(single_test_function, retrieved_focal_method, refine_retrieved_tests, reformatted_dict)
        
        # for single_example in base_retrived_tests:
        #     base_prompt = construct_rag_gen_prompt(single_test_function, reformatted_retrieved_focal_method, [single_example], reformatted_dict)
        #     formatted_base_prompt = format_prompt(base_prompt)
        #     single_data = {
        #         "focal_method_content": focal_method_content,
        #         "prompt": formatted_base_prompt
        #     }
        #     with open(base_prompt_file, 'a') as fw:
        #         fw.write(json.dumps(single_data) + '\n')
        
        # for single_example in refine_retrieved_tests:
        #     refine_prompt = construct_rag_gen_prompt(single_test_function, reformatted_retrieved_focal_method, [single_example], reformatted_dict)
        #     formatted_refine_prompt = format_prompt(refine_prompt)
        #     single_data = {
        #         "focal_method_content": focal_method_content,
        #         "prompt": formatted_refine_prompt
        #     }
        #     with open(refine_prompt_file, 'a') as fw:
        #         fw.write(json.dumps(single_data) + '\n')

        single_test_function.gen_from_origin_prompt = base_prompt
        single_test_function.gen_from_refined_prompt = refine_prompt
        
        with open(f'{base_res_dir}/{single_test_function.function_name}.pkl', 'wb') as f:
            pickle.dump(single_test_function, f)
        
        if focal_method_content in processed_focal_method:
            continue
        
        formatted_base_prompt = format_prompt(base_prompt, model_path)
        formatted_base_prompt = formatted_base_prompt.replace('</s>', '')
        single_data = {
            "focal_method_content": focal_method_content,
            "prompt": formatted_base_prompt
        }
        with open(base_prompt_file, 'a') as fw:
            fw.write(json.dumps(single_data) + '\n')

        formatted_refine_prompt = format_prompt(refine_prompt, model_path)
        formatted_refine_prompt = formatted_refine_prompt.replace('</s>', '')
        single_data = {
            "focal_method_content": focal_method_content,
            "prompt": formatted_refine_prompt
        }
        with open(refine_prompt_file, 'a') as fw:
            fw.write(json.dumps(single_data) + '\n')

        processed_focal_method.add(focal_method_content)
    
    # save the dict to json
    with open(reformatted_res, 'w') as fw:
        json.dump(reformatted_dict, fw)