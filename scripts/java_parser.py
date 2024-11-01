import sys
import os
sys.path.extend([".", ".."])
import json
import pickle
from tree_sitter import Parser, Language
from data.configuration import code_base

JAVA_LANGUAGE = Language(os.path.join(code_base, 'data/build/my-languages.so'), 'java')

def has_branch(tmp_focal_method):
    """
    判断一个给定的函数里是否包含分支，用于计算分支覆盖率
    Args:
        tmp_focal_method (_type_): 给定的函数

    Returns:
        boolean: 是否包含分支
    """
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    focal_method = "public class TmpClass {\n" + tmp_focal_method + "\n}"
    tree = parser.parse(bytes(focal_method, "utf8"))
    query = JAVA_LANGUAGE.query(
        """
        (if_statement )@if
        (for_statement )@for
        (while_statement) @while
        (catch_clause) @catch
        (switch_expression) @sw
        """
    )

    res = query.captures(tree.root_node)
    if len(res) != 0:
        return True
    else:
        return False


def parse_superclass_or_interface_from_class_node(class_str: str):
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    super_class_query = JAVA_LANGUAGE.query("(class_declaration superclass: (_) @supc)")
    tree = parser.parse(bytes(class_str, "utf-8"))
    superclasses = super_class_query.captures(tree.root_node)
    superclasses = [str(sc[0].text, encoding='utf-8') for sc in superclasses]
    interfaces_query = JAVA_LANGUAGE.query("(class_declaration interfaces: (_) @intf)")
    interfaces = interfaces_query.captures(tree.root_node)
    interfaces = [str(sc[0].text, encoding='utf-8') for sc in interfaces]

    return {
        "superclasses": superclasses,
        "interfaces": interfaces
    }


def parse_fields_from_class_code(class_str: str, need_prefix=True):
    """
    Analyze defined fields for given class.
    :param class_str: class code in a string.
    :return: list of field dicts, for eaxmple:
            {
                "field_name": field_name,
                "field_type": field_type,
                "field_modifiers": field_modifiers,
                "declaration_text": declaration_text,
            }
    """
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_class_str = pickle.loads(pickle.dumps(class_str))
    if need_prefix:
        tmp_class_str = "public class TmpClass{\n" + class_str
    tree = parser.parse(bytes(tmp_class_str, "utf-8"))
    rets = []

    field_decl_query = JAVA_LANGUAGE.query(
        """
        (field_declaration 
        (modifiers)@modifiers
            type: (_) @type_name 
            declarator: (variable_declarator name: (identifier)@var_name)
        ) @field_decl
        """
    )

    fields = field_decl_query.captures(tree.root_node)
    if len(fields) % 4 != 0:
        if int(len(fields) / 4) == 0:
            return []
        else:
            fields = fields[: -(len(fields) % 4)]
    num_iter = len(fields) / 4
    for i in range(int(num_iter)):
        field_name = ""
        field_type = ""
        field_modifiers = ""
        declaration_text = ""
        for item in fields[i * 4: (i+ 1) * 4]:
            text = str(item[0].text, encoding="utf-8")
            if item[1] == "modifiers":
                field_modifiers = text
                pass
            elif item[1] == "field_decl":
                declaration_text = text
                # if not text.strip().endswith(';'):
                #     field_name = ""
                #     field_type = ""
                #     field_modifiers = ""
                #     declaration_text = ""
                #     break
                pass
            elif item[1] == "type_name":
                field_type = text
                pass
            elif item[1] == "var_name":
                field_name = text
                pass
            else:
                raise NotImplementedError(f"Unknown query result name {item[1]}")
        if (
                field_name != ""
                and field_modifiers != ""
                and field_type != ""
                and declaration_text != ""
        ):
            rets.append(
                {
                    "field_name": field_name,
                    "field_type": field_type,
                    "field_modifiers": field_modifiers,
                    "declaration_text": declaration_text,
                }
            )

    return rets


