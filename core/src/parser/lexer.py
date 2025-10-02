# parser/lexer.py
import re

# Definición de tokens básicos
TOKEN_REGEX = [
    ("NUMBER", r"\d+(\.\d+)?"),
    ("STRING", r"'[^']*'|\"[^\"]*\""),
    ("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("SYMBOL", r"[(),=*]"),
    ("OP", r"(=|<=|>=|<|>|between|in)"),
    ("WS", r"\s+"),
]

token_re = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_REGEX), re.IGNORECASE)

def tokenize(query: str):
    tokens = []
    for match in token_re.finditer(query):
        kind = match.lastgroup
        value = match.group()
        if kind == "WS":
            continue
        tokens.append((kind, value))
    return tokens

if __name__ == "__main__":
    q = "SELECT * FROM Restaurantes WHERE id = 10"
    print(tokenize(q))
