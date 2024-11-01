from openai import OpenAI
import re
import sys
sys.path.append('..')
from code_parser import Code_AST
from utils import (read_file, get_indent, fast_multiprocessing)
import json
from collections import defaultdict
import pickle
import subprocess
from black import format_file_contents, FileMode

example_source = """
public void testDateFormatInMST7MDTTimeZone() throws Exception {
        // Arrange:  Set up the time zone and date format for the test
        TimeZone mountainTimeZone = TimeZone.getTimeZone("MST7MDT");
        TimeZone.setDefault(mountainTimeZone);
        DateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS z");
        dateFormat.setTimeZone(mountainTimeZone);
        Date dateWithTime_01MDT = new Date(1099206000000L);
        Date dateAtMidnightMDT             = new Date(dateWithTime_01MDT.getTime()       - 3600000L);
        Date dateWithTime_01_02MDT       = new Date(dateWithTime_01MDT.getTime()       + 120000L);
        Date dateWithTime_01_02_03MDT    = new Date(dateWithTime_01_02MDT.getTime()    + 3000L);
        Date dateWithTime_01_02_03_04MDT = new Date(dateWithTime_01_02_03MDT.getTime() + 4L);

        // Act & Assert:  Verify that the formatted dates match the expected strings
        assertEquals("Check 00:00:00.000", "2004-10-31 00:00:00.000 MDT", format.format(dateAtMidnightMDT));
        assertEquals("Check 01:00:00.000", "2004-10-31 01:00:00.000 MDT", format.format(dateWithTime_01MDT));
        assertEquals("Check 01:02:00.000", "2004-10-31 01:02:00.000 MDT", format.format(dateWithTime_01_02MDT));
        assertEquals("Check 01:02:03.000", "2004-10-31 01:02:03.000 MDT", format.format(dateWithTime_01_02_03MDT));
        assertEquals("Check 01:02:03.004", "2004-10-31 01:02:03.004 MDT", format.format(dateWithTime_01_02_03_04MDT));
    }
"""

def format_java_code_with_google_format(java_code):
    # Replace 'path/to/google-java-format.jar' with the path to your jar file
    jar_path = 
    
    # Step 1: Run the Google Java Format command with input from stdin
    result = subprocess.run(
        ['java', '-jar', jar_path, '-'],  # The '-' option tells Google Java Format to read from stdin
        input=java_code.encode('utf-8'),  # Provide the Java code as input
        stdout=subprocess.PIPE,  # Capture stdout for the formatted output
        stderr=subprocess.PIPE
    )
    
    # Check for errors
    if result.returncode != 0:
        print(f"Error: {result.stderr.decode('utf-8')}")
        return None

    # Step 2: Decode and return the formatted code
    formatted_code = result.stdout.decode('utf-8')
    return formatted_code


formatted_code = format_java_code_with_google_format(example_source)
print(formatted_code)
exit()

with open('/test_refine/data/d4j_rag_function_test/Time_27/testRemoveNullRemoved2.pkl', 'rb') as fr:
    test_case = pickle.load(fr)
print('')
exit()

    
def extract_specified_node(node, node_type):
    results = set()
    # If the node has children, process them
    if node.children:
        for i, child in enumerate(node.children):
            # Check if the current node is a 'line_comment'
            if child.type == node_type:
                # Add the 'line_comment' node and its siblings to the result
                results.add(child)
            
            results = results.union(extract_specified_node(child, node_type))

    return results


def extract_variables_need_renaming(node, rename_dict):
    all_identifiers = extract_specified_node(node, 'identifier')
    initial_rename_identifiers = [i for i in all_identifiers if i.source in rename_dict]
    filtered_rename_identifiers = []
    
    for single_identifier in initial_rename_identifiers:
        identifier_parent = single_identifier.parent
        
        if identifier_parent.type == 'method_invocation' and single_identifier.origin_node == identifier_parent.origin_node.child_by_field_name('name'):
            continue
        filtered_rename_identifiers.append(single_identifier)
    return filtered_rename_identifiers
   
rename_dict = {
    "format": "yearPartial"
}

comment_test_ast = Code_AST(code=example_source, lang="java").ast
identifiers = extract_variables_need_renaming(comment_test_ast, rename_dict)
# print()
comment_test_ast.print_ast()
exit()
rename_example_function_content = """
/**
 * Tests the {@code replace} method of {@code StrBuilder} with varying matchers.
 * This test verifies that the replace operation works correctly when using a specific
 * matcher ({@code A_NUMBER_MATCHER}) to replace parts of the string with a given replacement
 * string ("***") within specified start and end indices.
 * 
 * The test ensures that the string builder is initially empty and remains empty after
 * the replace operation, confirming that the replace method handles the case correctly.
 */
public void testReplace_StrMatcher_String_int_int_int_VaryMatcher() {
    // Arrange
    StrBuilder sb = new StrBuilder();

    // Act
    sb.replace(A_NUMBER_MATCHER, "***", 0, sb.length(), -1);

    // Assert
    assertEquals("", sb.toString());
}
"""
rename_example_response = """
```json
{
    "testReplace_StrMatcher_String_int_int_int_VaryMatcher": "testReplaceWithVaryingMatchers",
    "sb": "stringBuilder",
}
```
"""

