import re
from typing import List, Tuple

# Tokens simples para SQL muy básico
TOKEN_REGEX = [
    ("NUMBER", r"\d+(\.\d+)?"),
    ("STRING", r"'[^']*'|\"[^\"]*\""),
    ("IDENT",  r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("SYMBOL", r"[(),]"),
    ("OP",     r"(<=|>=|==|=|<|>|between|in)"),
    ("WS",     r"\s+"),
]
token_re = re.compile("|".join(f"(?P<{n}>{p})" for n,p in TOKEN_REGEX), re.IGNORECASE)

def tokenize(sql: str) -> List[Tuple[str, str]]:
    """Devuelve lista [(tipo, lexema)]. Se ignoran espacios."""
    out: List[Tuple[str,str]] = []
    for m in token_re.finditer(sql):
        kind = m.lastgroup or ""
        val  = m.group()
        if kind == "WS":
            continue
        out.append((kind, val))
    return out
if __name__ == "__main__":
    q = "SELECT * FROM Restaurantes WHERE id == 10"
    print(tokenize(q))
