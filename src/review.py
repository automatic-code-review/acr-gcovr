import os
import shutil
import subprocess
import re
import json
import automatic_code_review_commons as commons
from enum import Enum
import glob
import uuid

class BuildSystem(Enum):
    QMAKE = "qmake"
    CMAKE = "cmake"

BUILD_FILES = {
    BuildSystem.QMAKE: "*.pro",
    BuildSystem.CMAKE: "CMakeLists.txt"
}    

def review(config):    
    path_source = config['path_source']
    comment_description = str(config['message'])    
    minimum_coverage = config["configs"]["minimumCoverage"]
    minimum_coverage_by_project = config["configs"]["minimumCoverageByProject"]
    build_system = config["configs"]["buildSystem"]
    identify_test_class = config["configs"]["identifyTestClass"]
    only_new_files = config["configs"]["onlyNewFiles"]
    changes = config['merge']['changes']
    
    comments = []

    gcovr_run_path = "/tmp/gcovr-"+str(uuid.uuid4())

    os.makedirs(gcovr_run_path, exist_ok=True)          

    for change in changes:
        __remove_files(gcovr_run_path)

        if change['deleted_file']:
            continue

        if only_new_files and not change['new_file']:
            continue

        file_path = change['new_path']
        if not file_path.lower().endswith((".h", ".cpp")):
            continue

        if identify_test_class in file_path:
            file_path = __search_source_file_by_test_file(path_source, file_path)
            if not file_path:
                continue

        class_name = _class_name(file_path)
        class_name_without_extension = __remove_extension_file(class_name)
        
        root_path = __search_project_root(build_system, path_source, file_path, class_name)
        if not root_path:
            comments.append(__generate_comment(file_path, "diretório root não foi encontrado"))
            continue

        files_to_generate_coverage = __search_files_in_directory((class_name_without_extension+".gcda", class_name_without_extension+".gcno"), root_path)
        if not files_to_generate_coverage:
            continue

        for file in files_to_generate_coverage:
            shutil.copy(file, gcovr_run_path)

        filter_path = ".*"+os.path.relpath(path_source+"/"+__remove_extension_file(file_path), root_path)+".*"
        json_output = class_name_without_extension+".json"    
        command = f'gcovr --root {root_path} --filter "{filter_path}" --json-summary {json_output} {gcovr_run_path}'
        result = subprocess.run(command, shell=True, cwd=gcovr_run_path, capture_output=True, text=True)

        if result.returncode == 0:
            percent = __process_json(gcovr_run_path+"/"+json_output, class_name)
            minimum, warning = __minimum_coverage_verify(path_source+"/"+file_path, minimum_coverage, minimum_coverage_by_project)
            if percent < minimum:
                comment_description = comment_description.replace("${PERCENT_MINIMUM_COVERAGE}", str(minimum))
                comment_description = comment_description.replace("${PERCENT_COVERAGE}", str(percent))
                if warning:
                    comment_description += warning
                comments.append(__generate_comment(file_path, comment_description))
        else:
            comments.append(__generate_comment(file_path, f"Erro na geração do coverage, gcovr error code: {result.returncode}"))

    if os.path.exists(gcovr_run_path):
        shutil.rmtree(gcovr_run_path)

    return comments

def _class_name(file_path):
    splitPath = file_path.split(os.sep)
    return str(splitPath[len(splitPath)-1])

def __process_json(coverage_file_name, class_name):
    with open(coverage_file_name, "r", encoding="utf-8") as file:
         data = json.load(file)
    files = data["files"]
    linePercentValue = next((item["line_percent"] for item in files if item["filename"].endswith(f"/{class_name}")), 0)
    return linePercentValue

def __remove_files(gcovr_run_path):
    for file_name in os.listdir(gcovr_run_path):
        file_path = os.path.join(gcovr_run_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)            

def __search_files_in_directory(files_search, start_path):
    matches = []
    for root, _, files in os.walk(start_path):
        for file_name in files:
            if file_name in files_search:
                matches.append(os.path.join(root, file_name))
    return matches

def __remove_extension_file(file):
    return os.path.splitext(file)[0]

def __search_project_root(build_system, fixed_path, relative_path, file_search):
    parts = relative_path.split(os.sep)

    try:
        build_system_enum = BuildSystem(build_system)
        build_system_file = BUILD_FILES.get(build_system_enum, "")
    except ValueError:
        build_system_file = ""

    if not build_system_file:
        return None            

    for index in range(len(parts), 0, -1):
        current_path = os.path.join(fixed_path, *parts[:index-1])    
        matching_files = glob.glob(os.path.join(current_path, build_system_file))

        for build_system_file_path in matching_files:
            if os.path.isfile(build_system_file_path):
                with open(build_system_file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    if any(element in content for element in ("/"+file_search, " "+file_search)):
                        return current_path

    return None  

def __search_source_file_by_test_file(path_source, file_path):
    print(f"Path file: {file_path}")
    print(f"Path source: {path_source}")
    class_name = _class_name(file_path)
    class_name = match.group(1) if (match := re.search(r"(?:[^_]+_)?(.+?)test\.cpp", class_name)) else None
    path = __search_files_in_directory(class_name+".cpp", path_source)
    path = os.path.relpath(path[0], path_source)
    return path

def __minimum_coverage_verify(fullPath, minimum_coverage, minimum_coverage_by_project):
    minimum = 0    
    for project in minimum_coverage_by_project:        
        for rule in project["regexs"]:
            if re.match(rule["regex"], fullPath):
                minimum = rule["minimum"]
                break
        if minimum:
            break

    if not minimum:
        return minimum_coverage, "<br><br>Warning: foi utilizado para validação o percentual mínimo de cobertura geral, pois não foi identificado na configuração o percentual de cobertura mínimo para o projeto"
    
    return minimum, ""

def __generate_comment(file_path, comment_description):
    return commons.comment_create(
        comment_id=commons.comment_generate_id(comment_description),
        comment_path=file_path,
        comment_description=comment_description,
        comment_snipset=True,
        comment_end_line=1,
        comment_start_line=1,
        comment_language="c++")