def parse_methods_from_class_node(class_str: str, need_prefix=True):
    """
    Analyze methods defined in the class.
    :param class_str:
    :return: list of collected methods. The elements are like:
                    {
                        "method_name": method_name,
                        "method_modifiers": method_modifiers,
                        "method_return_type": method_return_type,
                        "method_body": method_body,
                        "method_text": method_text,
                        "method_start_line": method start line,
                        "method_end_line": method end line
                    }
    """
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_class_str = pickle.loads(pickle.dumps(class_str))
    if need_prefix:
        tmp_class_str = "public class TmpClass{\n" + tmp_class_str
    tree = parser.parse(bytes(tmp_class_str, "utf-8"))
    rets = []

    method_query = JAVA_LANGUAGE.query(
        """
        (method_declaration) @method_decl
        """
    )

    methods = method_query.captures(tree.root_node)
    unique_methods = set()
    method_attr_query = JAVA_LANGUAGE.query(
        """
        (method_declaration [
            (modifiers) @modifier
            type:(_) @ret_type
            name:(identifier) @name
            body:(block) @body
            ])
        """
    )
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    documents = methods = method_query.captures(tree.root_node)
    
    for index, (method_node, _) in enumerate(methods):
        attrs = method_attr_query.captures(method_node)
        if len(attrs) % 4 != 0:
            continue
        num_iter = int(len(attrs) / 4)
        for i in range(num_iter):
            assert attrs[i * 4 + 1][1] == "ret_type"
            method_text = str(method_node.text, encoding="utf-8")
            method_return_type = str(attrs[i * 4 + 1][0].text, encoding="utf-8")
            method_name = str(attrs[i * 4 + 2][0].text, encoding="utf-8")
            method_modifiers = str(attrs[i * 4][0].text, encoding="utf-8")
            method_body = str(attrs[i * 4 + 3][0].text, encoding="utf-8")
            method_start = method_node.start_point[0]
            method_end = method_node.end_point[0]
            try:
                document = documents[index][0].text + '\n'
            except:
                document = ''
            if method_body not in unique_methods and method_body.strip() != "":
                unique_methods.add(method_body)
                rets.append(
                    {
                        "method_name": method_name,
                        "method_modifiers": method_modifiers,
                        "method_return_type": method_return_type,
                        "method_body": method_body,
                        "method_text": document + method_text,
                        "method_start_line": method_start,
                        "method_end_line": method_end,
                    }
                )

    return rets

def parse_methods_from_class_node_no_deduplication(class_str: str, need_prefix=True):
    """
    Analyze methods defined in the class.
    :param class_str:
    :return: list of collected methods. The elements are like:
                    {
                        "method_name": method_name,
                        "method_modifiers": method_modifiers,
                        "method_return_type": method_return_type,
                        "method_body": method_body,
                        "method_text": method_text,
                        "method_start_line": method start line,
                        "method_end_line": method end line
                    }
    """
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_class_str = pickle.loads(pickle.dumps(class_str))
    if need_prefix:
        tmp_class_str = "public class TmpClass{\n" + tmp_class_str
    tree = parser.parse(bytes(tmp_class_str, "utf-8"))
    rets = []

    method_query = JAVA_LANGUAGE.query(
        """
        (method_declaration) @method_decl
        """
    )

    methods = method_query.captures(tree.root_node)
    method_attr_query = JAVA_LANGUAGE.query(
        """
        (method_declaration [
            (modifiers) @modifier
            type:(_) @ret_type
            name:(identifier) @name
            body:(block) @body
            ])
        """
    )
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    for method_node, _ in methods:
        attrs = method_attr_query.captures(method_node)
        if len(attrs) % 4 != 0:
            continue
        num_iter = int(len(attrs) / 4)
        for i in range(num_iter):
            assert attrs[i * 4 + 1][1] == "ret_type"
            method_text = str(method_node.text, encoding="utf-8")
            method_return_type = str(attrs[i * 4 + 1][0].text, encoding="utf-8")
            method_name = str(attrs[i * 4 + 2][0].text, encoding="utf-8")
            method_modifiers = str(attrs[i * 4][0].text, encoding="utf-8")
            method_body = str(attrs[i * 4 + 3][0].text, encoding="utf-8")
            method_start = method_node.start_point[0]
            method_end = method_node.end_point[0]
            if  method_body.strip() != "":
                rets.append(
                    {
                        "method_name": method_name,
                        "method_modifiers": method_modifiers,
                        "method_return_type": method_return_type,
                        "method_body": method_body,
                        "method_text": method_text,
                        "method_start_line": method_start,
                        "method_end_line": method_end,
                    }
                )

    return rets


