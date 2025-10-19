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
		# helper to try parse numeric
		def _to_num(x: Any):
			try:
				if isinstance(x, (int, float)):
					return x
				s = str(x)
				if s.isdigit():
					return int(s)
				return float(s)
			except Exception:
				return None
		k_num = _to_num(k)
		# search in main (binary-like since sorted list)
		offsets: List[int] = []
		lo, hi = 0, len(self._main) - 1
		first = -1
		while lo <= hi:
			mid = (lo + hi) // 2
			mk = self._main[mid][0]
			# try numeric comparison when possible
			mk_num = _to_num(mk)
			if k_num is not None and mk_num is not None:
				if mk_num == k_num:
					first = mid
					hi = mid - 1
				elif mk_num < k_num:
					lo = mid + 1
				else:
					hi = mid - 1
			else:
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
		"""
		Range search that attempts numeric comparison when possible.
		If both begin_key and end_key can be parsed as numbers, perform numeric
		comparison. Otherwise fallback to string comparison.
		When the main area is numeric-sorted (reconstruct sorts numerically when
		possible), we can break early once the key exceeds end_key.
		"""
		res: List[int] = []
		# Try to parse begin/end as numbers
		def _to_num(x: Any):
			try:
				# prefer int when exact
				if isinstance(x, (int, float)):
					return x
				s = str(x)
				if s.isdigit():
					return int(s)
				return float(s)
			except Exception:
				return None

		bk_num = _to_num(begin_key)
		ek_num = _to_num(end_key)
		numeric_range = (bk_num is not None and ek_num is not None)

		# Helper to compare a key value according to numeric_range
		def in_range(kstr: str):
			if numeric_range:
				knum = _to_num(kstr)
				if knum is None:
					return False, None
				return (bk_num <= knum <= ek_num), knum
			else:
				return (str(begin_key) <= kstr <= str(end_key)), None

		# main is sorted; detect if main keys are numeric so we can safely break early
		def _main_all_numeric():
			for k, _ in self._main:
				try:
					_ = float(k)
				except Exception:
					return False
			return True

		main_numeric = _main_all_numeric()
		for mk, mo in self._main:
			ok, knum = in_range(mk)
			if ok:
				res.append(mo)
			# early stop when numeric_range and main is numeric-sorted
			if numeric_range and main_numeric and knum is not None and knum > ek_num:
				break

		# aux is unsorted; must scan all
		for ak, ao in self._aux:
			ok, _ = in_range(ak)
			if ok:
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

		# Decide whether we can sort numerically: test if all keys parse as numbers
		def _all_numeric(items):
			for k, _ in items:
				try:
					_ = float(k)
				except Exception:
					return False
			return True

		if _all_numeric(candidates):
			# sort by numeric value
			candidates.sort(key=lambda it: float(it[0]))
		else:
			# default lexicographic sort
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


