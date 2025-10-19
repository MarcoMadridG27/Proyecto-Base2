from rtree import index
import os
import threading
import time


class RTreeIndex:

    def __init__(self, storage_path, index_name, dimension: int = 2):

        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

        self.index_path = os.path.join(storage_path, index_name)

        # Propiedades para la creación del índice
        p = index.Property()
        # Allow variable dimension (2D/3D)
        self.dimension = max(2, int(dimension))  # default to at least 2
        p.dimension = self.dimension
        p.dat_extension = 'data'
        p.idx_extension = 'index'

        # Carga el índice si ya existe, de lo contrario lo crea
        # Use try/except to surface errors early
        self.idx = index.Index(self.index_path, properties=p)

    def add(self, item_id, coordinates):
        # Build bounding box for variable dimension: (min1,...,minD, max1,...,maxD)
        # For a point, mins = maxs = coordinates
        try:
            coords = [float(c) for c in coordinates]
        except Exception:
            # fallback to zeros
            coords = [0.0] * self.dimension

        # ensure length
        if len(coords) < self.dimension:
            coords = coords + [0.0] * (self.dimension - len(coords))

        mins = coords[:self.dimension]
        maxs = coords[:self.dimension]
        bounding_box = tuple(mins + maxs)
        # perform insertion
        self.idx.insert(int(item_id), bounding_box)

    def range_search(self, point, radius):
        # Crea un 'bounding box' (caja delimitadora) para la consulta
        try:
            p = [float(c) for c in point]
        except Exception:
            p = [0.0] * self.dimension

        if len(p) < self.dimension:
            p = p + [0.0] * (self.dimension - len(p))

        mins = [p[i] - radius for i in range(self.dimension)]
        maxs = [p[i] + radius for i in range(self.dimension)]
        search_box = tuple(mins + maxs)
        return list(self.idx.intersection(search_box))

    def knn_search(self, point, k):
        # La librería rtree devuelve un generador, lo convertimos a lista
        try:
            return list(self.idx.nearest(coordinates=point, num_results=k))
        except TypeError:
            # fallback to positional args for older/newer rtree versions
            return list(self.idx.nearest(point, k))

    def close(self):
        try:
            self.idx.close()
        except Exception:
            pass

    def count(self):
        try:
            return self.idx.count(self.idx.bounds)
        except Exception:
            return 0


# Compatibility wrapper expected by SchemaManager
class RTree:
    """
    Robust wrapper that keeps a single inner index instance, protects access with a lock,
    and attempts a reopen+retry on failures. Also provides bulk_add for safer bulk population.
    """
    def __init__(self, table_name: str, column: str, data_dir: str = "data", dimension: int = 2):
        # data_dir is already the canonical index directory (data/idx_rtree/<table>/<column>)
        self.storage = data_dir
        self.idx_name = f"{column}"
        self.dimension = max(2, int(dimension))
        self._lock = threading.RLock()
        self._inner = None
        self._error_count = 0
        self._max_errors = 3
        self._disabled = False
        # attempt initial open
        self._open_index()

    def _open_index(self):
        try:
            self._inner = RTreeIndex(self.storage, self.idx_name, dimension=self.dimension)
            # reset error state on successful open
            self._error_count = 0
            self._disabled = False
        except Exception as e:
            print(f"[WARN] RTree: failed to open index {self.idx_name} at {self.storage}: {e}")
            self._inner = None

    def _ensure_inner(self):
        if self._inner is None:
            self._open_index()

    def add(self, key, offset):
        coords = None
        try:
            if isinstance(key, (list, tuple)) and len(key) >= 2:
                coords = [float(key[i]) for i in range(min(len(key), self.dimension))]
            elif isinstance(key, str) and "," in key:
                parts = [p.strip() for p in key.split(',') if p.strip()]
                coords = [float(parts[i]) for i in range(min(len(parts), self.dimension))]
            elif isinstance(key, dict):
                # try common keys
                if "lat" in key and "lon" in key:
                    coords = [float(key["lat"]), float(key["lon"])]
                elif "y" in key and "x" in key:
                    coords = [float(key["y"]), float(key["x"])]
        except Exception as e:
            print(f"[WARN] RTree: failed to parse coordinates from key={key}: {e}")

        if coords is None:
            # fallback location
            coords = [0.0] * self.dimension
            print(f"[WARN] RTree: non-spatial key provided for R-Tree index, storing at (0,...): {key}")

        with self._lock:
            self._ensure_inner()
            if self._inner is None:
                print("[ERROR] RTree.add failed: index not available")
                return

            # normalize coords length
            if len(coords) < self.dimension:
                coords = coords + [0.0] * (self.dimension - len(coords))

            try:
                self._inner.add(int(offset), coords)
            except Exception as e:
                print(f"[ERROR] RTree.add failed: {e}")
                # increment error counter and possibly disable index
                try:
                    self._error_count += 1
                    if self._error_count >= self._max_errors:
                        print(f"[ERROR] RTree: disabling index {self.idx_name} after {self._error_count} errors")
                        try:
                            self._inner.close()
                        except Exception:
                            pass
                        self._inner = None
                        self._disabled = True
                except Exception:
                    pass
                # try to recover: close, reopen, retry once
                try:
                    try:
                        self._inner.close()
                    except Exception:
                        pass
                    time.sleep(0.01)
                    self._open_index()
                    if self._inner is not None:
                        self._inner.add(int(offset), coords)
                except Exception as e2:
                    print(f"[ERROR] RTree.add failed on retry: {e2}")

    def bulk_add(self, iterable):
        """Accepts iterable of (key, offset) and inserts in small batches, reopening index if errors occur."""
        with self._lock:
            self._ensure_inner()
            if self._inner is None:
                print("[WARN] RTree.bulk_add: index not available, skipping")
                return
            for key, offset in iterable:
                try:
                    self.add(key, offset)
                except Exception:
                    # swallow per-item errors but continue
                    continue

    def range_search(self, point, radius):
        with self._lock:
            # if the index has been disabled due to repeated native errors, skip using it
            if getattr(self, "_disabled", False):
                print(f"[WARN] RTree.range_search skipped because index {self.idx_name} is disabled")
                return []
            self._ensure_inner()
            if self._inner is None:
                return []
            try:
                return self._inner.range_search(point, radius)
            except Exception as e:
                print(f"[ERROR] RTree.range_search failed: {e}")
                # increment error counter and disable index if threshold reached
                try:
                    self._error_count += 1
                    if self._error_count >= self._max_errors:
                        print(f"[ERROR] RTree: disabling index {self.idx_name} after {self._error_count} range_search errors")
                        try:
                            self._inner.close()
                        except Exception:
                            pass
                        self._inner = None
                        self._disabled = True
                        return []
                except Exception:
                    pass
                # try reopen once and attempt again
                try:
                    try:
                        self._inner.close()
                    except Exception:
                        pass
                    self._open_index()
                    if self._inner is None:
                        return []
                    return self._inner.range_search(point, radius)
                except Exception as e2:
                    print(f"[ERROR] RTree.range_search retry failed: {e2}")
                    return []

    def knn_search(self, point, k):
        with self._lock:
            self._ensure_inner()
            if self._inner is None:
                return []
            try:
                return self._inner.knn_search(point, k)
            except Exception as e:
                print(f"[ERROR] RTree.knn_search failed: {e}")
                return []

    def close(self):
        with self._lock:
            try:
                if self._inner is not None:
                    self._inner.close()
            except Exception:
                pass
            self._inner = None

    def count(self):
        with self._lock:
            try:
                if self._inner is not None:
                    return self._inner.count()
            except Exception:
                pass
            return 0