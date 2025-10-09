from math import inf
from typing import Any, Dict, List, Optional
from .lexer import tokenize

def _unquote(s: str) -> str:
    """Quita comillas simples/dobles si existen."""
    s = s.strip()
    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in ("'", '"')):
        return s[1:-1]
    return s

def _lit(tok: str) -> Any:
    """
    Convierte los literales en Python:
      - "10" -> int(10)
      - "10.5" -> float(10.5)
      - "'Zoe'" o "Zoe" -> "Zoe" (sin comillas en el primer caso)
    """
    t = tok.strip()
    # int
    try:
        if "." not in t:
            return int(t)
    except Exception:
        pass
    # float
    try:
        return float(t)
    except Exception:
        pass
    # string
    return _unquote(t)

def _find(words: List[str], target: str) -> int:
    """Índice de 'target' (case-insensitive) o -1 si no está."""
    tgt = target.lower()
    for i, w in enumerate(words):
        if w.lower() == tgt:
            return i
    return -1

class SQLParser:
    """
    SQL Parser reducido -> AST (diccionario).
    Soporta:
      - CREATE TABLE t (col TYPE [INDEX kind], ...)
      - CREATE INDEX idx_name ON table(column) [USING index_type]
      - INSERT INTO t VALUES (v1, v2, ...)
      - SELECT cols FROM t [WHERE col {=,<,<=,>,>=} val | col BETWEEN a AND b] [LIMIT n]
      - DELETE FROM t WHERE col = val
    """

    def parse(self, query: str) -> Dict[str, Any]:
        """Parses an SQL query and returns the corresponding AST (Abstract Syntax Tree)."""
        toks = tokenize(query)
        words = [v for (_k, v) in toks]
        if not words:
            raise ValueError("Consulta vacía")

        first = words[0].lower()
        if first == "create":
            if len(words) > 1 and words[1].lower() == "index":
                return self._parse_create_index(words)
            elif len(words) > 1 and words[1].lower() == "table":
                return self._parse_create(words)
        if first == "insert":
            return self._parse_insert(words)
        if first == "select":
            return self._parse_select(words)
        if first == "delete":
            return self._parse_delete(words)
        raise ValueError(f"Sentencia no soportada: {first}")

    def _parse_create(self, w: List[str]) -> Dict[str, Any]:
        """Parsea CREATE TABLE."""
        if len(w) < 3 or w[1].lower() != "table":
            raise ValueError("Sintaxis: CREATE TABLE <name> (...)")
        table = w[2]

        lp = _find(w, "(")
        rp = _find(w, ")")
        if lp == -1 or rp == -1 or rp <= lp + 1:
            raise ValueError("CREATE TABLE requiere definición de columnas entre ()")
        body = w[lp + 1 : rp]

        columns: List[Dict[str, str]] = []
        index_map: Dict[str, str] = {}

        # Parsear las columnas
        current: List[str] = []
        items: List[List[str]] = []
        for tok in body:
            if tok == ",":
                if current:
                    items.append(current)
                current = []
            else:
                current.append(tok)
        if current:
            items.append(current)

        for item in items:
            if len(item) < 2:
                raise ValueError(f"Definición de columna inválida: {' '.join(item)}")
            name = item[0]
            ctype = item[1]
            # Si el tipo es VARCHAR, procesamos el número
            if ctype.upper() == "VARCHAR" and len(item) == 3:
                try:
                    size = int(item[2])
                    ctype = f"VARCHAR[{size}]"
                except ValueError:
                    raise ValueError(f"VARCHAR inválido: {item[2]}")
            columns.append({"name": name, "type": ctype})
            if len(item) >= 4 and item[2].lower() == "index":
                index_map[name] = item[3].lower()

        return {"operation": "create", "table": table, "columns": columns, "index_map": index_map}

    def _parse_create_index(self, w: List[str]) -> Dict[str, Any]:
        """Parsea CREATE INDEX idx_name ON table(column) [USING index_type]."""
        print(w, len(w),w[4])
        if len(w) < 8 or w[3].lower() != "on" or w[1].lower() != "index":
            raise ValueError("Sintaxis: CREATE INDEX <idx_name> ON <table> (<column>) [USING <index_type>]")
        idx_name = w[2]  # nombre del índice (no usado aquí, pero se puede guardar si se necesita)
        table = w[4]

        # Parsear la columna entre paréntesis
        lp = _find(w, "(")
        rp = _find(w, ")")
        if lp == -1 or rp == -1 or rp <= lp + 1:
            raise ValueError("CREATE INDEX requiere columna entre paréntesis")
        column = w[lp + 1]

        # Tipo de índice (opcional, default 'btree')
        index_type = "sequential"  # por defecto
        ui = _find(w, "using")
        if ui != -1 and ui + 1 < len(w):
            index_type = w[ui + 1].lower()

        return {
            "operation": "create_index",
            "idx_name": idx_name,
            "table": table,
            "column": column,
            "index_type": index_type,
        }

    def _parse_insert(self, w: List[str]) -> Dict[str, Any]:
        """Parsea INSERT INTO con múltiples tuplas."""
        if len(w) < 4 or w[1].lower() != "into":
            raise ValueError("Sintaxis: INSERT INTO <tabla> VALUES (...)")

        table = w[2]

        if _find(w, "values") == -1:
            raise ValueError("INSERT debe incluir VALUES (...)")

        lp = _find(w, "(")
        rp = _find(w, ")")
        if lp == -1 or rp == -1 or rp <= lp + 1:
            raise ValueError("INSERT VALUES requiere paréntesis con valores")

        # Aquí identificamos todas las tuplas separadas por comas
        raw = [t for t in w[lp + 1: rp] if t != ","]
        # Parsear cada tupla en valores
        values = []
        for t in raw:
            values.append(_lit(t))
        return {"operation": "insert", "table": table, "values": values}

    def _parse_select(self, w: List[str]) -> Dict[str, Any]:
        # SELECT cols FROM t [WHERE ...] [USING col] [LIMIT n]
        fi = _find(w, "from")
        if fi == -1:
            raise ValueError("SELECT requiere FROM")

        raw_cols = [t for t in w[1:fi] if t != ","]
        columns = raw_cols or ["*"]

        if fi + 1 >= len(w):
            raise ValueError("Falta tabla tras FROM")
        table = w[fi + 1]

        where: Optional[Dict[str, Any]] = None
        idx_col: Optional[str] = None
        limit: Optional[int] = None

        # WHERE (acepta: col = v | col < v | col <= v | col > v | col >= v | col BETWEEN a AND b)
        wi = _find(w, "where")
        if wi != -1:
            end = len(w)
            li = _find(w, "limit")
            if li != -1:
                end = min(end, li)
            cond = [t for t in w[wi + 1: end] if t != ","]

            # BETWEEN (nuevo soporte)
            bi = _find(cond, "between")
            if bi == 1 and _find(cond, "and") == 3 and len(cond) >= 5:
                # cond: [col, between, a, and, b]
                col = cond[0]
                lo = _lit(cond[2])
                hi = _lit(cond[4])
                where = {
                    "type": "range",
                    "column": col,
                    "low": lo,
                    "high": hi,
                    "inc_low": True,
                    "inc_high": True,
                }

            # Comparadores simples
            elif len(cond) >= 3 and cond[1] in ("=", "==", "<", "<=", ">", ">="):
                op = cond[1]
                col = cond[0]
                val = _lit(cond[2])
                # Aquí determinamos si 'val' es un número (int o float) o un string
                if isinstance(val, (int, float)):
                    # Si es int o float, usamos float('-inf') o float('inf') para los rangos
                    if op == "<=":
                        where = {"type": "range", "column": col, "low": -inf, "high": val}
                    elif op == ">=":
                        where = {"type": "range", "column": col, "low": val, "high": inf}
                else:
                    # Si es un string, usamos '-inf' y 'inf' como los valores más bajos o más altos
                    if op == "<=":
                        where = {"type": "range", "column": col, "low": chr(0), "high": val}
                    elif op == ">=":
                        where = {"type": "range", "column": col, "low": val, "high": "{"}
                # Si es comparación de igualdad simple
                if op == "=" or op == "==":
                    m = {"=": "eq", "==": "eq"}
                    where = {"type": m[op], "column": col, "value": val}

        # LIMIT
        li = _find(w, "limit")
        if li != -1 and li + 1 < len(w):
            limit = int(_lit(w[li + 1]))

        return {
            "operation": "select",
            "table": table,
            "columns": columns,
            "where": where,  # dict estructurado o None
            "limit": limit,
        }

    def _parse_delete(self, w: List[str]) -> Dict[str, Any]:
        """Parsea DELETE."""
        if len(w) < 3 or w[1].lower() != "from":
            raise ValueError("Sintaxis: DELETE FROM <tabla> WHERE ...")
        table = w[2]
        wi = _find(w, "where")
        if wi == -1:
            raise ValueError("DELETE requiere WHERE col = val")
        cond = [t for t in w[wi + 1 :] if t != ","]
        where = {"type": "eq", "column": cond[0], "value": _lit(cond[2])}
        return {"operation": "delete", "table": table, "where": where}
