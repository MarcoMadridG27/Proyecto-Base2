# src/executor.py
from typing import Any, Dict, List
from src.parser.parser import SQLParser
from src.model.schema_manager import SchemaManager


class Executor:
    """
    Orquesta el parseo y delega la ejecución al SchemaManager.
    Ahora soporta CREATE INDEX con múltiples columnas (rtree) y
    predicados espaciales (NEARBY/KNN) en SELECT.
    """

    def __init__(self, data_dir: str = "data"):
        self.schema_manager = SchemaManager(data_dir=data_dir)
        self.parser = SQLParser()

    def execute(self, query: str) -> Any:
        ast = self.parser.parse(query)
        op = ast["operation"]

        if op == "create":
            return self._handle_create_table(ast)
        if op == "insert":
            return self._handle_insert(ast)
        if op == "select":
            return self._handle_select(ast)
        if op == "delete":
            return self._handle_delete(ast)
        if op == "create_index":
            return self._handle_create_index(ast)
        raise ValueError(f"Operación no soportada: {op}")

    # --- Handlers ---

    def _handle_create_table(self, ast: Dict[str, Any]) -> str:
        return self.schema_manager.create_table(
            ast["table"],
            ast["columns"],
            ast.get("index_map", {}),
        )

    def _handle_insert(self, ast: Dict[str, Any]) -> int:
        # Si INSERT viene como lista, SchemaManager ya sabe convertirla a dict.
        return self.schema_manager.insert(ast["table"], ast["values"])

    def _handle_select(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.schema_manager.select(
            table=ast["table"],
            columns=ast["columns"],
            where=ast.get("where"),
            limit=ast.get("limit"),
        )

    def _handle_delete(self, ast: Dict[str, Any]) -> int:
        return self.schema_manager.delete(ast["table"], ast["where"])

    def _handle_create_index(self, ast: Dict[str, Any]) -> str:
        """
        Admite:
          - 1D: "columns" = [col]
          - Multi-col (RTree): "columns" = [c1, c2, ...]
        El RTree usa column_type = f"{len(columns)}f" (p.ej., '2f', '3f'), que
        el constructor de RTree usa para fijar la dimensión.
        """
        idx_name = ast["idx_name"]
        table = ast["table"]
        columns = ast.get("columns")
        index_type = ast["index_type"]

        # Backward compatibility con parser antiguo:
        if not columns and "column" in ast:
            columns = [ast["column"]]

        if not columns or not isinstance(columns, list):
            raise ValueError("CREATE INDEX requiere una lista de columnas (al menos una)")

        return self.schema_manager.create_index(
            table=table,
            columns=columns,
            index_type=index_type,
            idx_name=idx_name,
        )
