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
            if use_index:
                # Ejecutar la consulta con el índice
                return self.schema_manager.select(
                    ast["table"],
                    ast["columns"],
                    ast["condition"],
                    index=ast.get("index"),
                    limit=ast.get("limit")
                )
            else:
                # Ejecutar la consulta directamente sobre el archivo `.dat` (sin índice)
                return self.schema_manager.select_without_index(
                    ast["table"],
                    ast["columns"],
                    ast["condition"],
                    limit=ast.get("limit")
                )

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