def extract_specified_node(node, node_type):
    results = set()
    # If the node has children, process them
    if node.children:
        for i, child in enumerate(node.children):
            # Check if the current node is a 'line_comment'
            if child.type == node_type:
                # Add the 'line_comment' node and its siblings to the result
                results.add(child)
            
            results = results.union(extract_specified_node(child, node_type))

    return results


def extract_target_variable_names(node):
    variables = extract_specified_node(node, 'variable_declarator')
    variable_names = set()
    for var in variables:
        for child in var.children:
            if child.type == 'identifier':
                variable_names.add(child.source)
                break

    identifiers = extract_specified_node(node, 'identifier')
    identifier_names = set([i.source for i in identifiers])

    target_variable_names = variable_names.intersection(identifier_names)
    return target_variable_names


example_ast_source = """
/**
 * Tests the {@code asWriter} method of {@code StrBuilder} to ensure it correctly writes
 * characters and strings to the underlying {@code StrBuilder} instance.
 * 
 * This test verifies that various write operations using the {@code Writer} returned by
 * {@code asWriter} correctly append the written content to the {@code StrBuilder}, and
 * the final content matches the expected string.
 * 
 * @throws Exception if an error occurs during the test execution
 */
public void testAsWriter() throws Exception {
    // Arrange
    StrBuilder sb = new StrBuilder("base");
    Writer writer = sb.asWriter();

    // Act
    writer.write('l');
    writer.write(new char[] {'i', 'n'});
    writer.write(new char[] {'n', 'e', 'r'}, 1, 2);
    writer.write(" rout");
    writer.write("ping that server", 1, 3);

    // Assert
    assertEquals("baseliner routing", sb.toString());
}
"""

client = OpenAI(
    # api_key="sk-fe4c3f17dfb24913ad5127e37a6acdc6",
    api_key="sk-1130e9ff386e4d6ea9663a1099fdc13b",
    # base_url="https://api.deepseek.com/beta",
    base_url="https://api.deepseek.com",
)

def construct_rename_prompt(target_variables, function_content, test_name):
    prompt = "Please rename the test and the variables in the test case to more descriptive names that reflect their purpose and usage. The test case is:\n```java\n"
    prompt += function_content
    prompt += "\n```\n"
    prompt += "The names that need to be renamed are:\n"
    target_variables = [test_name] + list(target_variables)
    for var in target_variables:
        prompt += f"- {var}\n"
    prompt += '\nProvide the result in json format with the following structure:\n```json\n{\n'
    for var in target_variables:
        prompt += f'    "{var}": "<new_name>",\n'
    prompt += '}\n```'
    return prompt


def rename_on_the_code(node, rename_dict, example_ast_source):
    # Extract all identifiers from the node
    all_identifiers = extract_specified_node(node, 'identifier')

    # Dictionary to store modifications based on byte ranges
    modify_dict = {}
    for identifier in all_identifiers:
        identifier_name = identifier.source
        if identifier_name not in rename_dict:
            continue
        range = (identifier.start_byte, identifier.end_byte)
        modify_dict[range] = rename_dict[identifier_name]

    # Convert the source code into a list of characters for mutable operations
    source_list = list(example_ast_source)

    # Apply the modifications to the source list
    # Note: Need to process ranges in reverse order to avoid issues with shifting indices
    for range, value in sorted(modify_dict.items(), key=lambda x: x[0][0], reverse=True):
        start, end = range
        source_list[start:end] = value

    # Join the list back into a string
    modified_source = ''.join(source_list)
    
    return modified_source


def parse_output(output):
    # Define the regex pattern to match code blocks
    output = output.replace('```java', '```')
    output = output.replace('```json', '```')
    
    pattern = r"```(.*?)```"
    
    # Find all matches in the output
    matches = re.findall(pattern, output, re.DOTALL)
    
    # Return the first match if it exists
    if matches:
        return matches[0]
    else:
        return None

comment_test_ast = Code_AST(code=example_ast_source, lang="java").ast
target_variables = extract_target_variable_names(comment_test_ast)
test_name = comment_test_ast.get_function_name()

rename_prompt = construct_rename_prompt(target_variables, example_ast_source, test_name)
print('=' * 40 + 'Prompt' + '=' * 40)
# print(rename_prompt)

messages = [
    {"role": "user", "content": rename_prompt}
    # {"role": "assistant", "content": "The new test case is:\n```java\n@Test\n", "prefix": True}
]

# response = client.chat.completions.create(
#     model="deepseek-coder",
#     messages=messages,
#     temperature=0.0,
#     # stop=["```"],
# )
# rename_output = response.choices[0].message.content
# print('=' * 40 + 'Response' + '=' * 40)
# print(rename_output)

