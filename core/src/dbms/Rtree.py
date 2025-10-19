# src/dbms/Rtree.py
from rtree import index
import os, sqlite3
from typing import Iterable, List, Sequence, Tuple, Optional

class RTree:
    def __init__(self, table: str, column_type: str, idx_name: Optional[str] = None):
        base = "/app/src/dbms/data_index"
        os.makedirs(base, exist_ok=True)

        self.dim = self._parse_dimension(column_type)  # "2f" -> 2
        safe_name = f"{table}_{idx_name or 'rtree'}_d{self.dim}"
        self.basepath = os.path.join(base, safe_name)
        self.sqlite_path = self.basepath + ".sqlite"

        p = index.Property()
        p.dimension = self.dim
        p.dat_extension = "data"
        p.idx_extension = "index"

        self.idx = self._open_or_recreate_index(p)

        self.db = sqlite3.connect(self.sqlite_path)
        self._init_sqlite()

    def _open_or_recreate_index(self, props: index.Property):
        try:
            return index.Index(self.basepath, properties=props)
        except Exception:
            # índice corrupto: eliminar y recrear
            for ext in (".data", ".index"):
                f = self.basepath + ext
                if os.path.exists(f):
                    try: os.remove(f)
                    except: pass
            return index.Index(self.basepath, properties=props)

    @staticmethod
    def _parse_dimension(column_type: str) -> int:
        n = 0
        for ch in column_type:
            if ch.isdigit():
                n = n * 10 + int(ch)
            else:
                break
        return n if n > 0 else 2

    def _init_sqlite(self):
        cur = self.db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id   INTEGER PRIMARY KEY,
                dims INTEGER NOT NULL,
                bbox TEXT NOT NULL  -- CSV: min...,max...
            )
        """)
        self.db.commit()

    @staticmethod
    def _serialize_bbox(bbox: Iterable[float]) -> str:
        return ",".join(str(float(x)) for x in bbox)

    @staticmethod
    def _deserialize_bbox(s: str) -> Tuple[float, ...]:
        return tuple(float(x) for x in s.split(",")) if s else tuple()

    def _bbox_from_point(self, point: Sequence[float]) -> Tuple[float, ...]:
        # cast seguro a float y pareja min..max consistente
        p = [float(x) for x in point]
        return tuple(p + p)  # (min...,max...) = (p...,p...)

    def insert(self, point: Sequence[float], row_off: int) -> None:
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")

        bbox = self._bbox_from_point(point)              # floats
        self.idx.insert(int(row_off), bbox)

        cur = self.db.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO items (id, dims, bbox) VALUES (?, ?, ?)",
            (int(row_off), self.dim, self._serialize_bbox(bbox))
        )
        self.db.commit()

    def range_search(self, point: Sequence[float], radius: float) -> List[int]:
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")

        p = [float(x) for x in point]
        r = float(radius)
        mins = [p[i] - r for i in range(self.dim)]
        maxs = [p[i] + r for i in range(self.dim)]
        query_bbox = tuple(mins + maxs)
        return list(self.idx.intersection(query_bbox))  # ids

    def knn_search(self, point: Sequence[float], k: int) -> List[int]:
        print(point)
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")
        p = tuple(float(x) for x in point)
        k = max(1, int(k))
        return list(self.idx.nearest(coordinates=p, num_results=k))

    def search(self, point: Sequence[float]) -> List[int]:
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")
        bbox = self._bbox_from_point(point)
        candidates = list(self.idx.intersection(bbox))
        if not candidates:
            return []
        want = self._serialize_bbox(bbox)
        cur = self.db.cursor()
        q = f"SELECT id FROM items WHERE id IN ({','.join('?'*len(candidates))}) AND bbox = ?"
        rows = cur.execute(q, [*map(int, candidates), want]).fetchall()
        return [int(r[0]) for r in rows]

    def delete(self, row_off: int) -> List[int]:
        cur = self.db.cursor()
        row = cur.execute("SELECT bbox FROM items WHERE id = ?", (int(row_off),)).fetchone()
        if not row:
            return [-1]
        bbox = self._deserialize_bbox(row[0])
        try:
            self.idx.delete(int(row_off), tuple(bbox))
        except Exception:
            pass
        cur.execute("DELETE FROM items WHERE id = ?", (int(row_off),))
        self.db.commit()
        return [int(row_off)]

    def close(self):
        try: self.idx.close()
        finally:
            try: self.db.close()
            except: pass
