import yaml
from typing import Dict, Any, List
import ast
from pathlib import Path

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

    @staticmethod
    def _line_range(node: ast.AST) -> str:
        start = int(getattr(node, "lineno", 1) or 1)
        end = int(getattr(node, "end_lineno", start) or start)
        if end < start:
            end = start
        return f"{start}-{end}"

    @staticmethod
    def _get_call_name(fn: ast.AST) -> str:
        if isinstance(fn, ast.Name):
            return fn.id
        if isinstance(fn, ast.Attribute):
            return fn.attr
        return ""

    @staticmethod
    def _extract_string_literals(call_node: ast.Call) -> List[str]:
        lits: List[str] = []
        for a in list(call_node.args) + [kw.value for kw in call_node.keywords if kw.value is not None]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                lits.append(a.value)
        return lits

    def parse_airflow_py(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses a Python Airflow DAG file to extract a task dependency graph.

        Supported patterns (best-effort):
        - task definitions: <var> = SomeOperator(task_id="x", ...)
        - dependencies: t1 >> t2, [t1, t2] >> t3, t1 << t2, chain(t1, t2, t3)
        - dependencies: t1.set_downstream(t2), t2.set_upstream(t1)

        Returns: [{"type":"task","id":..., "depends_on":[...], "line_range":"a-b", "sql_literals":[...]}]
        """
        p = Path(file_path)
        if p.suffix.lower() != ".py":
            return []

        try:
            source = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        try:
            tree = ast.parse(source, filename=str(p))
        except Exception:
            return []

        # Quick gate: only run if file references Airflow-ish identifiers.
        src_l = source.lower()
        if "airflow" not in src_l and "dag(" not in src_l:
            return []

        task_var_to_id: Dict[str, str] = {}
        task_id_to_meta: Dict[str, Dict[str, Any]] = {}
        deps: Dict[str, set[str]] = {}

        def _task_ids_from_expr(expr: ast.AST) -> List[str]:
            if isinstance(expr, ast.Name):
                tid = task_var_to_id.get(expr.id)
                return [tid] if tid else []
            if isinstance(expr, (ast.List, ast.Tuple)):
                out: List[str] = []
                for elt in expr.elts:
                    out.extend(_task_ids_from_expr(elt))
                return out
            return []

        def _add_edge(upstream: str, downstream: str, lr: str) -> None:
            if not upstream or not downstream or upstream == downstream:
                return
            deps.setdefault(downstream, set()).add(upstream)
            # Keep a best-effort dependency location on downstream (first seen).
            m = task_id_to_meta.get(downstream) or {}
            if not m.get("dependency_line_range"):
                m["dependency_line_range"] = lr
                task_id_to_meta[downstream] = m

        for node in ast.walk(tree):
            # Task definition: x = SomeOperator(task_id="...")
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                task_id = None
                for kw in call.keywords or []:
                    if kw.arg == "task_id" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        task_id = kw.value.value
                        break
                if not task_id:
                    continue
                var_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if not var_names:
                    continue
                var = var_names[0]
                task_var_to_id[var] = str(task_id)
                task_id_to_meta[str(task_id)] = {
                    "line_range": self._line_range(node),
                    "operator": self._get_call_name(call.func),
                    "sql_literals": self._extract_string_literals(call),
                }

            # Dependencies via >> / <<
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.RShift, ast.LShift)):
                left = _task_ids_from_expr(node.left)
                right = _task_ids_from_expr(node.right)
                lr = self._line_range(node)
                if isinstance(node.op, ast.RShift):
                    for u in left:
                        for v in right:
                            _add_edge(u, v, lr)
                else:
                    for u in right:
                        for v in left:
                            _add_edge(u, v, lr)

            # Dependencies via set_upstream / set_downstream
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                meth = str(node.func.attr or "")
                base_ids = _task_ids_from_expr(node.func.value)
                arg_ids: List[str] = []
                for a in node.args:
                    arg_ids.extend(_task_ids_from_expr(a))
                lr = self._line_range(node)
                if meth == "set_downstream":
                    for u in base_ids:
                        for v in arg_ids:
                            _add_edge(u, v, lr)
                if meth == "set_upstream":
                    for u in arg_ids:
                        for v in base_ids:
                            _add_edge(u, v, lr)

            # chain(t1, t2, t3)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "chain":
                ids: List[str] = []
                for a in node.args:
                    ids.extend(_task_ids_from_expr(a))
                lr = self._line_range(node)
                for i in range(len(ids) - 1):
                    _add_edge(ids[i], ids[i + 1], lr)

        out: List[Dict[str, Any]] = []
        # Ensure tasks with no deps still appear.
        for tid, meta in task_id_to_meta.items():
            out.append(
                {
                    "type": "task",
                    "id": str(tid),
                    "depends_on": sorted(deps.get(str(tid), set())),
                    "line_range": str(meta.get("dependency_line_range") or meta.get("line_range") or "1-1"),
                    "operator": str(meta.get("operator") or ""),
                    "sql_literals": [s for s in (meta.get("sql_literals") or []) if isinstance(s, str)],
                }
            )
        return out
