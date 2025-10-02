# parser/parser.py
from src.parser.lexer import tokenize  

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
        """
        CREATE TABLE Restaurantes (
            id INT INDEX isam,
            nombre VARCHAR[20] INDEX btree,
            fecha DATE
        )
        """
        table = tokens[2]
        # Extraer definición de columnas entre paréntesis
        if "(" in tokens and ")" in tokens:
            open_paren = tokens.index("(")
            close_paren = len(tokens) - 1 - tokens[::-1].index(")")
            cols_tokens = tokens[open_paren+1:close_paren]
        else:
            raise ValueError("CREATE TABLE debe definir columnas")


        # Parsear columnas
        columns, index_map = [], {}
        i = 0
        valid_types = {"INT", "FLOAT", "DATE", "VARCHAR", "CHAR"}
        while i < len(cols_tokens):
                if i+1 >= len(cols_tokens):
                    break
                name = cols_tokens[i]
                ctype = cols_tokens[i+1].upper()
                
                # Normalizar VARCHAR sin tamaño a VARCHAR[100]
                if ctype == "VARCHAR" and i+2 < len(cols_tokens) and not cols_tokens[i+2].startswith("["):
                    ctype = "VARCHAR[100]"
                
                if ctype not in valid_types and not ctype.startswith("VARCHAR["):
                    ctype = "VARCHAR[100]"
                    
                col_def = {"name": name, "type": ctype}
                i += 2
                
                # Si el siguiente token es tamaño [20], lo agregamos al tipo
                if i < len(cols_tokens) and cols_tokens[i].startswith("["):
                    ctype += cols_tokens[i]
                    i += 1

        return {
            "operation": "create",
            "table": table,
            "columns": columns,
            "index_map": index_map
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

        from_index = tokens.index("from")
        raw_columns = tokens[1:from_index]

        columns = [c.strip(",") for c in raw_columns if c != ","]

        table = tokens[from_index + 1]

        condition, index, limit = None, None, None

        if "where" in tokens:
            where_index = tokens.index("where")
            end_idx = len(tokens)
            if "using" in tokens:
                end_idx = tokens.index("using")
            if "limit" in tokens:
                end_idx = min(end_idx, tokens.index("limit"))
            condition = " ".join(tokens[where_index + 1:end_idx])

        if "using" in tokens:
            idx_index = tokens.index("using")
            # hasta LIMIT o fin
            if "limit" in tokens:
                end_idx = tokens.index("limit")
                index = " ".join(tokens[idx_index + 1:end_idx])
            else:
                index = tokens[idx_index + 1]

        if "limit" in tokens:
            limit_index = tokens.index("limit")
            try:
                limit = int(tokens[limit_index + 1])
            except:
                raise ValueError("LIMIT debe ir seguido de un número entero")

        return {
            "operation": "select",
            "table": table,
            "columns": columns if columns else ["*"],
            "condition": condition,
            "index": index,
            "limit": limit
        }



if __name__ == "__main__":
    parser = SQLParser()

    q1 = """
    CREATE TABLE Restaurantes (
        id int index isam,
        nombre varchar[20] index btree,
        fecha date
    )
    """
    print(parser.parse(q1))

    q2 = "INSERT INTO Restaurantes VALUES (1, 'KFC', '2023-01-01')"
    print(parser.parse(q2))

    q3 = "SELECT * FROM Restaurantes WHERE id = 10 USING btree"
    print(parser.parse(q3))
