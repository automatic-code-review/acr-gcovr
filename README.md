# acr-extension-name

Arquivo config.json

```json
{
    "path_target": "...",
    "path_source": "...",
    "path_output": "...",
    "message": "Percentual de coverage ${PERCENT_COVERAGE} não atingiu o percentual mínimo configurado para o projeto ${PERCENT_MINIMUM_COVERAGE}",
    "configs": {
        "buildSystem": "qmake|cmake",
        "minimumCoverage": 80,
        "identifyTestClass": "/test/",
        "onlyNewFiles": true,
        "regexToIgnore": [ ".*my_path_to_ignore.*"],
        "minimumCoverageByProject": [
            {
                "id": 1,
                "name": "project name",
                "regexs": [
                    {
                        "regex": ".*path-project.*",
                        "minimum": 70
                    }                    
                ]
            }
        ]
    },
    "merge": {
        "git_type": "...",
        "title": "...",
        "changes": [
            {
                "diff": "...",
                "new_path": "...",
                "old_path": "...",
                "a_mode": "...",
                "b_mode": "...",
                "new_file": false,
                "renamed_file": false,
                "deleted_file": false
            }
        ],
        "branch": {
            "target": "...",
            "source": "..."
        },
        "project_id": "...",
        "merge_request_id": "..."
    }
}
```
