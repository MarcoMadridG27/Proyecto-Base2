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

    def execute(self, query: str):
        ast = self.parser.parse(query)
        op = ast["operation"]

        if op == "create":
            return self.schema_manager.create_table(
                ast["table"], ast["columns"], ast.get("index_map")
            )

        elif op == "insert":
            return self.schema_manager.insert(ast["table"], ast["values"])

        elif op == "delete":
            return self.schema_manager.delete(ast["table"], ast["condition"])

        elif op == "select":
            return self.schema_manager.select(
                ast["table"],
                ast["columns"],
                ast["condition"],
                index=ast.get("index"),
                limit=ast.get("limit")
            )


        else:
            raise ValueError(f"Operación no soportada: {op}")


if __name__ == "__main__":
    exe = Executor()

    # Simulaciones
    q1 = "CREATE TABLE Restaurantes (id INT, nombre VARCHAR[20], fecha DATE) USING btree(id)"
    print(exe.execute(q1))

    q2 = "INSERT INTO Restaurantes VALUES (1, 'KFC', '2023-01-01')"
    print(exe.execute(q2))

    q3 = "SELECT * FROM Restaurantes WHERE id = 1"
    print(exe.execute(q3))