def parse_classes_from_file_node(file_code: str, strategy="generation"):
    """
    处理一下生成的代码中的inner classes
    :param file_code: 生成的code
    :return: inner classes as a list of strings.
    """
    rets = []
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_file_code = pickle.loads(pickle.dumps(file_code))
    if strategy == "extend":
        tmp_file_code = "public class TmpClass {\n" + file_code
    tree = parser.parse(bytes(tmp_file_code, "utf-8"))
    class_decl_query = JAVA_LANGUAGE.query(
        """
        (class_declaration) @class_decl
        """
    )
    classes = class_decl_query.captures(tree.root_node)
    if len(classes) == 1 or len(classes) == 0:
        pass
    else:
        for class_str in classes:
            modifier_nodes = [
                str(node.text, encoding="utf-8")
                for node in class_str[0].children
                if node.type == "modifiers"
            ]
            if len(modifier_nodes) != 1 and len(modifier_nodes) != 0:
                num_modifiers = len(modifier_nodes)
                raise IndexError(
                    f"number of modifiers should be 1, but was {num_modifiers}"
                )
            else:
                if len(modifier_nodes) == 1:
                    modifier_nodes = modifier_nodes[0]
                    # 去掉public的类
                    if "public" not in modifier_nodes:
                        rets.append(str(class_str[0].text, encoding="utf-8"))
                else:
                    rets.append(str(class_str[0].text, encoding="utf-8"))

    return rets


def parse_import_stmts_from_file_code(file_code: str):
    """
    从给定的代码文件内容中提取import。为了避免噪音，需要满足两个条件：
    1. import语句必须是分号结尾
    2. import语句至多含有三个以空格区分的token

    Args:
        file_code (str): 输入的代码文件内容（最好是代码文件，其他文件中可能会被过滤掉）

    Returns:
        list: 从输入内容中提取出的import strings
    """
    rets = []
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tree = parser.parse(bytes(file_code, "utf-8"))
    import_decl_query = JAVA_LANGUAGE.query(
        """
    (import_declaration) @import_decl
    """
    )
    imports = import_decl_query.captures(tree.root_node)
    for import_stmt, _ in imports:
        import_stmt = str(import_stmt.text, encoding="utf-8")
        tks = import_stmt.split()
        if import_stmt.endswith(";") and (len(tks) == 2 or len(tks) == 3):
            rets.append(import_stmt)
    return rets


def parse_import_nodes_from_file_code(file_code: str):
    """
    从给定的代码文件内容中提取import node节点信息。为了避免噪音，需要满足两个条件：
    1. import语句必须是分号结尾
    2. import语句至多含有三个以空格区分的token

    Args:
        file_code (str): 输入的代码文件内容（最好是代码文件，其他文件中可能会被过滤掉）

    Returns:
        list: 从输入内容中提取出的import node信息，例如：
            {
                'start':import_node.start_point[0],
                'end':import_node.end_point[0],
                'text':import_stmt
            }
    """
    rets = []
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tree = parser.parse(bytes(file_code, "utf-8"))
    import_decl_query = JAVA_LANGUAGE.query(
        """
    (import_declaration) @import_decl
    """
    )
    imports = import_decl_query.captures(tree.root_node)
    for import_node, _ in imports:
        import_stmt = str(import_node.text, encoding="utf-8")
        tks = import_stmt.split()
        if import_stmt.endswith(";") and (len(tks) == 2 or len(tks) == 3):
            rets.append(
                {
                    "start": import_node.start_point[0],
                    "end": import_node.end_point[0],
                    "text": import_stmt,
                }
            )
    return rets


