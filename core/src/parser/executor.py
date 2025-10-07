from typing import Any, Dict
# Importa el parser y el manager con rutas ABSOLUTAS (evita problemas de paquete)
from src.model.parser.parser import SQLParser
from src.model.schema_manager import SchemaManager


class Executor:
    """
    Traductor de AST (parseado por SQLParser) a llamadas de SchemaManager.
    No hace I/O directo de archivos; todo pasa por el manager.
    """

    def __init__(self, data_dir: str = "data"):
        self.schema_manager = SchemaManager(data_dir)
        self.parser = SQLParser()

    def execute(self, query: str):
        """
        1) Parsea la consulta a un dict (AST).
        2) Despacha a la operación correspondiente en el manager.
        3) Retorna el resultado (mensaje, lista de filas, entero, etc.).
        """
        ast: Dict[str, Any] = self.parser.parse(query)
        op = ast["operation"]

        # ---------- CREATE ----------
        if op == "create":
            # ast: {operation, table, columns, index_map}
            return self.schema_manager.create_table(
                ast["table"], ast["columns"], ast.get("index_map")
            )

        # ---------- INSERT ----------
        elif op == "insert":
            # ast: {operation, table, values(list)}
            table = ast["table"]
            values = ast["values"]

            # Convertimos la lista de valores a dict usando el orden del schema
            schema = self.schema_manager.tables[table]["schema"]
            cols = [c["name"] for c in schema.columns]
            row = {cols[i]: (values[i] if i < len(values) else None) for i in range(len(cols))}

            return self.schema_manager.insert(table, row)

        # ---------- SELECT ----------
        elif op == "select":
            # ast: {operation, table, columns, where(dict|None), index(str|None), limit(int|None)}
            return self.schema_manager.select(
                ast["table"],
                ast.get("columns"),
                where=ast.get("where"),
                index=ast.get("index"),
                limit=ast.get("limit"),
            )

        # ---------- DELETE ----------
        elif op == "delete":
            # ast: {operation, table, where(dict)}
            return self.schema_manager.delete(ast["table"], ast.get("where"))

        else:
            raise ValueError(f"Operación no soportada: {op}")


# Uso rápido manual:
if __name__ == "__main__":
    exe = Executor()

    print(exe.execute("""
        CREATE TABLE restaurantes (
            id INT INDEX isam,
            nombre VARCHAR[20] INDEX btree,
            fecha DATE
        )
    """))

    print(exe.execute("INSERT INTO restaurantes VALUES (1, 'KFC', '2023-01-01')"))
    print(exe.execute("INSERT INTO restaurantes VALUES (2, 'PizzaHut', '2023-01-02')"))

    # SELECT con igualdad (usa índice si existe en 'id' o si dices USING id)
    print(exe.execute("SELECT id,nombre FROM restaurantes WHERE id = 2 LIMIT 5"))
    print(exe.execute("SELECT * FROM restaurantes WHERE id = 2 USING id LIMIT 5"))

    # Full scan
    print(exe.execute("SELECT * FROM restaurantes"))
