# parser/executor.py
from parser.parser import SQLParser

class Executor:
    def __init__(self, db_engine):
        """
        db_engine: instancia que implementa funciones como:
          - create_table()
          - insert()
          - delete()
          - select()
        """
        self.db = db_engine
        self.parser = SQLParser()

    def execute(self, query: str):
        ast = self.parser.parse(query)

        op = ast["operation"]
        if op == "create":
            return self.db.create_table(ast["table"], ast["details"])
        elif op == "insert":
            return self.db.insert(ast["table"], ast["values"])
        elif op == "delete":
            return self.db.delete(ast["table"], ast["condition"])
        elif op == "select":
            return self.db.select(ast["table"], ast["columns"], ast["condition"])
        else:
            raise ValueError(f"Operación no soportada: {op}")

if __name__ == "__main__":
    class DummyDB:
        def create_table(self, t, d): return f"Tabla {t} creada con {d}"
        def insert(self, t, v): return f"Insert en {t} valores={v}"
        def delete(self, t, c): return f"Delete en {t} cond={c}"
        def select(self, t, cols, c): return f"Select {cols} de {t} cond={c}"

    exe = Executor(DummyDB())
    print(exe.execute("SELECT * FROM Restaurantes WHERE id = 5"))