def parse_param_declaration_from_method_code(method_code: str):
    """
    Analyze method parameters' types and names
    :param method_code: input method, usually focal method
    :return: a dict in which the keys are parameter names, and the values are corresponding types.
    """
    params = {}
    tmp_method_code = "public class TmpClass {\n" + method_code + "}\n"
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tree = parser.parse(bytes(tmp_method_code, "utf-8"))
    method_param_query = JAVA_LANGUAGE.query(
        """
    (class_declaration 
    body: (class_body
    (method_declaration 
    parameters: (formal_parameters
    (formal_parameter 
    type: (_) @type_identifier
    name: (identifier) @param_name )
    ))))
    (class_declaration 
    body: (class_body
    (method_declaration 
    parameters: (formal_parameters
    (_
    (type_identifier) @type_identifier
    (variable_declarator name: (_) @param_name))
    ))))
    
    """
    )
    res = method_param_query.captures(tree.root_node)
    for type_iden, param_name in zip(res[0::2], res[1::2]):
        params[str(param_name[0].text, encoding="utf-8")] = str(
            type_iden[0].text, encoding="utf-8"
        )
    return params


def parse_method_invocation(method_code: str):
    """
    分析给定的函数中的其他函数调用情况

    Args:
        method_code (str): 给定的函数实现，通常是大模型生成的UT

    Returns:
        list<dict>: 返回一个字典的list，每个字典包含以下键值对：
            - invocation: 整体的函数调用字符串
            - invocator: 调用者的标识符，这里如果有package，也会放到一起返回
            - invoked_method_name: 被调用的方法的方法名
            - invocation_args: 被调用方法的参数列表，注意这里是带括号的实际传入参数的字符串
    """
    ret = []  # 定义一个空列表用于存储解析结果
    tmp_method_code = (
            "public class TmpClass {\n" + method_code + "}\n"
    )  # 将输入的方法代码定义到一个临时类中
    parser = Parser()  # 创建一个解析器对象
    parser.set_language(JAVA_LANGUAGE)  # 设置解析器的语言为Java
    tree = parser.parse(bytes(tmp_method_code, "utf-8"))  # 解析临时类的方法代码，生成语法树
    # 定义一个查询语句，用于匹配方法调用
    method_invocation_query = JAVA_LANGUAGE.query(
        """
    (method_invocation 
    object: (_) @object
    name: (_) @methodNname
    arguments: (_) @args
    ) @invoke
    """
    )

    invocations = method_invocation_query.captures(tree.root_node)  # 在语法树中查找所有方法调用
    if len(invocations) % 4 != 0:  # 如果调用次数不能被4整除，则跳过此次循环
        pass
    else:
        num_iter = int(len(invocations) / 4)  # 调用次数除以4得到循环次数
        for i in range(num_iter):  # 循环处理每个方法调用
            invocation_str = str(
                invocations[i * 4][0].text, encoding="utf-8"
            )  # 获取调用的字符串形式
            invocator_obj = str(
                invocations[i * 4 + 1][0].text, encoding="utf-8"
            )  # 获取调用者对象的字符串形式
            invocated_method_name = str(
                invocations[i * 4 + 2][0].text, encoding="utf-8"
            )  # 获取被调用方法的字符串形式
            invocation_args = str(
                invocations[i * 4 + 3][0].text, encoding="utf-8"
            )  # 获取调用的参数字符串形式
            ret.append(  # 将解析结果添加到列表中
                {
                    "invocation": invocation_str,  # 调用信息
                    "invocator": invocator_obj,  # 调用者对象
                    "invoked_method_name": invocated_method_name,  # 被调用方法
                    "invocation_args": invocation_args,  # 调用参数
                }
            )
        pass
    return ret  # 返回解析结果列表


