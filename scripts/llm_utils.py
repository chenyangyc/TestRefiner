import random
from transformers import AutoTokenizer
from data.configuration import TEST_SMELL_RULES

# random.seed(42)
# tokenizer = AutoTokenizer.from_pretrained("gpt2")

def get_code_context(be_test_import_context, be_test_class_signature, 
                    be_test_class_field_context, be_test_class_function_signature_context,
                    test_import_context, test_class_signature, 
                    test_class_field_context, test_class_function_signature_context,
                    context_length, is_evo):
    code_context = "// Abstract Java Tested Class\n{be_test_import_context}\n\n{be_test_class_signature} {{\n{be_test_class_field_context}\n\n{be_test_class_function_signature_context}\n}}\n\n// Abstract Java Test Class\n{test_import_context}\n\n{test_class_signature} {{\n{test_class_field_context}\n\n{test_class_function_signature_context}\n}}"
    
    if is_evo:
        test_class_function_signature_context = ''
   
    code_context = code_context.format(
        be_test_import_context=be_test_import_context,
        be_test_class_signature=be_test_class_signature,
        be_test_class_field_context=be_test_class_field_context,
        be_test_class_function_signature_context=be_test_class_function_signature_context,
        test_import_context=test_import_context,
        test_class_signature=test_class_signature,
        test_class_field_context=test_class_field_context,
        test_class_function_signature_context=test_class_function_signature_context
    )
    code_context = code_context.strip()
    # cut_code_context = tokenizer.convert_tokens_to_string(tokenizer.tokenize(code_context)[-context_length:])
    # cut = cut_code_context != code_context
    # return cut, cut_code_context
    return False, code_context


def construct_few_shot_prompt(few_shot_function, context_option=None, context_length=2048, is_evo=True):
    if context_option is None:
        context_option = {
            "few_shot": -1,
            "be_test_import_context": True,
            "be_test_class_signature": True,
            "be_test_class_field_context": True,
            "be_test_class_function_signature_context": True,
            "test_import_context": True,
            "test_class_signature": True,
            "test_class_field_context": True,
            "test_class_function_signature_context": True
        }
    be_test_import_context = few_shot_function.be_test_import_context if context_option["be_test_import_context"] else ""
    be_test_class_signature = few_shot_function.be_test_class_signature if context_option["be_test_class_signature"] else ""
    be_test_class_field_context = few_shot_function.be_test_class_field_context if context_option["be_test_class_field_context"] else ""
    be_test_class_function_signature_context = few_shot_function.be_test_class_function_signature_context if context_option["be_test_class_function_signature_context"] else ""
    test_import_context = few_shot_function.test_import_context if context_option["test_import_context"] else ""
    test_class_signature = few_shot_function.test_class_signature if context_option["test_class_signature"] else ""
    test_class_field_context = few_shot_function.test_class_field_context if context_option["test_class_field_context"] else ""
    test_class_function_signature_context = few_shot_function.test_class_function_signature_context if context_option["test_class_function_signature_context"] else ""
        
        
    becut, code_context = get_code_context(be_test_import_context, be_test_class_signature,
                                            be_test_class_field_context, be_test_class_function_signature_context,
                                            test_import_context, test_class_signature,
                                            test_class_field_context, test_class_function_signature_context,
                                            context_length, is_evo)

    if becut:
        code_context = "\n".join(code_context.split("\n")[1:])

    comment = few_shot_function.function_comment
    
    prompt_template = """```java\n{code_context}\n```\n\nPlease create a test case for the `{be_test_class_name}` class. Here is an example test case: \n```java\n{few_shot_content}\n```\nPlease create new test case according to the provided context information and the example. """
    
    prompt = prompt_template.format(
        code_context=code_context,
        be_test_class_name=few_shot_function.be_test_class_name,
        few_shot_content=f'{few_shot_function.function_content}'
    )
    return prompt


def construct_refine_prompt(basic_function):
    prompt_template = """The given test case has several issues that need addressing to improve its quality and readability:\n\n{smell_content}\n\nPlease refactor the test case to address these issues while ensuring that its original functionality remains intact. The test case is\n```java\n{function_content}\n```\n"""
    
    used_smells = []
    if basic_function.smell_types is not None:
        for smell_type, occurance in basic_function.smell_types.items():
            if occurance > 0:
                if 'Sensitive Equality' in smell_type:
                    continue
                used_smells.append(smell_type)
    
    used_smells.append("Meaningful Naming")
    used_smells.append("Annotations and Documentation")

    smell_content = '\n'.join([f'{str(index + 1)}. {i}: {TEST_SMELL_RULES[i]}' for index, i in enumerate(used_smells)])

    prompt = prompt_template.format(smell_content=smell_content, function_content=basic_function.function_content)
    prompt += "Note that do not modify the original code logic or introduce new classes that are not present in the original code. Provide merely the refined test case. Do not provide one complete test class!"
    return prompt