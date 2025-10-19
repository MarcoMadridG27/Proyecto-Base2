# src/parser/parser.py
from math import inf
from typing import Any, Dict, List, Optional
from .lexer import tokenize

def _unquote(s: str) -> str:
    s = s.strip()
    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in ("'", '"')):
        return s[1:-1]
    return s

def _lit(tok: str) -> Any:
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

def _find(words: List[str], target: str, start: int = 0) -> int:
    tgt = target.lower()
    for i in range(start, len(words)):
        if words[i].lower() == tgt:
            return i
    return -1

def _slice_exclusive(words: List[str], start_tok: str, end_tok: str, start_at: int = 0) -> tuple[list[str], int, int]:
    """Devuelve (tokens_internos, lp, rp) para el primer bloque start_tok ... end_tok encontrado a partir de start_at."""
    lp = _find(words, start_tok, start_at)
    rp = _find(words, end_tok, (lp + 1) if lp != -1 else start_at)
    if lp == -1 or rp == -1 or rp <= lp + 1:
        return [], -1, -1
    return [t for t in words[lp + 1: rp] if t != ","], lp, rp

class SQLParser:
    """
    - CREATE TABLE t (col TYPE [INDEX kind], ...)
    - CREATE INDEX idx ON table(col[,col2,...]) [USING index_type]
    - INSERT INTO t VALUES (...)
    - SELECT ... FROM t
        WHERE:
          * col =, <, <=, >, >=, BETWEEN
          * NEARBY (c1,c2,...) POINT (x[,y,...]) RADIUS r
          * KNN    (c1,c2,...) POINT (x[,y,...]) K k
    - DELETE FROM t WHERE col = val
    """

    def parse(self, query: str) -> Dict[str, Any]:
        toks = tokenize(query)
        words = [v for (_k, v) in toks]
        if not words:
            raise ValueError("Consulta vacía")

        first = words[0].lower()
        if first == "create":
            if len(words) > 1 and words[1].lower() == "index":
                return self._parse_create_index(words)
            if len(words) > 1 and words[1].lower() == "table":
                return self._parse_create(words)
        if first == "insert":
            return self._parse_insert(words)
        if first == "select":
            return self._parse_select(words)
        if first == "delete":
            return self._parse_delete(words)
        raise ValueError(f"Sentencia no soportada: {first}")

    # --- CREATE TABLE ---

    def _parse_create(self, w: List[str]) -> Dict[str, Any]:
        if len(w) < 3 or w[1].lower() != "table":
            raise ValueError("Sintaxis: CREATE TABLE <name> (...)")
        table = w[2]

        body, lp, rp = _slice_exclusive(w, "(", ")", 3)
        if lp == -1:
            raise ValueError("CREATE TABLE requiere definición de columnas entre ()")

        # partir por comas (ya filtradas arriba)
        items: List[List[str]] = []
        current: List[str] = []
        for tok in body:
            if tok == ",":
                if current:
                    items.append(current)
                current = []
            else:
                current.append(tok)
        if current:
            items.append(current)

        columns: List[Dict[str, str]] = []
        index_map: Dict[str, str] = {}
        for item in items:
            if len(item) < 2:
                raise ValueError(f"Definición de columna inválida: {' '.join(item)}")
            name, ctype = item[0], item[1]
            if ctype.upper() == "VARCHAR" and len(item) >= 3:
                try:
                    size = int(item[2])
                    ctype = f"VARCHAR[{size}]"
                except ValueError:
                    raise ValueError(f"VARCHAR inválido: {item[2]}")
            columns.append({"name": name, "type": ctype})
            if len(item) >= 4 and item[2].lower() == "index":
                index_map[name] = item[3].lower()

        return {"operation": "create", "table": table, "columns": columns, "index_map": index_map}

    # --- CREATE INDEX (soporta columnas múltiples) ---

    def _parse_create_index(self, w: List[str]) -> Dict[str, Any]:
        # CREATE INDEX <idx_name> ON <table> (<c1>[,<c2>...]) [USING <type>]
        if len(w) < 8 or w[1].lower() != "index" or w[3].lower() != "on":
            raise ValueError("Sintaxis: CREATE INDEX <idx_name> ON <table> (<column[, ...]>) [USING <index_type>]")

        idx_name = w[2]
        table = w[4]

        cols, lp, rp = _slice_exclusive(w, "(", ")", 5)
        if lp == -1:
            raise ValueError("CREATE INDEX requiere columna(s) entre paréntesis")
        if not cols:
            raise ValueError("Debe indicar al menos una columna para el índice")

        index_type = "sequential"
        ui = _find(w, "using", rp + 1)
        if ui != -1 and ui + 1 < len(w):
            index_type = w[ui + 1].lower()

        return {
            "operation": "create_index",
            "idx_name": idx_name,
            "table": table,
            "columns": cols,
            "index_type": index_type,
        }

    # --- INSERT ---

    def _parse_insert(self, w: List[str]) -> Dict[str, Any]:
        if len(w) < 4 or w[1].lower() != "into":
            raise ValueError("Sintaxis: INSERT INTO <tabla> VALUES (...)")
        table = w[2]

        if _find(w, "values") == -1:
            raise ValueError("INSERT debe incluir VALUES (...)")

        vals, lp, rp = _slice_exclusive(w, "(", ")", _find(w, "values") + 1)
        if lp == -1:
            raise ValueError("INSERT VALUES requiere paréntesis con valores")
        values = [_lit(t) for t in vals]
        return {"operation": "insert", "table": table, "values": values}

    # --- SELECT (incluye NEARBY/KNN) ---

    def _parse_select(self, w: List[str]) -> Dict[str, Any]:
        fi = _find(w, "from")
        if fi == -1:
            raise ValueError("SELECT requiere FROM")

        raw_cols = [t for t in w[1:fi] if t != ","]
        columns = raw_cols or ["*"]

        if fi + 1 >= len(w):
            raise ValueError("Falta tabla tras FROM")
        table = w[fi + 1]

        where: Optional[Dict[str, Any]] = None
        limit: Optional[int] = None

        wi = _find(w, "where", fi + 2)
        # Bloque condicional hasta LIMIT (si existe)
        end = len(w)
        li = _find(w, "limit", (wi + 1) if wi != -1 else 0)
        if li != -1:
            end = min(end, li)

        if wi != -1:
            cond = [t for t in w[wi + 1: end] if t != ","]

            # --- Espaciales: NEARBY / KNN ---
            if cond and cond[0].lower() in ("nearby", "knn"):
                mode = cond[0].lower()
                cols, pt_vals, extra = self._parse_nearby_or_knn(cond, mode=mode)

                # Validación: #cols == #point
                if len(cols) != len(pt_vals):
                    raise ValueError(f"Dimensión mismatcheada: columnas={len(cols)} vs point={len(pt_vals)}")

                if mode == "nearby":
                    where = {"type": "rt_range", "columns": cols, "point": pt_vals, "radius": extra}
                else:
                    where = {"type": "rt_knn", "columns": cols, "point": pt_vals, "k": int(extra)}

            # --- BETWEEN ---
            elif "between" in [x.lower() for x in cond]:
                bi = _find(cond, "between")
                if bi == 1 and _find(cond, "and") == 3 and len(cond) >= 5:
                    col = cond[0]; lo = _lit(cond[2]); hi = _lit(cond[4])
                    where = {"type": "range", "column": col, "low": lo, "high": hi,
                             "inc_low": True, "inc_high": True}

            # --- Comparadores simples ---
            elif len(cond) >= 3 and cond[1] in ("=", "==", "<", "<=", ">", ">="):
                op = cond[1]; col = cond[0]; val = _lit(cond[2])
                if op in ("=", "=="):
                    where = {"type": "eq", "column": col, "value": val}
                else:
                    if isinstance(val, (int, float)):
                        if op == "<=":
                            where = {"type": "range", "column": col, "low": -inf, "high": val}
                        elif op == ">=":
                            where = {"type": "range", "column": col, "low": val, "high": inf}
                    else:
                        if op == "<=":
                            where = {"type": "range", "column": col, "low": chr(0), "high": val}
                        elif op == ">=":
                            where = {"type": "range", "column": col, "low": val, "high": "{"}

        # LIMIT
        if li != -1 and li + 1 < len(w):
            limit = int(_lit(w[li + 1]))

        return {"operation": "select", "table": table, "columns": columns, "where": where, "limit": limit}

    # --- Helpers espaciales ---

    def _parse_nearby_or_knn(self, cond: List[str], mode: str):
        # NEARBY (c1,c2,...) POINT (x,y[,...]) RADIUS r
        # KNN    (c1,c2,...) POINT (x,y[,...]) K k

        # columnas (primer paréntesis tras la palabra)
        cols, lp, rp = _slice_exclusive(cond, "(", ")", 1)
        if lp == -1:
            raise ValueError("Sintaxis espacial inválida: faltan paréntesis de columnas")

        # POINT ( ... )
        pi = _find(cond, "point", rp + 1)
        if pi == -1:
            raise ValueError("Sintaxis espacial inválida: falta POINT")
        pts, lp2, rp2 = _slice_exclusive(cond, "(", ")", pi + 1)
        if lp2 == -1:
            raise ValueError("Sintaxis espacial inválida en POINT(...)")
        point_vals = [_lit(t) for t in pts]

        if mode == "nearby":
            ridx = _find(cond, "radius", rp2 + 1)
            if ridx == -1 or ridx + 1 >= len(cond):
                raise ValueError("Sintaxis NEARBY inválida: falta RADIUS <r>")
            radius = _lit(cond[ridx + 1])
            return cols, point_vals, radius

        if mode == "knn":
            kidx = _find(cond, "k", rp2 + 1)
            if kidx == -1 or kidx + 1 >= len(cond):
                raise ValueError("Sintaxis KNN inválida: falta K <k>")
            kval = _lit(cond[kidx + 1])
            return cols, point_vals, kval

        raise ValueError("Modo espacial desconocido")

    # --- DELETE ---

    def _parse_delete(self, w: List[str]) -> Dict[str, Any]:
        if len(w) < 3 or w[1].lower() != "from":
            raise ValueError("Sintaxis: DELETE FROM <tabla> WHERE ...")
        table = w[2]
        wi = _find(w, "where")
        if wi == -1:
            raise ValueError("DELETE requiere WHERE col = val")
        cond = [t for t in w[wi + 1:] if t != ","]
        where = {"type": "eq", "column": cond[0], "value": _lit(cond[2])}
        return {"operation": "delete", "table": table, "where": where}
