import sqlglot
from sqlglot import parse_one, exp
from typing import List, Dict, Any

class SQLLineageAnalyzer:
    def __init__(self):
        pass

    def extract_dependencies(self, sql_query: str, dialect: str = "postgres") -> Dict[str, Any]:
        """
        Parses SQL to find dependencies via sqlglot.
        Returns sources (tables read from) and targets (tables written to).
        """
        try:
            parsed = parse_one(sql_query, read=dialect)
        except Exception as e:
            print(f"Failed to parse SQL: {e}")
            return {"sources": [], "targets": []}
            
        sources = []
        targets = []
        
        if not parsed:
            return {"sources": [], "targets": []}
        
        # Determine targets (e.g. CREATE TABLE AS ... or INSERT INTO ...)
        if isinstance(parsed, exp.Create):
            this_node = parsed.find(exp.Table)
            if this_node:
                targets.append(this_node.name)
        elif isinstance(parsed, exp.Insert):
            this_node = parsed.find(exp.Table)
            if this_node:
                targets.append(this_node.name)
                
        # Find all CTEs to exclude them from sources
        cte_names = set()
        for with_ in parsed.find_all(exp.With):
            for cte in with_.expressions:
                cte_names.add(cte.alias)
                
        # Find all table references
        for table in parsed.find_all(exp.Table):
            if table.name not in cte_names and table.name not in targets:
                name = table.name
                if table.db:
                    name = f"{table.db}.{name}"
                if table.catalog:
                    name = f"{table.catalog}.{name}"
                sources.append(name)
                
        # Also parse dbt ref() if they exist. ref and source in dbt are often rendered as functions if not compiled
        # But if it's a jinja {{ ref('table') }}, sqlglot won't parse it well unless it's configured.
        # Often we parse the compiled sql if it exists.
        # Simple extraction for jaffle_shop jinja fallback:
        import re
        dbt_refs = re.findall(r"{{\s*ref\(['\"](.*?)['\"]\)\s*}}", sql_query)
        dbt_sources = re.findall(r"{{\s*source\(['\"](.*?)['\"]\s*,\s*['\"](.*?)['\"]\)\s*}}", sql_query)
        
        for ref in dbt_refs:
            sources.append(ref)
        for src in dbt_sources:
            sources.append(f"{src[0]}.{src[1]}")
            
        return {
            "sources": list(set(sources)),
            "targets": list(set(targets))
        }
