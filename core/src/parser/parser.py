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
