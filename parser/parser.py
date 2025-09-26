# parser/parser.py
from parser.lexer import tokenize

class SQLParser:
    def parse(self, query: str):
        tokens = [t[1].lower() if t[0] in ("IDENT", "OP") else t[1] for t in tokenize(query)]
        if tokens[0] == "create":
            return self._parse_create(tokens)
        elif tokens[0] == "insert":
            return self._parse_insert(tokens)
        elif tokens[0] == "delete":
            return self._parse_delete(tokens)
        elif tokens[0] == "select":
            return self._parse_select(tokens)
        else:
            raise ValueError("Sentencia SQL no soportada")

    def _parse_create(self, tokens):
        # CREATE TABLE <name> FROM FILE "x.csv" USING INDEX isam("id")
        table = tokens[2]
        return {
            "operation": "create",
            "table": table,
            "details": tokens[3:]
        }

    def _parse_insert(self, tokens):
        # INSERT INTO <table> VALUES (...)
        table = tokens[2]
        open_paren = tokens.index("(")
        close_paren = tokens.index(")")
        values = tokens[open_paren+1:close_paren]
        return {
            "operation": "insert",
            "table": table,
            "values": [v.strip(",") for v in values]
        }

    def _parse_delete(self, tokens):
        # DELETE FROM <table> WHERE <cond>
        table = tokens[2]
        where_index = tokens.index("where")
        condition = tokens[where_index+1:]
        return {
            "operation": "delete",
            "table": table,
            "condition": " ".join(condition)
        }

    def _parse_select(self, tokens):
        # SELECT col FROM table WHERE cond
        from_index = tokens.index("from")
        columns = tokens[1:from_index]
        table = tokens[from_index+1]
        if "where" in tokens:
            where_index = tokens.index("where")
            condition = tokens[where_index+1:]
        else:
            condition = None
        return {
            "operation": "select",
            "table": table,
            "columns": columns,
            "condition": " ".join(condition) if condition else None
        }

if __name__ == "__main__":
    parser = SQLParser()
    q1 = "SELECT * FROM Restaurantes WHERE id = 10"
    print(parser.parse(q1))
