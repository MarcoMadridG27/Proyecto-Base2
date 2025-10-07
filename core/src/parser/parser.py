# parser/parser.py
from typing import Any, Dict, List, Optional
from .lexer import tokenize

# ---------- helpers básicos ----------

def _unquote(s: str) -> str:
    """Quita comillas simples/dobles si existen."""
    s = s.strip()
    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in ("'", '"')):
        return s[1:-1]
    return s

def _lit(tok: str) -> Any:
    """
    Literal a Python:
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

# ---------- parser principal ----------

class SQLParser:
    """
    SQL MUY reducido -> AST (diccionario).
    Soporta:
      - CREATE TABLE t (col TYPE [INDEX kind], ...)
      - INSERT INTO t VALUES (v1, v2, ...)
      - SELECT cols FROM t [WHERE col {=,<,<=,>,>=} val | col BETWEEN a AND b] [USING col] [LIMIT n]
      - DELETE FROM t WHERE col = val
    """

    def parse(self, query: str) -> Dict[str, Any]:
        toks = tokenize(query)
        words = [v for (_k, v) in toks]
        if not words:
            raise ValueError("Consulta vacía")

        first = words[0].lower()
        if first == "create":
            return self._parse_create(words)
        if first == "insert":
            return self._parse_insert(words)
        if first == "select":
            return self._parse_select(words)
        if first == "delete":
            return self._parse_delete(words)
        raise ValueError(f"Sentencia no soportada: {first}")

    # ---------- CREATE ----------

    def _parse_create(self, w: List[str]) -> Dict[str, Any]:
        # CREATE TABLE <name> ( col TYPE [INDEX kind], ... )
        if len(w) < 3 or w[1].lower() != "table":
            raise ValueError("Sintaxis: CREATE TABLE <name> (...)")
        table = w[2]

        lp = _find(w, "(")
        rp = _find(w, ")")
        if lp == -1 or rp == -1 or rp <= lp + 1:
            raise ValueError("CREATE TABLE requiere definición de columnas entre ()")
        body = w[lp + 1 : rp]

        # separar por comas en items
        items: List[List[str]] = []
        cur: List[str] = []
        for tok in body:
            if tok == ",":
                if cur:
                    items.append(cur)
                cur = []
            else:
                cur.append(tok)
        if cur:
            items.append(cur)

        columns: List[Dict[str, str]] = []
        index_map: Dict[str, str] = {}

        for it in items:
            # it: ["id","INT"]  o  ["nombre","VARCHAR[20]","INDEX","btree"]
            if len(it) < 2:
                raise ValueError(f"Columna mal definida: {' '.join(it)}")
            name = it[0]
            ctype = it[1]
            columns.append({"name": name, "type": ctype})
            if len(it) >= 4 and it[2].lower() == "index":
                index_map[name] = it[3].lower()

        return {"operation": "create", "table": table, "columns": columns, "index_map": index_map}

    # ---------- INSERT ----------

    def _parse_insert(self, w: List[str]) -> Dict[str, Any]:
        # INSERT INTO <t> VALUES (v1, v2, ...)
        if len(w) < 4 or w[1].lower() != "into":
            raise ValueError("Sintaxis: INSERT INTO <tabla> VALUES (...)")
        table = w[2]
        if _find(w, "values") == -1:
            raise ValueError("INSERT requiere VALUES (...)")

        lp = _find(w, "(")
        rp = _find(w, ")")
        if lp == -1 or rp == -1 or rp <= lp + 1:
            raise ValueError("INSERT VALUES requiere paréntesis con valores")
        raw = [t for t in w[lp + 1 : rp] if t != ","]
        values = [_lit(t) for t in raw]
        return {"operation": "insert", "table": table, "values": values}

    # ---------- SELECT (con rangos) ----------

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
            ui = _find(w, "using")
            li = _find(w, "limit")
            if ui != -1:
                end = min(end, ui)
            if li != -1:
                end = min(end, li)
            cond = [t for t in w[wi + 1 : end] if t != ","]

            # BETWEEN
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
                m = {"=": "eq", "==": "eq", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}
                where = {"type": m[op], "column": col, "value": val}

        # USING
        ui = _find(w, "using")
        if ui != -1 and ui + 1 < len(w):
            idx_col = w[ui + 1]

        # LIMIT
        li = _find(w, "limit")
        if li != -1 and li + 1 < len(w):
            limit = int(_lit(w[li + 1]))

        return {
            "operation": "select",
            "table": table,
            "columns": columns,
            "where": where,     # dict estructurado o None
            "index": idx_col,   # columna cuyo índice preferimos usar
            "limit": limit,
        }

    # ---------- DELETE ----------

    def _parse_delete(self, w: List[str]) -> Dict[str, Any]:
        # DELETE FROM t WHERE col = val
        if len(w) < 3 or w[1].lower() != "from":
            raise ValueError("Sintaxis: DELETE FROM <tabla> WHERE ...")
        table = w[2]
        wi = _find(w, "where")
        if wi == -1:
            raise ValueError("DELETE requiere WHERE col = val")

        cond = [t for t in w[wi + 1 :] if t != ","]
        if len(cond) < 3 or cond[1] not in ("=", "=="):
            raise ValueError("WHERE debe ser 'col = valor'")
        where = {"type": "eq", "column": cond[0], "value": _lit(cond[2])}
        return {"operation": "delete", "table": table, "where": where}
