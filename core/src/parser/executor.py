# parser/executor.py
from src.parser.parser import SQLParser
from src.schema_manager import SchemaManager


class Executor:
    def __init__(self, data_dir="data"):
        """
        El Executor se conecta con el SchemaManager, 
        que maneja tablas, archivos e índices.
        """
        self.schema_manager = SchemaManager(data_dir)
        self.parser = SQLParser()

    def execute(self, query: str, use_index: bool = True):
        # Parseamos la consulta SQL
        ast = self.parser.parse(query)
        op = ast["operation"]

        if op == "create":
            # Crear tabla con posibles índices
            return self.schema_manager.create_table(
                ast["table"], ast["columns"], ast.get("index_map")
            )

        elif op == "insert":
            # Insertar datos en la tabla
            return self.schema_manager.insert(ast["table"], ast["values"])

        elif op == "delete":
            # Eliminar datos de la tabla
            return self.schema_manager.delete(ast["table"], ast["condition"])

        elif op == "select":
            table_name = ast["table"]
            has_any_index = False
            try:
                tbl = self.schema_manager.tables.get(table_name)
                if tbl and tbl.get("indexes"):
                    has_any_index = len(tbl["indexes"]) > 0
            except Exception:
                has_any_index = False

            if use_index and has_any_index:
                # Intentar usar índice real (SchemaManager.select usa índice si aplica)
                rows = self.schema_manager.select(
                    table_name,
                    ast["columns"],
                    ast.get("condition"),
                    index=ast.get("index"),
                    limit=ast.get("limit")
                )
                # Detectar si realmente aplicó índice: parseo sencillo y consulta rápida
                eq_col, _ = self.schema_manager._parse_simple_equality(ast.get("condition")) if ast.get("condition") else (None, None)
                used = bool(eq_col and self.schema_manager.tables.get(table_name, {}).get("indexes", {}).get(eq_col))
                warning = None if used else f"No index available for column '{eq_col}' in condition"
                return {"result": rows, "used_index": used, "index_warning": warning}
            elif use_index and not has_any_index:
                # No hay índices disponibles, ejecutar sin índice pero con advertencia
                rows = self.schema_manager.select_without_index(
                    table_name,
                    ast["columns"],
                    ast["condition"],
                    limit=ast.get("limit")
                )
                return {"result": rows, "used_index": False, "index_warning": f"No indexes available for table '{table_name}'"}
            else:
                rows = self.schema_manager.select_without_index(
                    table_name,
                    ast["columns"],
                    ast["condition"],
                    limit=ast.get("limit")
                )
                return {"result": rows, "used_index": False, "index_warning": None}

        elif op == "create_index":
            # Crear un índice en una columna de una tabla
            return self.schema_manager.create_index(
                ast["table"], ast["column"], ast["index_type"]
            )

        else:
            raise ValueError(f"Operación no soportada: {op}")


if __name__ == "__main__":
    exe = Executor()

    # Simulaciones de operaciones SQL
    q1 = "CREATE TABLE Restaurantes (id INT, nombre VARCHAR[20], fecha DATE) USING btree(id)"
    print(exe.execute(q1))  # Crear tabla con índice BTree en 'id'

    q2 = "INSERT INTO Restaurantes VALUES (1, 'KFC', '2023-01-01')"
    print(exe.execute(q2))  # Insertar un registro en Restaurantes

    q3 = "SELECT * FROM Restaurantes WHERE id = 1"
    print(exe.execute(q3))  # Consultar registros con 'id' = 1

    q4 = "CREATE INDEX btree ON Restaurantes (nombre)"
    print(exe.execute(q4))  # Crear índice BTree en la columna 'nombre'