def test_parse_fields_from_class_node():
    input_1 = 'public static String [] name = "";\n public static Integer[] name2 = [];\n\npublic void getNmae(String name1, String name2){ System.out.println("Hello World");}'
    input_1 = 'public static String [] name = "";\n public static Integer[] name2 = [];\n\npublic void getNmae(String name1, String name2){ System.out.println("Hello World");}\n public void testSomething { int a=new Int'
    input_2 = "This is a simple JUnit test for the `generateToolTipFragment` method. It tests the method with normal text, text with special characters, empty text, and null text. The expected results are hardcoded and compared with the actual results from the method. If the actual results match the expected results, the test passes. If not, the test fails.\n<|EOT|>"
    fields = parse_fields_from_class_code(input_1)
    assert len(fields) == 2
    # assert fields[0]["field_name"] == "name"
    # assert fields[1]["field_name"] == "name2"
    fields = parse_fields_from_class_code(input_2)
    input_3 = ""
    assert len(fields) == 0
    print("pass test: parse_field_from_class_node")

    pass


def test_parse_import_from_text():
    input_1 = 'import org.junit.Assertion.*;\n public static String [] name = "";\n public static Integer[] name2 = [];\n\npublic void getNmae(String name1, String name2){ System.out.println("Hello World");}'
    input_2 = "This is a simple JUnit test for the `generateToolTipFragment` method. Please make sure you import this class properly. It tests the method with normal text, text with special characters, empty text, and null text. The expected results are hardcoded and compared with the actual results from the method. If the actual results match the expected results, the test passes. If not, the test fails.\n<|EOT|>"
    imports = parse_import_stmts_from_file_code(input_1)
    assert len(imports) == 1
    imports = parse_import_stmts_from_file_code(input_2)
    assert len(imports) == 0
    print("pass test_parse_imports_from_text")
    pass


def test_match():
    with open(
            "/home/yanglin/data/code-bot/data/fixed_projects_source/Cli/Cli_1_fixed.jsonl",
            "r",
            encoding="utf-8",
    ) as reader:
        for line in reader.readlines():
            line = line.strip()
            obj = json.loads(line)
            assert len(obj.keys()) == 1
            for key in obj.keys():
                tmp_obj = obj[key]
                print("\n".join([tmp_key for tmp_key in tmp_obj.keys()]))
                if len(tmp_obj["testMethodSignature"]) != 0:
                    print(tmp_obj["testMethodSignature"])
    pass


def test_parse_method_invocation_from_method_str():
    method = '@Test\n    public void testGenerateToolTipFragment_withNormalText() {\n        String toolTipText = "This is a normal text";\n        String expectedResult = " title=\\"This is a normal text\\" alt=\\"\\"";\n        String actualResult = standardToolTipTagFragmentGenerator.generateToolTipFragment(toolTipText);\n        Assert.assertEquals(expectedResult, actualResult);\n    }\n\n'
    res = parse_method_invocation(method)
    assert len(res) == 2
    method = '@Test\n    public void testGenerateToolTipFragment_withNormalText() {\n        String toolTipText = "This is a normal text";\n        String expectedResult = " title=\\"This is a normal text\\" alt=\\"\\"";\n        String actualResult = standardToolTipTagFragmentGenerator.generateToolTipFragment();\n        Assert.assertEquals(expectedResult, actualResult);\n    }\n\n'
    res = parse_method_invocation(method)
    assert len(res) == 2 and res[0]["invocation_args"] == "()"
    print("pass test: test_parse_method_invocation_from_method_str")


