import re
from typing import List, Tuple

# Tokens simples para SQL
TOKEN_REGEX = [
    ("NUMBER", r"\d+(\.\d+)?"),  # Número entero o decimal
    ("STRING", r"'[^']*'|\"[^\"]*\""),  # Cadenas de texto entre comillas
    ("IDENT",  r"[a-zA-Z_][a-zA-Z0-9_]*"),  # Identificadores (como nombres de columnas)
    ("SYMBOL", r"[(),;]"),  # Símbolos como paréntesis, comas y punto y coma
    ("OP",     r"(<=|>=|==|=|<|>|between|in)"),  # Operadores
    ("WS",     r"\s+"),  # Espacios en blanco
]

# Crear un patrón de expresiones regulares que combina todos los tokens definidos
token_re = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_REGEX), re.IGNORECASE)

def tokenize(sql: str) -> List[Tuple[str, str]]:
    """Devuelve lista [(tipo, lexema)]. Se ignoran espacios."""
    out: List[Tuple[str, str]] = []
    for m in token_re.finditer(sql):
        kind = m.lastgroup or ""
        val  = m.group()
        if kind == "WS":
            continue
        out.append((kind, val))
    return out

if __name__ == "__main__":
    q = "CREATE TABLE restaurantes (id INT, nombre VARCHAR 100, tipo VARCHAR 50, ubicacion VARCHAR 100, calificacion FLOAT, fecha_apertura DATE);"
    print(tokenize(q))
