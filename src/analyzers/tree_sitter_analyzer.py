import os
from pathlib import Path
from typing import Dict, Any, List, Optional
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
        parsed = self._parse(file_path)
        if not parsed:
            return {"imports": [], "functions": [], "classes": [], "data_ops": []}
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
            "classes": classes,
            "data_ops": data_ops
        }

    def parse_python(self, file_path):
        return self.analyze_python_module(file_path)

    def parse_sql(self, file_path):
        pass
        
    def parse_yaml(self, file_path):
        pass
