import sys
sys.path.extend(['.', '..'])
from scripts.java_parser import (
    parse_import_stmts_from_file_code,
    parse_methods_from_class_node,
    parse_fields_from_class_code,
    parse_classes_from_file_node,
    parse_method_invocation,
    parse_methods_from_class_node_no_deduplication
)

def extract_elements_from_llm_generation(generation: str):
    """
    从LLM的输出结果中分析代码元素，组成测试类
    Args:
        generation: LLM的输出内容
        method_signature: 待测函数签名

    Returns:
        dict:{
                "msg": 提取结果，"success", "no llm output" 或 "no methods in output"
                "methods":[method],
                "imports":[import],
                "fields":[field],
                "classes":[class],
                "uts": [ut],
            }
    """
    # 当LLM有正确输出的时候才进行下一步
    msg = "no llm output"
    imports, fields, classes, methods, uts = [], [], [], [], []
    if generation != "":
        methods, imports, fields, classes = analyze_outputs(generation)
        set_up_methods = [method for method in methods if not method.strip().startswith("@Test")]
        uts = [method for method in methods if method.strip().startswith("@Test")]
        
        remove_uts = []
        for set_up_method in set_up_methods:
            line = set_up_method.split('\n')[0];
            if 'test' in line.lower():
                new_ut = "@Test\n" + set_up_method
                uts.append(new_ut)
                remove_uts.append(set_up_method)
        
        set_up_methods = [method for method in set_up_methods if method not in remove_uts]
        # uts = [method for method in set_up_methods]
        
        msg = "success"

    # 如果没有提取到任何method
    if len(uts) == 0:
        set_up_methods, imports, fields, classes = [], [], [], []
        msg = "no methods in output"
        uts = []

    return {
        "msg": msg,
        "methods": set_up_methods,
        "uts": uts,
        "imports": imports,
        "fields": fields,
        "classes": classes
    }


def analyze_outputs(output_str: str):
    block_dot_lines = []
    lines = output_str.split("\n")
    strategy = "generation"
    if strategy == "generation":
        for id, line in enumerate(lines):
            if line.startswith("```"):
                block_dot_lines.append(id)
    elif strategy == "extend":
        for id, line in enumerate(lines):
            if line.endswith("```") or line.startswith("```"):
                block_dot_lines.append(id)
                pass
            else:
                pass
        pass
    else:
        raise NotImplementedError(
            f"Strategy {strategy} is not supported for analyze_outputs method"
        )
    total_lines = len(lines)
    methods = []
    imports = []
    fields = []
    classes = []
    start = 0
    for id in block_dot_lines:
        if id == 0:
            start = 1
            continue
        cur_block = lines[start: id]
        cur_content = "\n".join(cur_block)
        if lines[id].startswith("```"):
            pass
        else:
            column_id = lines[id].find("```")
            if column_id == -1:
                raise IndexError(f"Failing in finding ``` starters in {lines[id]}")
            else:
                cur_content += lines[id][:column_id]


        # methods.extend(
        #     [i["method_text"] + '@_@' + i['method_name'] for i in parse_methods_from_class_node(cur_content)]
        # )
        methods.extend(
            [i["method_text"] for i in parse_methods_from_class_node(cur_content)]
        )
        imports.extend(parse_import_stmts_from_file_code(cur_content))
        # fields.extend(parse_fields_from_class_code(cur_content, strategy))
        fields.extend(
            [i["declaration_text"] for i in parse_fields_from_class_code(cur_content)]
        )
        classes.extend(parse_classes_from_file_node(cur_content, strategy))
        start = id + 1
        pass

    if start < total_lines:
        if start == 0:
            pass
        else:
            start += 1
        cur_block = lines[start:]
        cur_content = "\n".join(cur_block)
        cur_methods = parse_methods_from_class_node(cur_content)
        if len(cur_methods) != 0:
            methods.extend(
                [i["method_text"] for i in parse_methods_from_class_node(cur_content)]
            )
            imports.extend(parse_import_stmts_from_file_code(cur_content))
            fields.extend(
                [
                    i["declaration_text"]
                    for i in parse_fields_from_class_code(cur_content)
                ]
            )
            classes.extend(parse_classes_from_file_node(cur_content))

    imports = list(set(imports))
    methods = set(methods)
    fields = list(set(fields))

    return methods, imports, fields, classes


def main():
    output = '''
public class TestPeriodType extends TestCase {

    private PeriodType periodType;

    // Setup method to initialize the PeriodType instance
    public void setUp() {
        periodType = new PeriodType("Test", new DurationFieldType[]{DurationFieldType.years(), DurationFieldType.days()}, new int[]{0, 1});
    }

    // Test method for isSupported method
    public void testIsSupported() {
        // Test with a supported DurationFieldType
        assertEquals(true, periodType.isSupported(DurationFieldType.years()));

        // Test with an unsupported DurationFieldType
        assertEquals(false, periodType.isSupported(DurationFieldType.weeks()));

        // Test with null input
        try {
            periodType.isSupported(null);
            fail("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // Expected exception
        }
    }

    // Tear down method to clean up after each test
    public void tearDown() {
        periodType = null;
    }
}
```
This unit test checks if the `isSupported` method correctly identifies whether a given `DurationFieldType` is supported by the `PeriodType` instance. It tests with a supported `DurationFieldType`, an unsupported `DurationFieldType`, and a null input. The test also includes a setup and tear down method to initialize and clean up the `PeriodType` instance for each test.
    '''
    result = extract_elements_from_llm_generation(output)
    print(result)


if __name__ == '__main__':
    main()