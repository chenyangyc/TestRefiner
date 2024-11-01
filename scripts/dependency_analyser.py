import re
import xml.etree.ElementTree as ET
import os
from data.configuration import defects4j_home

proxy_host = None
proxy_port = None
proxy_username = None
proxy_password = None


xmls = {
    'Chart': 'maven-jfreechart-project.xml',
    'Closure': 'closure-compiler.pom',
    'Codec': 'pom.xml',
    'Collections': 'pom.xml',
    'Compress': 'pom.xml',
    'Csv': 'pom.xml',
    'Gson': 'gson/pom.xml',
    'JacksonCore': 'pom.xml',
    'JacksonDatabind': 'pom.xml',
    'JacksonXml': 'pom.xml',
    'Jsoup': 'pom.xml',
    'Lang': 'pom.xml',
    'Time': 'pom.xml',
    'Math': 'pom.xml',
    'JxPath': 'project.xml',
    # 'Cli': 'project.xml',
    'Cli': 'pom.xml',
    'Mockito': 'build.gradle'
}

dependency_dict = {
    "Cli": (
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-core-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-junit-jupiter-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-params-5.0.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/apiguardian-api-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-api-5.7.2.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-rt.jar\"></pathelement>\n"
        
        ),
    "Chart": (
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-core-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-junit-jupiter-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-api-5.7.2.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-params-5.0.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-api-mockito2-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-core-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/apiguardian-api-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-module-junit4-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-rt.jar\"></pathelement>\n"
    ),
    "Lang": (
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-core-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-junit-jupiter-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-api-5.7.2.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-params-5.0.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-api-mockito2-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-core-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/apiguardian-api-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-module-junit4-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-rt.jar\"></pathelement>\n"
    ),
    "Gson": (
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-core-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-junit-jupiter-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-api-5.7.2.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-params-5.0.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-api-mockito2-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-core-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/apiguardian-api-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-module-junit4-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-rt.jar\"></pathelement>\n"
    ),
    "Csv": (
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-core-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/mockito-junit-jupiter-3.12.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-api-5.7.2.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/junit-jupiter-params-5.0.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-api-mockito2-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-core-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/apiguardian-api-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/powermock-module-junit4-1.7.4.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-1.1.0.jar\"></pathelement>\n"
        "<pathelement location=\"/data/defects4j/framework/projects/lib/evosuite-rt.jar\"></pathelement>\n"
    ),
}

jdk_version_dict = {
    "Cli": "1.7",
    "Chart": "1.7",
    "Lang": "1.4",
    "Gson": "1.7",
    "Csv": "1.7",
    "Codec": "1.7"
}


