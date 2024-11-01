from transformers import AutoTokenizer
from openai import OpenAI
import re
import sys
sys.path.append('..')
from code_parser import Code_AST
from utils import (read_file, get_indent, fast_multiprocessing)

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

be_test_class_ast = Code_AST(code=example_ast_source, lang="java").ast
be_test_class_ast.print_ast()

# DFS the ast and get the sibling node at each level
def dfs_sibling(node, level=0, siblings=[]):
    if node is None:
        return
    if len(siblings) <= level:
        siblings.append([])
    siblings[level].append(node)
    for child in node.children:
        dfs_sibling(child, level + 1, siblings)
    return siblings

siblings = []
dfs_sibling(be_test_class_ast, 0, siblings)
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