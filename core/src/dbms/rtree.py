# src/dbms/rtree.py
import os
import sqlite3
import math
from typing import Iterable, List, Sequence, Tuple, Optional

try:
    from rtree import index as rtree_index  # type: ignore
    _HAVE_RTREE = True
except Exception:
    rtree_index = None
    _HAVE_RTREE = False

# KDTree support removed; only libspatialindex (rtree) or sqlite scan fallbacks remain.
KDTree = None
_HAVE_KDTREE = False


class RTree:
    def __init__(self, table: str, column: str, data_dir: Optional[str] = None, dimension: Optional[int] = None, idx_name: Optional[str] = None):
        if data_dir:
            base = data_dir
        else:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "idx_rtree"))
        os.makedirs(base, exist_ok=True)

        self.dim = int(dimension) if dimension else self._parse_dimension(column)
        safe_name = f"{table}_{idx_name or column}_d{self.dim}"
        self.basepath = os.path.join(base, safe_name)
        self.sqlite_path = self.basepath + ".sqlite"

        self.idx = None
        if _HAVE_RTREE:
            p = rtree_index.Property()
            p.dimension = self.dim
            try:
                self.idx = self._open_or_recreate_index(p)
            except Exception:
                self.idx = self._open_or_recreate_index(p)

        self.db = sqlite3.connect(self.sqlite_path)
        self._init_sqlite()

        # no KDTree initialization (removed)
        self._kd = None

    def _open_or_recreate_index(self, props):
        try:
            return rtree_index.Index(self.basepath, properties=props)
        except Exception:
            for ext in (".data", ".index", ".dat", ".idx"):
                f = self.basepath + ext
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            return rtree_index.Index(self.basepath, properties=props)

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
                bbox TEXT NOT NULL
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
        p = [float(x) for x in point]
        return tuple(p + p)

    def insert(self, point: Sequence[float], row_off: int) -> None:
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")

        bbox = self._bbox_from_point(point)
        if self.idx is not None:
            try:
                self.idx.insert(int(row_off), bbox)
            except Exception:
                pass

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

        if self.idx is not None:
            try:
                return list(self.idx.intersection(query_bbox))
            except Exception:
                pass

        # Fallback: linear scan in sqlite and distance filter
        cur = self.db.cursor()
        rows = cur.execute("SELECT id, bbox FROM items WHERE dims = ?", (self.dim,)).fetchall()
        out: List[int] = []
        for rid, bbox_s in rows:
            bbox = self._deserialize_bbox(bbox_s)
            pt = tuple(bbox[:self.dim])
            inside = True
            for i in range(self.dim):
                if pt[i] < mins[i] or pt[i] > maxs[i]:
                    inside = False
                    break
            if not inside:
                continue
            out.append(int(rid))
        return out

    def knn_search(self, point: Sequence[float], k: int) -> List[int]:
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")
        if self.idx is not None:
            try:
                p = tuple(float(x) for x in point)
                return list(self.idx.nearest(coordinates=p, num_results=max(1, int(k))))
            except Exception:
                pass

        # no KDTree available; final fallback is brute-force distance sort

        # final fallback: brute-force distance sort
        cur = self.db.cursor()
        rows = cur.execute("SELECT id, bbox FROM items WHERE dims = ?", (self.dim,)).fetchall()
        pts = []
        for rid, bbox_s in rows:
            bbox = self._deserialize_bbox(bbox_s)
            pt = tuple(bbox[:self.dim])
            pts.append((int(rid), pt))
        def dist(a, b):
            return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(self.dim)))
        pts.sort(key=lambda it: dist(it[1], point))
        return [rid for rid, _ in pts[:max(1, int(k))]]

    def search(self, point: Sequence[float]) -> List[int]:
        if len(point) != self.dim:
            raise ValueError(f"Dimensión mismatcheada: {len(point)}D vs {self.dim}D")
        bbox = self._bbox_from_point(point)
        if self.idx is not None:
            try:
                candidates = list(self.idx.intersection(bbox))
            except Exception:
                candidates = []
        else:
            cur = self.db.cursor()
            rows = cur.execute("SELECT id, bbox FROM items WHERE dims = ?", (self.dim,)).fetchall()
            candidates = [int(rid) for rid, _ in rows]

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
        if self.idx is not None:
            try:
                self.idx.delete(int(row_off), tuple(bbox))
            except Exception:
                pass
        cur.execute("DELETE FROM items WHERE id = ?", (int(row_off),))
        self.db.commit()
        return [int(row_off)]

    def close(self):
        try:
            if self.idx is not None:
                try:
                    self.idx.close()
                except Exception:
                    pass
        finally:
            try:
                self.db.close()
            except Exception:
                pass