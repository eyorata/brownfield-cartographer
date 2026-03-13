import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import ast
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_yaml
    import tree_sitter_sql
except ImportError:
    Language, Parser = None, None

class LanguageRouter:
    def __init__(self):
        if Language is None:
            self.languages = {}
            return
        self.languages = {
            ".py": Language(tree_sitter_python.language()),
            ".js": Language(tree_sitter_javascript.language()),
            ".ts": Language(tree_sitter_javascript.language()),
            ".yaml": Language(tree_sitter_yaml.language()),
            ".yml": Language(tree_sitter_yaml.language()),
            ".sql": Language(tree_sitter_sql.language()),
        }

    def get_language(self, ext: str):
        return self.languages.get(ext)

class TreeSitterAnalyzer:
    def __init__(self):
        self.router = LanguageRouter()
        self.parser = Parser() if Parser else None

    def _analyze_python_tree_sitter(self, file_path: str) -> Dict[str, Any]:
        parsed = self._parse(file_path)
        if not parsed:
            return {"imports": [], "functions": [], "function_defs": [], "classes": [], "class_defs": [], "data_ops": []}

        tree, content = parsed
        imports: List[str] = []
        functions: List[str] = []
        function_defs: List[Dict[str, Any]] = []
        classes: List[str] = []
        class_defs: List[Dict[str, Any]] = []
        data_ops: List[Dict[str, Any]] = []

        def text(node) -> str:
            return content[node.start_byte : node.end_byte].decode("utf-8", "ignore")

        def traverse(node, decorators: Optional[List[str]] = None):
            decorators = decorators or []

            # decorated_definition wraps function_definition/class_definition
            if node.type == "decorated_definition":
                decos = []
                for child in node.children:
                    if child.type == "decorator":
                        decos.append(text(child).strip())
                for child in node.children:
                    if child.type in ("function_definition", "class_definition"):
                        traverse(child, decorators=decos)
                return

            if node.type in ("import_statement", "import_from_statement"):
                raw = text(node).strip()
                parts = raw.split()
                if parts and parts[0] == "import" and len(parts) >= 2:
                    imports.append(parts[1])
                elif parts and parts[0] == "from" and len(parts) >= 2:
                    imports.append(parts[1])

            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                params_node = node.child_by_field_name("parameters")
                name = text(name_node).strip() if name_node else ""
                signature = text(params_node).strip() if params_node else "()"
                if name and (not name.startswith("_") or name == "__init__"):
                    functions.append(name)
                    function_defs.append(
                        {
                            "name": name,
                            "signature": signature,
                            "decorators": decorators,
                        }
                    )

            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                super_node = node.child_by_field_name("superclasses")
                name = text(name_node).strip() if name_node else ""
                bases = text(super_node).strip() if super_node else ""
                if name:
                    classes.append(name)
                    class_defs.append(
                        {
                            "name": name,
                            "bases": bases,
                            "decorators": decorators,
                        }
                    )

            # Simple heuristic for data ops: read_csv, read_sql, execute, read, write
            if node.type == "call":
                func_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                func_name = text(func_node).strip() if func_node else ""
                if func_name and any(k in func_name for k in ("read_csv", "read_sql", "execute", "read", "write")):
                    data_ops.append(
                        {
                            "type": func_name,
                            "args": text(args_node).strip() if args_node else "",
                        }
                    )

            for child in node.children:
                traverse(child, decorators=decorators)

        traverse(tree.root_node)

        # Normalize imports to module roots (for module graph)
        clean_imports: List[str] = []
        for imp in imports:
            clean_imports.append(imp.split(".")[0])

        return {
            "imports": sorted(set(clean_imports)),
            "functions": sorted(set(functions)),
            "function_defs": function_defs,
            "classes": sorted(set(classes)),
            "class_defs": class_defs,
            "data_ops": data_ops,
        }

    def _analyze_python_ast(self, file_path: str) -> Dict[str, Any]:
        try:
            source = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return {"imports": [], "functions": [], "classes": [], "data_ops": []}

        try:
            tree = ast.parse(source, filename=file_path)
        except Exception:
            return {"imports": [], "functions": [], "classes": [], "data_ops": []}

        imports: List[str] = []
        import_modules: List[Dict[str, Any]] = []
        functions: List[str] = []
        function_defs: List[Dict[str, Any]] = []
        classes: List[str] = []
        class_defs: List[Dict[str, Any]] = []
        data_ops: List[Dict[str, Any]] = []

        def _line_range(node: ast.AST) -> str:
            start = int(getattr(node, "lineno", 1) or 1)
            end = int(getattr(node, "end_lineno", start) or start)
            if end < start:
                end = start
            return f"{start}-{end}"

        def _call_path(fn: ast.AST) -> str:
            parts: List[str] = []
            cur = fn
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            base = ""
            if isinstance(cur, ast.Name):
                base = cur.id
            parts.reverse()
            if base and parts:
                return base + "." + ".".join(parts)
            if parts:
                return ".".join(parts)
            return base

        def _string_literals(call_node: ast.Call) -> List[str]:
            lits: List[str] = []
            for a in list(call_node.args) + [kw.value for kw in call_node.keywords if kw.value is not None]:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    lits.append(a.value)
            return lits

        def _looks_like_sql(s: str) -> bool:
            if not s or len(s) < 12:
                return False
            sl = s.lower()
            return any(k in sl for k in (" select ", "\nselect ", " from ", " join ", " insert ", " update ", " merge "))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        imports.append(alias.name)
                        import_modules.append(
                            {
                                "kind": "import",
                                "module": alias.name,
                                "level": 0,
                                "names": [],
                                "line_range": _line_range(node),
                            }
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                import_modules.append(
                    {
                        "kind": "from",
                        "module": node.module or "",
                        "level": int(getattr(node, "level", 0) or 0),
                        "names": [a.name for a in node.names if getattr(a, "name", None)],
                        "line_range": _line_range(node),
                    }
                )
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith("_") or node.name == "__init__":
                    functions.append(node.name)
                    function_defs.append({"name": node.name, "signature": "", "decorators": []})
            elif isinstance(node, ast.AsyncFunctionDef):
                if not node.name.startswith("_") or node.name == "__init__":
                    functions.append(node.name)
                    function_defs.append({"name": node.name, "signature": "", "decorators": []})
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                class_defs.append({"name": node.name, "bases": "", "decorators": []})
            elif isinstance(node, ast.Call):
                call_path = _call_path(node.func)
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                pandas_reads = {
                    "read_csv",
                    "read_parquet",
                    "read_json",
                    "read_excel",
                    "read_sql",
                    "read_sql_query",
                    "read_table",
                }
                pandas_writes = {
                    "to_csv",
                    "to_parquet",
                    "to_json",
                    "to_sql",
                }
                spark_reads = {"csv", "parquet", "json", "table", "text", "format", "load"}
                spark_writes = {"saveastable", "insertinto", "parquet", "csv", "json", "save", "format"}

                op_type = ""
                direction = ""
                if func_name in pandas_reads or call_path.endswith(tuple("." + x for x in pandas_reads)):
                    op_type = f"pandas_{func_name}"
                    direction = "read"
                elif func_name in pandas_writes or call_path.endswith(tuple("." + x for x in pandas_writes)):
                    op_type = f"pandas_{func_name}"
                    direction = "write"
                elif call_path.startswith("spark.read.") and func_name.lower() in spark_reads:
                    op_type = f"pyspark_read_{func_name.lower()}"
                    direction = "read"
                elif ".write." in call_path.lower() and func_name.lower() in spark_writes:
                    op_type = f"pyspark_write_{func_name.lower()}"
                    direction = "write"
                elif call_path.startswith("spark.sql") or func_name == "sql":
                    op_type = "pyspark_sql"
                    direction = "sql"
                elif func_name == "execute" or call_path.endswith(".execute"):
                    op_type = "sqlalchemy_execute"
                    direction = "sql"

                if op_type:
                    try:
                        args_src = ast.get_source_segment(source, node) or ""
                    except Exception:
                        args_src = ""
                    literals = _string_literals(node)
                    sql_literals = [s for s in literals if _looks_like_sql(s)]
                    unresolved = bool(direction in {"read", "write", "sql"} and not literals)
                    data_ops.append(
                        {
                            "type": op_type,
                            "direction": direction,
                            "call_path": call_path,
                            "args": args_src,
                            "literals": literals,
                            "sql_literals": sql_literals,
                            "line_range": _line_range(node),
                            "unresolved": unresolved,
                        }
                    )

        return {
            "imports": sorted(set(imports)),
            "import_modules": import_modules,
            "functions": sorted(set(functions)),
            "function_defs": function_defs,
            "classes": sorted(set(classes)),
            "class_defs": class_defs,
            "data_ops": data_ops,
        }

    def _parse(self, file_path: str):
        if not self.parser:
            return None
        ext = Path(file_path).suffix
        lang = self.router.get_language(ext)
        if not lang:
            return None
        self.parser.language = lang
        with open(file_path, 'rb') as f:
            content = f.read()
        return self.parser.parse(content), content

    def analyze_python_module(self, file_path: str) -> Dict[str, Any]:
        """Extracts imports, public functions, classes."""
        # Prefer tree-sitter when available for richer structural extraction.
        ast_result = self._analyze_python_ast(file_path)
        if self.parser:
            ts_result = self._analyze_python_tree_sitter(file_path)
            if ts_result["imports"] or ts_result["functions"] or ts_result["classes"]:
                # Always merge in AST-based import info for relative import resolution.
                ast_imports = ast_result.get("import_modules", [])
                ts_result["import_modules"] = ast_imports
                # Prefer richer AST data-op extraction for lineage (better literals + line ranges).
                if ast_result.get("data_ops"):
                    ts_result["data_ops"] = ast_result.get("data_ops") or []
                return ts_result

        if ast_result["imports"] or ast_result["functions"] or ast_result["classes"]:
            return ast_result

        parsed = self._parse(file_path)
        if not parsed:
            return {"imports": [], "functions": [], "function_defs": [], "classes": [], "class_defs": [], "data_ops": []}
        tree, content = parsed
        
        imports = []
        functions = []
        classes = []
        data_ops = []

        def traverse(node):
            if node.type == 'import_statement' or node.type == 'import_from_statement':
                imports.append(content[node.start_byte:node.end_byte].decode('utf-8'))
            elif node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    if not name.startswith('_') or name == '__init__':
                        functions.append(name)
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    classes.append(name)
            
            # Simple heuristic for data ops: read_csv, read_sql, execute
            if node.type == 'call':
                func_node = node.child_by_field_name('function')
                if func_node:
                    func_name = content[func_node.start_byte:func_node.end_byte].decode('utf-8')
                    if 'read_csv' in func_name or 'read_sql' in func_name or 'execute' in func_name or 'read' in func_name or 'write' in func_name:
                        args_node = node.child_by_field_name('arguments')
                        if args_node:
                            data_ops.append({
                                "type": func_name,
                                "args": content[args_node.start_byte:args_node.end_byte].decode('utf-8')
                            })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        
        # Parse imports to just get module names
        clean_imports = []
        for imp in imports:
            parts = imp.split()
            if parts[0] == 'import':
                clean_imports.append(parts[1].split('.')[0])
            elif parts[0] == 'from':
                clean_imports.append(parts[1].split('.')[0])
        
        return {
            "imports": list(set(clean_imports)),
            "functions": functions,
            "function_defs": [{"name": n, "signature": "", "decorators": []} for n in functions],
            "classes": classes,
            "class_defs": [{"name": n, "bases": "", "decorators": []} for n in classes],
            "data_ops": data_ops
        }

    def parse_python(self, file_path):
        return self.analyze_python_module(file_path)

    def parse_sql(self, file_path):
        parsed = self._parse(file_path)
        if not parsed:
            return {"relations": []}
        tree, content = parsed

        relations: List[Dict[str, Any]] = []

        def text(node) -> str:
            return content[node.start_byte : node.end_byte].decode("utf-8", "ignore")

        def traverse(node):
            # The tree-sitter-sql grammar surfaces table-like references as `relation` nodes.
            if node.type == "relation":
                val = text(node).strip()
                if val:
                    relations.append(
                        {
                            "name": val,
                            "start": {"row": node.start_point[0] + 1, "col": node.start_point[1] + 1},
                            "end": {"row": node.end_point[0] + 1, "col": node.end_point[1] + 1},
                        }
                    )
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        # Stable ordering (by location).
        relations_sorted = sorted(relations, key=lambda r: (r["start"]["row"], r["start"]["col"], r["name"]))
        return {"relations": relations_sorted}
        
    def parse_yaml(self, file_path):
        parsed = self._parse(file_path)
        if not parsed:
            # Fallback to semantic YAML load when tree-sitter isn't available.
            try:
                import yaml  # type: ignore

                data = yaml.safe_load(Path(file_path).read_text(encoding="utf-8"))
                return {"keys": sorted(list(data.keys())) if isinstance(data, dict) else []}
            except Exception:
                return {"keys": []}

        tree, content = parsed
        key_paths: List[str] = []

        def text(node) -> str:
            return content[node.start_byte : node.end_byte].decode("utf-8", "ignore")

        def traverse(node, stack: List[str]):
            # Capture dotted key paths for nested mappings.
            if node.type == "block_mapping_pair":
                key_node = node.child_by_field_name("key")
                value_node = node.child_by_field_name("value")
                if key_node:
                    k = text(key_node).strip().strip("'\"")
                    if k:
                        path = ".".join(stack + [k]) if stack else k
                        key_paths.append(path)
                        if value_node:
                            traverse(value_node, stack + [k])
                        return

            for child in node.children:
                traverse(child, stack)

        traverse(tree.root_node, [])
        return {"key_paths": sorted(set(key_paths))}
