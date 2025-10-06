import os
import json
from typing import Any, List, Dict, Tuple


class SequentialIndex:
	"""
	Sequential Index with main (ordered) and auxiliary (unsorted) areas.
	- add(key, offset): appends into auxiliary; when aux reaches K, reconstructs
	- find(key): returns list of offsets for exact key
	- range_search(a, b): returns offsets whose key is in [a, b]
	- remove(key): marks in-memory; reconstruction will drop deleted keys

	Persists as JSON arrays: main = sorted list of [key, offset], aux = list of [key, offset].
	This models the behavior without binary packing, focusing on correctness and clarity.
	"""

	def __init__(self, table_name: str, column: str, data_dir: str = "data", aux_limit: int = 32):
		self.table_name = table_name
		self.column = column
		self.data_dir = data_dir
		self.aux_limit = max(4, int(aux_limit))
		os.makedirs(self.data_dir, exist_ok=True)
		self.main_path = os.path.join(self.data_dir, f"{self.table_name}.{self.column}.sidx.json")
		self.aux_path = os.path.join(self.data_dir, f"{self.table_name}.{self.column}.sidx.aux.json")
		self._main: List[Tuple[str, int]] = []
		self._aux: List[Tuple[str, int]] = []
		self._load()

	def _load(self) -> None:
		if os.path.exists(self.main_path):
			try:
				with open(self.main_path, "r", encoding="utf-8") as f:
					self._main = [(str(k), int(o)) for k, o in json.load(f)]
			except Exception:
				self._main = []
		if os.path.exists(self.aux_path):
			try:
				with open(self.aux_path, "r", encoding="utf-8") as f:
					self._aux = [(str(k), int(o)) for k, o in json.load(f)]
			except Exception:
				self._aux = []

	def _save(self) -> None:
		with open(self.main_path, "w", encoding="utf-8") as f:
			json.dump(self._main, f)
		with open(self.aux_path, "w", encoding="utf-8") as f:
			json.dump(self._aux, f)

	def add(self, key: Any, offset: int) -> None:
		k = str(key)
		self._aux.append((k, int(offset)))
		if len(self._aux) >= self.aux_limit:
			self.reconstruct()
		else:
			self._save()

	def find(self, key: Any) -> List[int]:
		k = str(key)
		# search in main (binary-like since sorted list)
		offsets: List[int] = []
		lo, hi = 0, len(self._main) - 1
		first = -1
		while lo <= hi:
			mid = (lo + hi) // 2
			mk = self._main[mid][0]
			if mk == k:
				first = mid
				hi = mid - 1
			elif mk < k:
				lo = mid + 1
			else:
				hi = mid - 1
		if first != -1:
			# collect contiguous equals
			i = first
			while i < len(self._main) and self._main[i][0] == k:
				offsets.append(self._main[i][1])
				i += 1
		# scan aux
		for ak, ao in self._aux:
			if ak == k:
				offsets.append(ao)
		return offsets

	def range_search(self, begin_key: Any, end_key: Any) -> List[int]:
		bk, ek = str(begin_key), str(end_key)
		res: List[int] = []
		# main is sorted
		for mk, mo in self._main:
			if bk <= mk <= ek:
				res.append(mo)
		# aux is unsorted
		for ak, ao in self._aux:
			if bk <= ak <= ek:
				res.append(ao)
		return res

	def remove(self, key: Any) -> None:
		# Append a special tombstone in aux; reconstruction will drop
		self._aux.append((f"__DEL__::{str(key)}", -1))
		if len(self._aux) >= self.aux_limit:
			self.reconstruct()
		else:
			self._save()

	def reconstruct(self) -> None:
		# Build a merged, sorted main removing tombstones
		delete_keys = {k.split("::", 1)[1] for k, o in self._aux if k.startswith("__DEL__::")}
		candidates = [x for x in self._main if x[0] not in delete_keys]
		candidates.extend([(k, o) for k, o in self._aux if not k.startswith("__DEL__::")])
		candidates.sort(key=lambda it: it[0])
		self._main = candidates
		self._aux = []
		self._save()

	def info(self) -> Dict[str, Any]:
		return {
			"table": self.table_name,
			"column": self.column,
			"aux_limit": self.aux_limit,
			"main_count": len(self._main),
			"aux_count": len(self._aux),
			"sample_main": self._main[:20],
			"sample_aux": self._aux[:20],
		}


