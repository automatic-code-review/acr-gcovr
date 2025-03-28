import os
import shutil
import subprocess
import re
import json
import automatic_code_review_commons as commons
from enum import Enum

class BuildSystem(Enum):
    QMAKE = "qmake"
    CMAKE = "cmake"

BUILD_FILES = {
    BuildSystem.QMAKE: "lib.pro",
    BuildSystem.CMAKE: "CMakeLists.txt"
}    

def review(config):    
    pathSource = config['path_source']
    commentDescription = str(config['message'])
    minimumCoverage = config["configs"]["minimum_coverage"]
    minimumCoverageByProject = config["configs"]["minimum_coverage_by_project"]
    buildSystem = config["configs"]["build_system"]
    changes = config['merge']['changes']    
    
    comments = []

    gcovrRunPath = "/tmp/"+config['merge']['merge_request_id']

    os.makedirs(gcovrRunPath, exist_ok=True)          

    for change in changes:
        __remove_files(gcovrRunPath)

        if change['deleted_file'] or change['new_file']:
            continue

        filePath = change['new_path']
        if not filePath.lower().endswith((".h", ".cpp")):
            continue

        if "/test/" in filePath:
            filePath = __search_source_file_by_test_file(pathSource, filePath)
            if not filePath:
                continue

        className = _class_name(filePath)
        classNameWithoutExtension = __remove_extension_file(className)
        
        rootPath = __search_project_root(buildSystem, pathSource, filePath, className)
        if not rootPath:
            comments.append(__generate_comment(filePath, "diretório root não foi encontrado"))
            continue

        filesToGenerateCoverage = __search_files_in_directory((classNameWithoutExtension+".gcda", classNameWithoutExtension+".gcno"), rootPath)
        if not filesToGenerateCoverage:
            continue

        for file in filesToGenerateCoverage:
            shutil.copy(file, gcovrRunPath)

        filterPath = ".*"+os.path.relpath(pathSource+"/"+__remove_extension_file(filePath), rootPath)+".*"
        jsonOutput = classNameWithoutExtension+".json"    
        command = f'gcovr --root {rootPath} --filter "{filterPath}" --json-summary {jsonOutput} {gcovrRunPath}'
        result = subprocess.run(command, shell=True, cwd=gcovrRunPath, capture_output=True, text=True)

        if result.returncode == 0:
            percent = __process_json(gcovrRunPath+"/"+jsonOutput, className)
            minimum = __minimum_coverage_verify(pathSource+"/"+filePath, minimumCoverage, minimumCoverageByProject)
            if percent < minimum:
                commentDescription = commentDescription.replace("${PERCENT_MINIMUM_COVERAGE}", str(minimum))
                commentDescription = commentDescription.replace("${PERCENT_COVERAGE}", str(percent))
                comments.append(__generate_comment(filePath, commentDescription))

    if os.path.exists(gcovrRunPath):
        shutil.rmtree(gcovrRunPath)

    return comments

def _class_name(filePath):
    splitPath = filePath.split(os.sep)
    return str(splitPath[len(splitPath)-1])

def __process_json(coverageFileName, className):
    with open(coverageFileName, "r", encoding="utf-8") as file:
         data = json.load(file)
    files = data["files"]
    linePercentValue = next((item["line_percent"] for item in files if item["filename"].endswith(f"/{className}")), 0)
    return linePercentValue

def __remove_files(gcovrRunPath):
    for fileName in os.listdir(gcovrRunPath):
        filePath = os.path.join(gcovrRunPath, fileName)
        if os.path.isfile(filePath):
            os.remove(filePath)            

def __search_files_in_directory(filesSearch, startPath):
    matches = []
    for root, _, files in os.walk(startPath):
        for fileName in files:
            if fileName in filesSearch:
                matches.append(os.path.join(root, fileName))
    return matches

def __remove_extension_file(file):
    return os.path.splitext(file)[0]

def __search_project_root(buildSystem, fixedPath, relativePath, fileSearch):
    parts = relativePath.split(os.sep)

    try:
        buildSystemEnum = BuildSystem(buildSystem)
        buildSystemFile = BUILD_FILES.get(buildSystemEnum, "")
    except ValueError:
        buildSystemFile = ""

    if not buildSystemFile:
        return None            

    for index in range(len(parts), 0, -1):
        currentPath = os.path.join(fixedPath, *parts[:index-1])
        buildSystemFilePath = os.path.join(currentPath, buildSystemFile)
        if os.path.isfile(buildSystemFilePath):
            with open(buildSystemFilePath, "r", encoding="utf-8") as file:
                content = file.read()
                if any(element in content for element in ("/"+fileSearch, " "+fileSearch)):
                    return currentPath

    return None  

def __search_source_file_by_test_file(pathSource, filePath):
    className = _class_name(filePath)
    className = match.group(1) if (match := re.search(r"(?:[^_]+_)?(.+?)test\.cpp", className)) else None
    path = __search_files_in_directory(className+".cpp", pathSource)
    path = os.path.relpath(path[0], pathSource)
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
        return minimum_coverage
    
    return minimum

def __generate_comment(filePath, commentDescription):
    return commons.comment_create(
        comment_id=commons.comment_generate_id(commentDescription),
        comment_path=filePath,
        comment_description=commentDescription,
        comment_snipset=True,
        comment_end_line=1,
        comment_start_line=1,
        comment_language="c++")