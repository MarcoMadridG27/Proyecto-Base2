from typing import Any, Dict
from src.parser.parser import SQLParser
from src.model.schema_manager import SchemaManager


class Executor:
    """
    Executor que maneja las consultas SQL:
    - Ejecuta consultas SELECT, INSERT, DELETE.
    - Gestiona la creación de índices a través de CREATE INDEX.
    - Interactúa con el SchemaManager para modificar y consultar tablas.
    """

    def __init__(self, data_dir="data"):
        """
        Inicializa el Executor con el SchemaManager y el SQLParser.

        Args:
            schema_manager: Instancia del SchemaManager para manejar las tablas y operaciones.
            parser: Instancia del SQLParser para analizar las consultas SQL.
        """
        self.schema_manager = SchemaManager(data_dir)
        self.parser = SQLParser()

    def execute(self, query: str) -> Any:
        """
        Ejecuta una consulta SQL dada, utilizando el SQLParser y el SchemaManager.

        Dependiendo de la operación SQL, se dirige a los métodos correspondientes.

        Args:
            query (str): Consulta SQL a ejecutar.

        Returns:
            El resultado de la operación (por ejemplo, el resultado de un SELECT o el número de filas afectadas por un DELETE/INSERT).
        """
        # Parsear la consulta usando el parser
        ast = self.parser.parse(query)

        # Gestionar la operación según el tipo de consulta
        operation = ast["operation"]

        if operation == "create":
            return self._handle_create_table(ast)
        elif operation == "insert":
            return self._handle_insert(ast)
        elif operation == "select":
            return self._handle_select(ast)
        elif operation == "delete":
            return self._handle_delete(ast)
        elif operation == "create_index":
            return self._handle_create_index(ast)
        else:
            raise ValueError(f"Operación no soportada: {operation}")

    def _handle_create_table(self, ast: Dict[str, Any]) -> str:
        """
        Maneja la creación de una tabla.

        Args:
            ast (dict): El árbol de sintaxis abstracta para la operación CREATE TABLE.

        Returns:
            str: Mensaje de éxito o error.
        """
        table = ast["table"]
        columns = ast["columns"]
        index_map = ast.get("index_map", {})

        # Crear la tabla en el SchemaManager
        return self.schema_manager.create_table(table, columns, index_map)

    def _handle_insert(self, ast: Dict[str, Any]) -> int:
        """
        Maneja la operación INSERT INTO.

        Args:
            ast (dict): El árbol de sintaxis abstracta para la operación INSERT.

        Returns:
            int: El offset de la fila insertada.
        """
        table = ast["table"]
        values = ast["values"]

        # Insertar la fila en la tabla
        return self.schema_manager.insert(table, values)

    def _handle_select(self, ast: Dict[str, Any]) -> list[Dict[str, Any]]:
        """
        Maneja la operación SELECT.

        Args:
            ast (dict): El árbol de sintaxis abstracta para la operación SELECT.

        Returns:
            list: Los registros que coinciden con la consulta SELECT.
        """
        table = ast["table"]
        columns = ast["columns"]
        where = ast.get("where")
        limit = ast.get("limit")

        # Ejecutar el SELECT en el SchemaManager
        return self.schema_manager.select(table, columns, where, limit)

    def _handle_delete(self, ast: Dict[str, Any]) -> int:
        """
        Maneja la operación DELETE.

        Args:
            ast (dict): El árbol de sintaxis abstracta para la operación DELETE.

        Returns:
            int: La cantidad de filas borradas.
        """
        table = ast["table"]
        where = ast["where"]

        # Ejecutar el DELETE en el SchemaManager
        return self.schema_manager.delete(table, where)

    def _handle_create_index(self, ast: Dict[str, Any]) -> str:
        """
        Maneja la operación CREATE INDEX.

        Args:
            ast (dict): El árbol de sintaxis abstracta para la operación CREATE INDEX.

        Returns:
            str: Mensaje de éxito o error al crear el índice.
        """
        idx_name = ast["idx_name"]
        table = ast["table"]
        column = ast["column"]
        index_type = ast["index_type"]

        # Crear el índice en el SchemaManager
        return self.schema_manager.create_index(table, column, index_type,idx_name)