def add_dependencies(base_dir, bug_id):
    project_name = bug_id.split('_')[0]
    dependency_file_name = 'build.xml'
    # xmls[project_name]
    item_path = os.path.join(base_dir, bug_id)
    # 判断item path是否存在
    if not os.path.exists(item_path):
        print("bug_id path {} does not exit".format(item_path))
        exit(-1)

    directory_paths = [os.path.join(item_path, "fixed")]
    for fixed_directory_path in directory_paths:
        # fixed_directory_path = os.path.join(item_path, "fixed")
        if 'maven-build.xml' in os.listdir(fixed_directory_path):
            dependency_file_name = 'maven-build.xml'
        elif 'build.xml' in os.listdir(fixed_directory_path):
            dependency_file_name = 'build.xml'
        elif 'build-ant.xml' in os.listdir(fixed_directory_path):
            dependency_file_name = 'build-ant.xml'
        if 'Chart' in bug_id:
            dependency_file_name = 'ant/build.xml'
        if 'Gson' in bug_id:
            dependency_file_name = 'gson/maven-build.xml'

        dependency_file_path = os.path.join(fixed_directory_path, dependency_file_name)
        dependency_file_copy_path = dependency_file_path + ".copy"
        if not os.path.exists(dependency_file_copy_path):
            os.system("cp {} {}".format(dependency_file_path, dependency_file_copy_path))

        with open(dependency_file_copy_path, 'r') as file:
            content = file.read()
        new_content = content

        if project_name not in ['Math']:
            jdk_pattern = r"<javac(.*?)</javac>"
            existing_jdk_versions = re.findall(jdk_pattern, new_content, re.DOTALL)
            for single_jdk in existing_jdk_versions:
                target_pattern = r"target=\"(.*?)\""
                target_versions = re.findall(target_pattern, single_jdk, re.DOTALL)

                source_pattern = r"source=\"(.*?)\""
                source_versions = re.findall(source_pattern, single_jdk, re.DOTALL)

                if target_versions and source_versions:
                    target_version = target_versions[0]
                    source_version = source_versions[0]

                    if project_name in jdk_version_dict.keys():
                        new_jdk = single_jdk.replace(target_version, jdk_version_dict[project_name])
                        new_jdk = new_jdk.replace(source_version, jdk_version_dict[project_name])
                    else:
                        new_jdk = single_jdk.replace(target_version, "1.7")
                        new_jdk = new_jdk.replace(source_version, "1.7")

                    new_content = new_content.replace(single_jdk, new_jdk)
                else:
                    continue
        else:
            # 处理math的特殊情况，单独加一下classpath refid这种依赖
            math_pattern = r"<classpath>(.*?)<path refid=\"(.*?)classpath(.*?)\">(.*?)</path>(.*?)</classpath>"
            math_dependencies = re.findall(math_pattern, content, re.DOTALL)

            if len(math_dependencies) != 0:
                new_dependencies = dependency_dict[project_name] if project_name in dependency_dict.keys() else \
                dependency_dict['Chart']
                for single_dependency in math_dependencies:
                    if new_dependencies not in single_dependency[4]:
                        ori = f"<path refid=\"{single_dependency[1]}classpath{single_dependency[2]}\">{single_dependency[3]}</path>{single_dependency[4]}"
                        new_depen = single_dependency[4] + '\n' + new_dependencies
                        after = f"<path refid=\"{single_dependency[1]}classpath{single_dependency[2]}\">{single_dependency[3]}</path>{new_depen}"
                        new_content = new_content.replace(ori, after)
            pass

            config_settings = [
                proxy_host, proxy_port, proxy_username, proxy_password
            ]

            if None not in config_settings:
                proxy_settings = [
                    "<property name=\"proxy.host\" value=\"",
                    "<property name=\"proxy.port\" value=\"",
                    "<property name=\"proxy.username\" value=\"",
                    "<property name=\"proxy.password\" value=\""
                ]
                for i in range(len(proxy_settings)):
                    # 如果本来就有proxy设置
                    if proxy_settings[i] in new_content:
                        new_content = new_content.replace(proxy_settings[i], f"{proxy_settings[i]}{config_settings[i]}")
                    # 如果本来没有设置proxy，就给它加上
                    else:
                        proxy_pattern = r"<property (.*?)/>"
                        proxy_dependencies = re.findall(proxy_pattern, content, re.DOTALL)
                        if proxy_dependencies and len(proxy_dependencies) != 0:
                            ori = f"<property {proxy_dependencies[0]}/>"
                            new_content = new_content.replace(ori, f"{ori}\n{proxy_settings[i]}{config_settings[i]}\"/>\n", 1)
            else:
                pass
        pass

        pattern = r"<path id=\"(.*?)classpath(.*?)\">(.*?)</path>"

        existing_dependencies = re.findall(pattern, content, re.DOTALL)
        if len(existing_dependencies) == 0:
            if 'JxPath' in bug_id:  # ${d4j.home}
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/mockito-core-3.12.4.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/mockito-junit-jupiter-3.12.4.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/junit-jupiter-api-5.7.2.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/junit-jupiter-params-5.0.0.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/byte-buddy-1.14.11.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/byte-buddy-agent-1.14.11.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/objenesis-3.3.jar",
                                            fixed_directory_path + "/target/lib/"))
                os.system("cp {} {}".format(f"{defects4j_home}/framework/projects/lib/hamcrest-2.1.jar",
                                            fixed_directory_path + "/target/lib/"))

        else:
            if 'Mockito' in bug_id:
                for single_dependency in existing_dependencies:
                    new_content = new_content.replace(single_dependency[2], single_dependency[2] + '\n' + \
                                                    f"<fileset dir=\"{defects4j_home}/framework/projects/Mockito/lib\" includes=\"*.jar\" /> \n")

            else:
                new_dependencies = dependency_dict[project_name] if project_name in dependency_dict.keys() else \
                dependency_dict['Chart']
                for single_dependency in existing_dependencies:
                    if new_dependencies not in single_dependency[2]:
                        new_content = new_content.replace(single_dependency[2],
                                                        single_dependency[2] + '\n' + new_dependencies)

        with open(dependency_file_path, 'w') as file:
            file.write(new_content)