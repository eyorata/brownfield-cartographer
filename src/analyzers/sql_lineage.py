import re
import sys
from typing import Any, Dict, List, Optional

import sqlglot
from sqlglot import exp, parse
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

class SQLLineageAnalyzer:
    def __init__(self):
        # Aggregate parse failures to avoid noisy logs on Jinja-heavy SQL.
        # Each item: {"error": str, "snippet": str}
        self.parse_failures: List[Dict[str, str]] = []
        self._parse_failures_max = 25

    def _try_parse(self, sql_query: str, dialects: List[str]) -> tuple[List[exp.Expression], Optional[str]]:
        for d in dialects:
            try:
                statements = parse(sql_query, read=d)
                if statements:
                    return statements, d
            except Exception:
                continue
        return [], None

    @staticmethod
    def _line_number_at(sql: str, index: int) -> int:
        # 1-based line number
        return sql.count("\n", 0, index) + 1

    def extract_dependencies(self, sql_query: str, dialect: str = "postgres") -> Dict[str, Any]:
        """
        Parses SQL to find dependencies via sqlglot.
        Returns sources (tables read from) and targets (tables written to).
        """
        sources: List[str] = []
        targets: List[str] = []
        statements_out: List[Dict[str, Any]] = []
        dialects_tried: List[str] = []

        # Dialect support: try caller dialect first, then a few common warehouse dialects.
        dialects_tried = [dialect, "postgres", "bigquery", "snowflake"]
        dialects_tried = [d for i, d in enumerate(dialects_tried) if d and d not in dialects_tried[:i]]
        statements, dialect_used = self._try_parse(sql_query, dialects_tried)
        if not statements and dialect_used is None:
            # Many dbt models contain Jinja which sqlglot cannot parse directly.
            # We still extract dependencies via regex fallbacks below.
            try:
                # One last attempt with no explicit read dialect (sqlglot guess).
                statements = parse(sql_query)
                dialect_used = "auto"
            except Exception as e:
                if len(self.parse_failures) < self._parse_failures_max:
                    snippet = sql_query.strip().splitlines()[:20]
                    self.parse_failures.append(
                        {
                            "error": str(e),
                            "snippet": "\n".join(snippet),
                        }
                    )
                statements = []
                dialect_used = None
        
        for stmt in statements:
            stmt_sources: List[str] = []
            stmt_targets: List[str] = []

            # Determine targets (e.g. CREATE/INSERT/UPDATE/MERGE)
            if isinstance(stmt, exp.Create):
                this_node = stmt.find(exp.Table)
                if this_node:
                    stmt_targets.append(this_node.name)
            elif isinstance(stmt, exp.Insert):
                this_node = stmt.find(exp.Table)
                if this_node:
                    stmt_targets.append(this_node.name)
            elif isinstance(stmt, exp.Update):
                this_node = stmt.find(exp.Table)
                if this_node:
                    stmt_targets.append(this_node.name)
            elif isinstance(stmt, exp.Delete):
                this_node = stmt.find(exp.Table)
                if this_node:
                    stmt_targets.append(this_node.name)
            elif isinstance(stmt, exp.Merge):
                this_node = stmt.find(exp.Table)
                if this_node:
                    stmt_targets.append(this_node.name)

            # Find all CTEs to exclude them from sources
            cte_names = set()
            for with_ in stmt.find_all(exp.With):
                for cte in with_.expressions:
                    try:
                        cte_names.add(cte.alias_or_name)
                    except Exception:
                        pass

            # Find all table references, including FROM/JOIN/subqueries.
            for table in stmt.find_all(exp.Table):
                if table.name in cte_names or table.name in stmt_targets:
                    continue
                name = table.name
                if table.db:
                    name = f"{table.db}.{name}"
                if table.catalog:
                    name = f"{table.catalog}.{name}"
                stmt_sources.append(name)

            stmt_sources = list(set(stmt_sources))
            stmt_targets = list(set(stmt_targets))
            sources.extend(stmt_sources)
            targets.extend(stmt_targets)
            statements_out.append({"sources": stmt_sources, "targets": stmt_targets})
                
        # Also parse dbt ref() if they exist. ref and source in dbt are often rendered as functions if not compiled
        # But if it's a jinja {{ ref('table') }}, sqlglot won't parse it well unless it's configured.
        # Often we parse the compiled sql if it exists.
        # Simple extraction for jaffle_shop jinja fallback:
        # Also handle multi-arg ref('package', 'model') by taking the last arg as model name.
        dbt_refs = list(re.finditer(r"{{\s*ref\((.*?)\)\s*}}", sql_query))
        dbt_sources = list(
            re.finditer(r"{{\s*source\(\s*['\"](.*?)['\"]\s*,\s*['\"](.*?)['\"]\s*\)\s*}}", sql_query)
        )

        ref_locations: Dict[str, List[int]] = {}
        source_locations: Dict[str, List[int]] = {}
        
        for m in dbt_refs:
            ref_args = m.group(1)
            args = re.findall(r"['\"]([^'\"]+)['\"]", ref_args)
            if not args:
                continue
            name = args[-1]
            sources.append(name)
            ref_locations.setdefault(name, []).append(self._line_number_at(sql_query, m.start()))

        for m in dbt_sources:
            name = f"{m.group(1)}.{m.group(2)}"
            sources.append(name)
            source_locations.setdefault(name, []).append(self._line_number_at(sql_query, m.start()))
            
        return {
            "sources": list(set(sources)),
            "targets": list(set(targets)),
            "statements": statements_out,
            "dialect_requested": dialect,
            "dialect_used": dialect_used,
            "dialects_tried": dialects_tried,
            "ref_line_numbers": ref_locations,
            "source_line_numbers": source_locations,
        }

    def consume_parse_failures(self) -> List[Dict[str, str]]:
        """
        Return and clear aggregated parse failures.
        """
        out = list(self.parse_failures)
        self.parse_failures.clear()
        return out