rename_output = """
```json
{
    "testAsWriter": "testAsWriter_AppendsCorrectly",
    "writer": "strBuilderWriter",
    "sb": "strBuilderInstance"
}
```
"""
json_output = parse_output(rename_output)
rename_dict = json.loads(json_output)
print(rename_dict)

new_test = rename_on_the_code(comment_test_ast, rename_dict, example_ast_source)
print(new_test)
# be_test_class_ast.print_ast()



# # Example of using the function
# line_comments_with_siblings = find_line_comments_with_siblings(be_test_class_ast)

print()
exit()

def parse_output(output):
    # Define the regex pattern to match code blocks
    output = output.replace('```java', '```')
    
    pattern = r"```(.*?)```"
    
    # Find all matches in the output
    matches = re.findall(pattern, output, re.DOTALL)
    
    # Return the first match if it exists
    if matches:
        return matches[0]
    else:
        return None


def reformat_func_name(func_content):
    function_sig = func_content.strip().split('\n')[0]
    new_func_sig = function_sig.split('_split_')[0] + '() {'
    func_content = func_content.replace(function_sig, new_func_sig)
    return func_content

client = OpenAI(
    # api_key="sk-fe4c3f17dfb24913ad5127e37a6acdc6",
    api_key="sk-1130e9ff386e4d6ea9663a1099fdc13b",
    # base_url="https://api.deepseek.com/beta",
    base_url="https://api.deepseek.com",
)

example_function_content = """
public void testReplace_StrMatcher_String_int_int_int_VaryMatcher() {
    StrBuilder sb = new StrBuilder();
    sb.replace(A_NUMBER_MATCHER, "***", 0, sb.length(), -1);
    assertEquals("", sb.toString());
}
"""

example_added_comment = """
/**
 * Tests the {@code replace} method of {@code StrBuilder} with varying matchers.
 * This test verifies that the replace operation works correctly when using a specific
 * matcher ({@code A_NUMBER_MATCHER}) to replace parts of the string with a given replacement
 * string ("***") within specified start and end indices.
 * 
 * The test ensures that the string builder is initially empty and remains empty after
 * the replace operation, confirming that the replace method handles the case correctly.
 */
public void testReplace_StrMatcher_String_int_int_int_VaryMatcher() {
    // Arrange
    StrBuilder sb = new StrBuilder();

    // Act
    sb.replace(A_NUMBER_MATCHER, "***", 0, sb.length(), -1);

    // Assert
    assertEquals("", sb.toString());
}
"""

example_add_comment_prompt = f"Please split the test into three parts following the 'Arrange-Act-Assert' pattern and add docstring for the test. The test case is:\n```java\n{example_function_content}\n```"

example_response = example_added_comment


function_content = """
public void testAsWriter_split_4() throws Exception {
    StrBuilder sb = new StrBuilder("base");
    Writer writer = sb.asWriter();
    writer.write('l');
    writer.write(new char[] {'i', 'n'});
    writer.write(new char[] {'n', 'e', 'r'}, 1, 2);
    writer.write(" rout");
    writer.write("ping that server", 1, 3);
    assertEquals("baseliner routing", sb.toString());
}
"""

print(function_content)
# add_comment_prompt = f"Please add necessary descriptive comments to accurately reflect the test case's intention and behavior. The test case is:\n```java\n{function_content}\n```\nDo not change any code, only add comments."

add_comment_prompt = f"Please split the test into three parts following the 'Arrange-Act-Assert' pattern and add docstring for the test. The test case is:\n```java\n{function_content}\n```"

messages = [
    {"role": "user", "content": example_add_comment_prompt},
    {'role': 'assistant', 'content': example_response},
    {"role": "user", "content": add_comment_prompt},
    # {"role": "assistant", "content": "The new test case is:\n```java\n@Test\n", "prefix": True}
]
response = client.chat.completions.create(
    model="deepseek-coder",
    messages=messages,
    temperature=0.0,
    # stop=["```"],
)
add_comment_output = response.choices[0].message.content
add_comment_test = parse_output(add_comment_output)

print(add_comment_test)


# rename_prompt =f"""Please rename the test and the variables to make them more meaningful to improve understanding. The test case is:
# ```java 
# {add_comment_test}
# ```
# Do not change the variables that are not declared in the test. Do not change the origin statement and structure. Do not change the test input data (string, char, int value, etc.). """

# rename_message = [
#     {"role": "user", "content": rename_prompt},
#     # {"role": "assistant", "content": "The new test case is:\n```java\n@Test\n", "prefix": True}
# ]
# response = client.chat.completions.create(
#     model="deepseek-coder",
#     messages=rename_message,
#     temperature=0.0,
#     # stop=["```"],
# )
# output = response.choices[0].message.content
# output_test = parse_output(output)
# print(output_test)