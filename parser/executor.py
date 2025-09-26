# parser/executor.py
from parser.parser import SQLParser
from core.schema_manager import SchemaManager

class Executor:
    def __init__(self, data_dir="data"):
        """
        El Executor se conecta con el SchemaManager, 
        que maneja tablas, archivos e índices.
        """
        self.db = SchemaManager(data_dir)
        self.parser = SQLParser()

    def execute(self, query: str):
        ast = self.parser.parse(query)
        op = ast["operation"]

        if op == "create":
            # ast["details"] debe tener columns + index_map
            return self.db.create_table(ast["table"], ast["columns"], ast.get("index_map"))

        elif op == "insert":
            return self.db.insert(ast["table"], ast["values"])

        elif op == "delete":
            return self.db.delete(ast["table"], ast["condition"])

        elif op == "select":
            return self.db.select(
                ast["table"],
                ast["columns"],
                ast["condition"],
                index=ast.get("index")  # si en la query eliges índice explícito
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
