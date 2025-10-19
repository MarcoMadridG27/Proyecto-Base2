import os
import math
import pickle
from typing import List, Tuple, Optional, Any


class KDNode:
    __slots__ = ("point", "offset", "left", "right", "axis")

    def __init__(self, point: List[float], offset: int, axis: int):
        self.point = point
        self.offset = offset
        self.left = None
        self.right = None
        self.axis = axis


class KDTree:
    """
    Simple persistent KD-Tree for 2D/3D points.
    Stores points as (point:list, offset:int) and persists to data_dir/index.pkl.
    Provides add, bulk_add, range_search, count and close.
    This is a deterministic, pure-Python fallback for spatial queries.
    """

    def __init__(self, table_name: str, index_name: str, data_dir: str = "data", dimension: int = 2):
        self.table_name = table_name
        self.index_name = index_name
        self.data_dir = data_dir
        self.dimension = max(2, int(dimension))
        os.makedirs(self.data_dir, exist_ok=True)
        self._store_path = os.path.join(self.data_dir, "index.pkl")
        self._points: List[Tuple[List[float], int]] = []
        self._root: Optional[KDNode] = None
        self._closed = False

        # load if exists
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "rb") as f:
                    self._points = pickle.load(f)
                self._build_tree()
            except Exception:
                # if load fails, start empty
                self._points = []
                self._root = None

    def _build_tree(self):
        def build(points, depth=0):
            if not points:
                return None
            axis = depth % self.dimension
            points.sort(key=lambda x: x[0][axis])
            mid = len(points) // 2
            node = KDNode(points[mid][0], points[mid][1], axis)
            node.left = build(points[:mid], depth + 1)
            node.right = build(points[mid + 1 :], depth + 1)
            return node

        self._root = build(list(self._points), 0)

    def add(self, key: Any, offset: int):
        # Normalize key into a point list of floats
        point = self._key_to_point(key)
        if point is None:
            point = [0.0] * self.dimension
        # persist and rebuild (for simplicity)
        self._points.append((point, int(offset)))
        try:
            with open(self._store_path, "wb") as f:
                pickle.dump(self._points, f)
        except Exception:
            pass
        self._build_tree()

    def bulk_add(self, iterable):
        # iterable yields (key, offset)
        for key, offset in iterable:
            point = self._key_to_point(key)
            if point is None:
                continue
            self._points.append((point, int(offset)))
        try:
            with open(self._store_path, "wb") as f:
                pickle.dump(self._points, f)
        except Exception:
            pass
        self._build_tree()

    def _key_to_point(self, key: Any) -> Optional[List[float]]:
        try:
            if isinstance(key, (list, tuple)):
                vals = [float(k) for k in list(key)[: self.dimension]]
                if len(vals) < self.dimension:
                    vals += [0.0] * (self.dimension - len(vals))
                return vals
            if isinstance(key, str):
                parts = [p.strip() for p in key.replace("[", "").replace("]", "").split(",") if p.strip()]
                if parts:
                    vals = [float(p) for p in parts[: self.dimension]]
                    if len(vals) < self.dimension:
                        vals += [0.0] * (self.dimension - len(vals))
                    return vals
            if isinstance(key, dict):
                # try common orders
                if "lon" in key and "lat" in key:
                    return [float(key.get("lon", 0.0)), float(key.get("lat", 0.0))][: self.dimension]
                if "x" in key and "y" in key:
                    return [float(key.get("x", 0.0)), float(key.get("y", 0.0))][: self.dimension]
        except Exception:
            return None
        return None

    def range_search(self, point: List[float], radius: float):
        if not self._root:
            return []

        # ensure point length
        p = [float(x) for x in point]
        if len(p) < self.dimension:
            p += [0.0] * (self.dimension - len(p))

        radius2 = float(radius) * float(radius)
        results: List[int] = []

        def recur(node):
            if node is None:
                return
            # distance squared
            d2 = sum((node.point[i] - p[i]) ** 2 for i in range(self.dimension))
            if d2 <= radius2:
                results.append(node.offset)
            axis = node.axis
            diff = p[axis] - node.point[axis]
            if diff <= 0:
                recur(node.left)
                if diff * diff <= radius2:
                    recur(node.right)
            else:
                recur(node.right)
                if diff * diff <= radius2:
                    recur(node.left)

        try:
            recur(self._root)
        except Exception:
            return []
        return results

    def count(self):
        return len(self._points)

    def knn_search(self, point: List[float], k: int):
        # naive fallback using full scan + sort
        if not self._points:
            return []
        p = [float(x) for x in point]
        if len(p) < self.dimension:
            p += [0.0] * (self.dimension - len(p))
        arr = []
        for pt, off in self._points:
            d2 = sum((pt[i] - p[i]) ** 2 for i in range(self.dimension))
            arr.append((d2, off))
        arr.sort(key=lambda x: x[0])
        return [off for _, off in arr[:k]]

    def close(self):
        self._closed = True

