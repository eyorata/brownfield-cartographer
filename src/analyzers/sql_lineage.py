import sqlglot
from sqlglot import parse_one, exp
from sqlglot.lineage import lineage

class SQLLineageAnalyzer:
    def __init__(self):
        print("Initializing SQLLineageAnalyzer with sqlglot...")

    def extract_dependencies(self, sql_query):
        """
        Parses SQL to find dependencies via sqlglot.
        """
        try:
            parsed = parse_one(sql_query)
        except Exception as e:
            print(f"Failed to parse SQL: {e}")
            return []
        
        # Example to find source tables
        tables = [t.name for t in parsed.find_all(exp.Table)]
        return tables
