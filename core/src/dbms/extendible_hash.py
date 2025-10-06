import json
import os
from typing import Dict, List, Any

class ExtendibleHash:
	"""
	SimpleIndex persistente basado en JSON para mapear clave -> lista de offsets.
	Se usa como índice por igualdad. No es un hash extensible real, solo un stub funcional.
	"""

	def __init__(self, table_name: str, column: str, data_dir: str = "data"):
		self.table_name = table_name
		self.column = column
		self.data_dir = data_dir
		os.makedirs(self.data_dir, exist_ok=True)
		self.index_path = os.path.join(self.data_dir, f"{self.table_name}.{self.column}.idx.json")
		self._map: Dict[str, List[int]] = {}
		self._load()

	def _load(self) -> None:
		if os.path.exists(self.index_path):
			try:
				with open(self.index_path, "r", encoding="utf-8") as f:
					self._map = json.load(f)
			except Exception:
				self._map = {}

	def _save(self) -> None:
		with open(self.index_path, "w", encoding="utf-8") as f:
			json.dump(self._map, f)

	def add(self, key: Any, offset: int) -> None:
		k = str(key)
		self._map.setdefault(k, []).append(offset)
		self._save()

	def find(self, key: Any) -> List[int]:
		return list(self._map.get(str(key), []))

	def clear(self) -> None:
		self._map = {}
		self._save()
