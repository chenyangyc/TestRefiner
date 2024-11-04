import os

from tree_sitter import Language, Parser
import tree_sitter_java as tsjava

JAVA_LANGUAGE = Language(tsjava.language(), name='java')
parser = Parser()
parser.set_language(JAVA_LANGUAGE)

code_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

defects4j_home = '/data/defects4j'
defects4j_bin_dir = f'{defects4j_home}/framework/bin/'
defects4j_bin = f'{defects4j_home}/framework/bin/defects4j'
defects4j_projects_base = f'{defects4j_home}/projects_0728'

google_formatter = f'{code_base}/data/google-java-format-1.6-all-deps.jar'

TSDETECTOR_PATH = f'{code_base}/data/TestSmellDetector.jar'

ts_detect_tmp = f'{code_base}/data/temp_dirs/tmp_ts_detect'
os.makedirs(ts_detect_tmp, exist_ok=True)

extract_cov_info_tmp = f'{code_base}/data/temp_dirs/tmp_extract_cov_info'
os.makedirs(extract_cov_info_tmp, exist_ok=True)

execution_tmp_dir = f"{code_base}/data/temp_dirs/tmp_execute_tests"
os.makedirs(execution_tmp_dir, exist_ok=True)

refine_tmp_dir = f"{code_base}/data/temp_dirs/tmp_refine"
os.makedirs(refine_tmp_dir, exist_ok=True)

refine_seed_gen_tmp_dir = f"{code_base}/data/temp_dirs/tmp_refine_seed_gen"
os.makedirs(refine_seed_gen_tmp_dir, exist_ok=True)

process_function_tmp_dir = f"{code_base}/data/temp_dirs/tmp_process_function_res"
os.makedirs(process_function_tmp_dir, exist_ok=True)

SMELL_TYPES = ['Assertion Roulette', 'Conditional Test Logic', 'Constructor Initialization', 'Default Test', 'EmptyTest', 'Exception Catching Throwing', 'General Fixture', 'Mystery Guest', 'Print Statement', 'Redundant Assertion', 'Sensitive Equality', 'Verbose Test', 'Sleepy Test', 'Eager Test', 'Lazy Test', 'Duplicate Assert', 'Unknown Test', 'IgnoredTest', 'Resource Optimism', 'Magic Number Test', 'Dependent Test']


TEST_SMELL_RULES = {
    "Assertion Roulette": "The test case contains more than one assertion statement without an explanation. Assertions in the JUnit framework have an optional first argument to give an explanatory message to the user when the assertion fails. You can add a message to the assertion.",
    
    "Conditional Test Logic": "The test case contains code that may or may not be executed due to branching logic.",
    
    "Magic Number Test": "The test case contains assertion that uses a numeric literal as an argument. You can replace the numeric literal with a variaible declared in advance.",
    
    "Exception Catching Throwing": "The test case contains either a throw statement or a catch clause. You can use @Test(expected) annotation to handle exceptions. Do not use features in Junit 5 such as assertThrows",
    
    "Eager Test": "The test case checks several methods of the object to be tested. You may split the test case and only test one method at a time.",
    
    "Duplicate Assert": "The test case tests for the same condition multiple times within the same test method. You can create new test methods with different values",
    
    "Sensitive Equality": "A test method invokes the toString() method of an object.",
    
    "Constructor Initialization": "A test class that contains a constructor declaration.",
    
    "Default Test": "A test class is named either 'ExampleUnitTest' or 'ExampleInstrumentedTest'.",
    
    "Empty Test": "A test method that does not contain a single executable statement.",
    
    "General Fixture": "Not all fields instantiated within the setUp method of a test class are utilized by all test methods in the same test class.",
    "Ignored Test": "A test method or class that contains the @Ignore annotation.",
    "Lazy Test": "Multiple test methods calling the same production method.",
    
    "Mystery Guest": "A test method containing object instances of files and databases classes.",
    "Redundant Print": "A test method that invokes either the print or println or printf or write method of the System class.",
    "Redundant Assertion": "A test method that contains an assertion statement in which the expected and actual parameters are the same.",
    "Resource Optimism": "A test method utilizes an instance of a File class without calling the method exists(), isFile() or notExists() methods of the object.",
    "Sleepy Test": "A test method that invokes the Thread.sleep() method.",
    "Unknown Test": "A test method that does not contain a single assertion statement and @Test(expected) annotation parameter.",
    
    "Meaningful Naming": "The current names of the test case and the variables are not sufficiently descriptive. Rename the test and the variables to accurately reflect its purpose and behavior.",
    "Annotations and Documentation": "The test case lacks comments or annotations that explain its behavior and intent. Add necessary annotations and comments to improve understanding."
}