def test_parse_method_from_class_node():
    output = '\n    private StandardToolTipTagFragmentGenerator standardToolTipTagFragmentGenerator;\n\n    @Before\n    public void setUp() {\n        standardToolTipTagFragmentGenerator = new StandardToolTipTagFragmentGenerator();\n    }\n\n    @Test\n    public void testGenerateToolTipFragment_withNormalText() {\n        String toolTipText = "This is a normal text";\n        String expectedResult = " title=\\"This is a normal text\\" alt=\\"\\"";\n        String actualResult = standardToolTipTagFragmentGenerator.generateToolTipFragment(toolTipText);\n        Assert.assertEquals(expectedResult, actualResult);\n    }\n\n   \n}\n```\nThis is a simple JUnit test for the `generateToolTipFragment` method. It tests the method with normal text, text with special characters, empty text, and null text. The expected results are hardcoded and compared with the actual results from the method. If the actual results match the expected results, the test passes. If not, the test fails.\n<|EOT|>'
    methods = parse_methods_from_class_node(output)
    assert len(methods) == 2
    assert methods[0]["method_name"] == "setUp"
    assert methods[1]["method_name"] == "testGenerateToolTipFragment_withNormalText"

    output = "### Test 1: Remove Domain Marker\n\n* Test case: Remove a domain marker from the plot\n* Expected result: The domain marker should be removed from the plot\n\n```\n@Test\npublic void testRemoveDomainMarker() {\n    // Arrange\n    CategoryPlot plot = new CategoryPlot();\n    Marker marker = new Marker();\n    plot.addDomainMarker(marker);\n\n    // Act\n    boolean result = plot.removeDomainMarker(marker);\n\n    // Assert\n    assertTrue(result);\n    assertFalse(plot.getDomainMarkers().contains(marker));\n}\n```\n\n### Test 2: Remove Domain Marker with Index\n\n* Test case: Remove a domain marker from the plot using the index\n* Expected result: The domain marker should be removed from the plot\n\n```\n@Test\npublic void testRemoveDomainMarkerWithIndex() {\n    // Arrange\n    CategoryPlot plot = new CategoryPlot();\n    Marker marker = new Marker();\n    plot.addDomainMarker(marker);\n\n    // Act\n    boolean result = plot.removeDomainMarker(0);\n\n    // Assert\n    assertTrue(result);\n    assertFalse(plot.getDomainMarkers().contains(marker));\n}\n```\n\nrs().contains(marker));\n}\n```\n\n### Test 6: Remove Domain Marker with Null Marker and Layer\n\n* Test case: Remove a"
    methods = parse_methods_from_class_node(output)
    assert len(methods) == 2
    assert methods[0]["method_name"] == "testRemoveDomainMarker"
    assert methods[1]["method_name"] == "testRemoveDomainMarkerWithIndex"

    output = '\n    private StandardToolTipTagFragmentGenerator standardToolTipTagFragmentGenerator;\n\n    @Before\n    public void setUp() {\n        standardToolTipTagFragmentGenerator = new StandardToolTipTagFragmentGenerator();\n    }\n\n    @Test\n    public void testGenerateToolTipFragment_withNormalText() {\n        String toolTipText = "This is a normal text";\n        String expectedResult = " title=\\"This is a normal text\\" alt=\\"\\"";\n        String actualResult = standardToolTipTagFragmentGenerator.generateToolTipFragment(toolTipText);\n        Assert.assertEquals(expectedResult, actualResult);\n```\nThis is a simple JUnit test for the `generateToolTipFragment` method. It tests the method with normal text, text with special characters, empty text, and null text. The expected results are hardcoded and compared with the actual results from the method. If the actual results match the expected results, the test passes.'
    methods = parse_methods_from_class_node(output)
    assert len(methods) == 1
    output = '\n    private StandardToolTipTagFragmentGenerator standardToolTipTagFragmentGenerator;\n\n    @Before\n    public void setUp() {\n        standardToolTipTagFragmentGenerator = new StandardToolTipTagFragmentGenerator();\n    }\n\n    @Test\n    public void testGenerateToolTipFragment_withNormalText() {\n        String toolTipText = "This is a normal text";\n        String expectedResult = " title=\\"This is a normal text\\" alt=\\"\\"";\n        String actualResult = standardToolTipTagFragmentGenerator.generateToolTipFragment(toolTipText);\n        Assert.assertEquals(expectedResult, actualR\n```\nThis is a simple JUnit test for the `generateToolTipFragment` method. It tests the method with normal text, text with special characters, empty text, and null text. The expected results are hardcoded and compared with the actual results from the method. If the actual results match the expected results, the test passes.'
    methods = parse_methods_from_class_node(output)
    assert len(methods) == 1

    output = '\n    private StandardToolTipTagFragmentGenerator standardToolTipTagFragmentGenerator;\n\n  @Before\n    public void setUp() {\n        standardToolTipTagFragmentGenerator;    } @BeforeEach\n public void setUpBeforeEach(){}   @Before\n    public void setUp() {\n        standardToolTipTagFragmentGenerator = new StandardToolTipTagFragmentGenerator();\n    }\n\n  @Before\n    public void setUp1() {\n        standardToolTipTagFragmentGenerator = new StandardToolTipTagFragmentGenerator();\n    }   @Test\n    public void testGenerateToolTipFragment_withNormalText() {\n        String toolTipText = "This is a normal text";\n        String expectedResult = " title=\\"This is a normal text\\" alt=\\"\\"";\n        String actualResult = standardToolTipTagFragmentGenerator.generateToolTipFragment(toolTipText);\n        Assert.assertEquals(expectedResult, actualResult);\n    }\n\n   \n}\n```\nThis is a simple JUnit test for the `generateToolTipFragment` method. It tests the method with normal text, text with special characters, empty text, and null text. The expected results are hardcoded and compared with the actual results from the method. If the actual results match the expected results, the test passes. If not, the test fails.\n<|EOT|>'
    methods = parse_methods_from_class_node(output)
    assert len(methods) == 4

    output = "public class tmpClass{\n\n    @Test\n    public void testEqual_NullLines() {\n        Line2D l1 = null;\n        Line2D l2 = null;\n        boolean expected = true;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NullLineAndNonNullLine() {\n        Line2D l1 = null;\n        Line2D l2 = new Line2D.Double(1, 2, 3, 4);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLineAndNullLine() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = null;\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLines() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(1, 2, 3, 4);\n        boolean expected = true;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentStartPoints() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(4, 5, 6, 7);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentEndPoints() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(1, 2, 5, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlope() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(1, 4, 3, 2);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentYIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(1, 2, 3, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentXIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 2, 3, 4);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 3, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndXIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 2, 4, 4);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPoint() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPoint() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlope() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentYIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentXIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentStartPoint() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentEndPoint() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndYIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndXIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndYInterceptAndXIntercept() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndYInterceptAndXInterceptAndStartPoint() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPoint() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlope() {\n        Line2D l1 = new Line2D.Double(1, 2, 3, 4);\n        Line2D l2 = new Line2D.Double(2, 4, 4, 6);\n        boolean expected = false;\n        boolean actual = ShapeUtilities.equal(l1, l2);\n        Assert.assertEquals(expected, actual);\n    }\n\n    @Test\n    public void testEqual_NonNullLinesWithDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentSlopeAndYInterceptAndXInterceptAndStartPointAndEndPointAndDifferentYIntercept()\n\n"
    methods = parse_methods_from_class_node(output)

    output = "@Test\npublic void testEqual()"
    methods = parse_methods_from_class_node(output)
    print("pass test: parse_method_from_class_node")


def test_parse_parameters_from_method_code():
    method_code = """
        public void myMethod(int param1, String param2, boolean param3) {
            // method code
        }
    """
    expected_result = {"param1": "int", "param2": "String", "param3": "boolean"}

    result = parse_param_declaration_from_method_code(method_code)
    assert result == expected_result

    method_code = """
        public void myMethod(int[] param1, String... param2, boolean param3) {
            // method code
        }
    """
    expected_result = {"param1": "int[]", "param2": "String", "param3": "boolean"}
    result = parse_param_declaration_from_method_code(method_code)
    assert expected_result == result

def test_parse_superclasses_and_implements():
    str_ = ("public class ABC extends BCD implements Abc, Bcd {}")
    res = parse_superclass_or_interface_from_class_node(str_)
    print(res)

if __name__ == "__main__":
    # test_parse_method_invocation_from_method_str()
    # test_parse_method_from_class_node()
    test_parse_fields_from_class_node()
    # test_parse_import_from_text()
    # test_parse_parameters_from_method_code()
    # test_parse_superclasses_and_implements()
    pass
