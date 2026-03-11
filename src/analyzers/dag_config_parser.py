import yaml
from typing import Dict, Any, List

class DAGConfigParser:
    def parse_dbt_yaml(self, file_path: str) -> List[Dict[str, Any]]:
        """Parses a dbt schema or models .yml file."""
        configs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
            
            if not content:
                return configs
                
            # dbt typically has "models", "sources", "seeds"
            models = content.get("models")
            if isinstance(models, list):
                for model in models:
                    if isinstance(model, dict):
                        model_name = model.get("name")
                        if model_name:
                            configs.append({"type": "model", "name": model_name})

            sources = content.get("sources")
            if isinstance(sources, list):
                for source in sources:
                    if not isinstance(source, dict):
                        continue
                    source_name = source.get("name")
                    for table in source.get("tables", []) or []:
                        if isinstance(table, dict) and source_name and table.get("name"):
                            configs.append(
                                {
                                    "type": "source",
                                    "name": f"{source_name}.{table.get('name')}",
                                }
                            )
        except Exception as e:
            print(f"Error parsing dbt yaml {file_path}: {e}")
            
        return configs

    def parse_airflow_yaml(self, file_path: str) -> List[Dict[str, Any]]:
        """Parses an Airflow declarative context or custom configs."""
        configs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
            if not content:
                return configs
        except Exception as e:
            return configs

        # Extremely lightweight schema for "task graph" YAMLs used in some teams.
        # Expected shapes (examples):
        # - {"tasks": [{"id": "a", "depends_on": ["b"]}, ...]}
        # - {"dag": {"tasks": [{"task_id": "...", "upstream": [...]}, ...]}}
        tasks = None
        if isinstance(content, dict):
            if isinstance(content.get("tasks"), list):
                tasks = content.get("tasks")
            elif isinstance(content.get("dag"), dict) and isinstance(content["dag"].get("tasks"), list):
                tasks = content["dag"].get("tasks")

        if not tasks:
            return configs

        for task in tasks:
            if not isinstance(task, dict):
                continue
            task_id = task.get("id") or task.get("task_id") or task.get("name")
            if not task_id:
                continue
            depends = task.get("depends_on") or task.get("upstream") or []
            if not isinstance(depends, list):
                depends = [depends]
            configs.append({"type": "task", "id": str(task_id), "depends_on": [str(d) for d in depends]})
        return configs
