# parser/parser.py
from src.parser.lexer import tokenize

class SQLParser:
    def parse(self, query: str):
        tokens = [t[1].lower() if t[0] in ("IDENT", "OP") else t[1] for t in tokenize(query)]
        
        if tokens[0] == "create":
            # Diferenciar CREATE TABLE vs CREATE INDEX
            if tokens[1] == "table":
                return self._parse_create(tokens)
            elif tokens[1] == "index":
                return self._parse_create_index(tokens)
            else:
                raise ValueError("CREATE soporta TABLE o INDEX")
        
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

        # Parsear columnas y los índices asociados
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

            columns.append(col_def)

            # Verificar si existe la palabra clave "index" para aplicar un índice
            if i < len(cols_tokens) and cols_tokens[i].startswith("index"):
                index_type = cols_tokens[i + 1].lower()
                index_map[name] = index_type
                i += 2  # Avanzar para saltar "index" y el tipo de índice

        return {
            "operation": "create",
            "table": table,
            "columns": columns,
            "index_map": index_map
        }

    def _parse_insert(self, tokens):
        # Support two forms:
        # INSERT INTO <table> VALUES (...)
        # INSERT INTO <table> (col1, col2) VALUES (v1, v2)
        table = tokens[2]
        cols = None
        values = None

        if "values" in tokens:
            # find values (...) parentheses
            v_idx = tokens.index("values")
            # find the '(' that starts VALUES(...) and match its closing ')' using nesting
            open_vals = None
            for i in range(v_idx + 1, len(tokens)):
                if tokens[i] == "(":
                    open_vals = i
                    break
            if open_vals is None:
                raise ValueError("Malformed INSERT: missing VALUES(...)")
            # find matching closing paren with nesting
            level = 0
            close_vals = None
            for j in range(open_vals, len(tokens)):
                if tokens[j] == "(":
                    level += 1
                elif tokens[j] == ")":
                    level -= 1
                    if level == 0:
                        close_vals = j
                        break
            if close_vals is None:
                raise ValueError("Malformed INSERT: missing closing ')' for VALUES")
            values = tokens[open_vals + 1:close_vals]
            # remove comma tokens so we get only actual value tokens
            values = [t for t in values if t != ',']

            # check for optional column list between table and VALUES
            open_cols = None
            for i in range(3, v_idx):
                if tokens[i] == "(":
                    open_cols = i
                    break
            if open_cols is not None:
                # find matching closing paren for the column list using nesting
                level = 0
                close_cols = None
                for j in range(open_cols, v_idx):
                    if tokens[j] == "(":
                        level += 1
                    elif tokens[j] == ")":
                        level -= 1
                        if level == 0:
                            close_cols = j
                            break
                if close_cols is None:
                    raise ValueError("Malformed INSERT: missing closing ')' for column list")
                # Build column names by grouping tokens until commas — this allows names containing '/'
                cols = []
                cur = []
                for t in tokens[open_cols + 1:close_cols]:
                    if t == ',':
                        if cur:
                            cols.append(''.join(cur))
                            cur = []
                        continue
                    cur.append(t)
                if cur:
                    cols.append(''.join(cur))
                # strip trailing commas/whitespace
                cols = [c.strip().strip(',') for c in cols]
        else:
            # fallback: naive VALUES(...) detection (no explicit 'VALUES' token)
            open_paren = tokens.index("(")
            close_paren = tokens.index(")")
            values = tokens[open_paren + 1:close_paren]
            values = [t for t in values if t != ',']

        return {
            "operation": "insert",
            "table": table,
            "columns": cols,
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
        # SELECT col FROM table WHERE cond [USING <index>]
        from_index = tokens.index("from")
        raw_columns = tokens[1:from_index]
        
        # Parse columns
        columns = [c.strip(",") for c in raw_columns if c != ","]
        
        table = tokens[from_index + 1]
        
        condition, index, limit = None, None, None

        # Procesar condición WHERE
        if "where" in tokens:
            where_index = tokens.index("where")
            end_idx = len(tokens)
            if "using" in tokens:
                end_idx = tokens.index("using")
            if "limit" in tokens:
                end_idx = min(end_idx, tokens.index("limit"))
            condition = " ".join(tokens[where_index + 1:end_idx])

        # Procesar índice USING
        if "using" in tokens:
            idx_index = tokens.index("using")
            if "limit" in tokens:
                end_idx = tokens.index("limit")
                index = " ".join(tokens[idx_index + 1:end_idx])
            else:
                index = tokens[idx_index + 1]

        # Procesar LIMIT
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

    def _parse_create_index(self, tokens):
        """
        CREATE INDEX <tipo> ON <tabla> (columna)
        Ejemplo:
            CREATE INDEX btree ON empleados (id)
        """
        if len(tokens) < 6:
            raise ValueError("Sintaxis: CREATE INDEX <tipo> ON <tabla> (columna)")
        
        index_type = tokens[2]
        
        if tokens[3] != "on":
            raise ValueError("Sintaxis incorrecta, falta 'ON'")
        
        table = tokens[4]

        if "(" not in tokens or ")" not in tokens:
            raise ValueError("Sintaxis incorrecta, falta (columna)")
        
        open_paren = tokens.index("(")
        close_paren = tokens.index(")")
        column = tokens[open_paren+1:close_paren][0]

        return {
            "operation": "create_index",
            "table": table,
            "index_type": index_type,
            "column": column
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
