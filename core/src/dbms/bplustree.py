# B+Tree persistente con claves int/float/string (fija) y valores=row_off int32
import os, struct, bisect
from typing import Optional, Tuple, List

# ---------------------------------------------------------------------
# Codec de claves
# ---------------------------------------------------------------------
class KeyCodec:
    """
    Convierte claves Python <-> bytes de tamaño fijo.
    Soporta:
      - "i"  : int32 little-endian
      - "f"  : float32 little-endian
      - "Ns" : cadena UTF-8 con longitud fija N (relleno con \x00)
    """
    def __init__(self, column_type: str):
        self.kind = column_type
        if column_type == "i":
            self.size = 4
            self.pack_key   = lambda v: struct.pack("<i", int(v))
            self.unpack_key = lambda b: struct.unpack("<i", b)[0]
        elif column_type == "f":
            self.size = 4
            self.pack_key   = lambda v: struct.pack("<f", float(v))
            self.unpack_key = lambda b: struct.unpack("<f", b)[0]
        elif column_type.endswith("s"):
            n = int(column_type[:-1])
            if n <= 0:
                raise ValueError("longitud de string debe ser > 0")
            self.size = n
            def _pack_str(v):
                if isinstance(v, bytes):
                    raw = v[:n].ljust(n, b"\x00")
                else:
                    raw = str(v).encode("utf-8")[:n].ljust(n, b"\x00")
                return raw
            def _unpack_str(b):
                return b.rstrip(b"\x00").decode("utf-8", errors="ignore")
            self.pack_key   = _pack_str
            self.unpack_key = _unpack_str
        else:
            raise ValueError("column_type debe ser 'i', 'f' o 'Ns'.")

# ---------------------------------------------------------------------
# Nodo del B+Tree
# ---------------------------------------------------------------------
class BPlusNode:
    """
    Nodo del B+Tree.
      - node_type: 0=interno, 1=hoja
      - is_root  : 1 si este nodo es la raíz en este momento
      - num_keys : # de claves válidas
      - parent_ptr, next_leaf: metadatos (no imprescindibles para el algoritmo aquí)
      - keys/pointers: en internos => claves + (num_keys+1) hijos; en hojas => (key,row_off)
    """
    ORDER: int = 256
    KEYC: KeyCodec = None

    HEADER_FMT  = "<BBiii"      # node_type, is_root, num_keys, parent_ptr, next_leaf
    HEADER_SIZE = struct.calcsize(HEADER_FMT)
    BODY_SIZE   = None
    NODE_SIZE   = None

    @classmethod
    def init_layout(cls, order: int, keyc: KeyCodec):
        cls.ORDER = order
        cls.KEYC  = keyc
        key_bytes = keyc.size
        internal_bytes = order * key_bytes + (order + 1) * 4
        leaf_bytes     = order * (key_bytes + 4)
        cls.BODY_SIZE = max(internal_bytes, leaf_bytes)
        cls.NODE_SIZE = cls.HEADER_SIZE + cls.BODY_SIZE

    def __init__(self, node_type=1, is_root=0, num_keys=0, parent_ptr=-1, next_leaf=-1):
        self.node_type  = node_type
        self.is_root    = is_root
        self.num_keys   = num_keys
        self.parent_ptr = parent_ptr
        self.next_leaf  = next_leaf
        self.keys: List = []
        self.pointers: List[int] = []

    # ----------------- Serialización del header -----------------
    def _pack_header(self) -> bytes:
        return struct.pack(self.HEADER_FMT, self.node_type, self.is_root,
                           self.num_keys, self.parent_ptr, self.next_leaf)

    @classmethod
    def _unpack_header(cls, buf: bytes) -> "BPlusNode":
        t, r, nk, par, nxt = struct.unpack(cls.HEADER_FMT, buf)
        return cls(t, r, nk, par, nxt)

    # ----------------- Serialización del nodo completo -----------------
    def pack(self) -> bytes:
        keyc = self.KEYC
        hdr  = self._pack_header()
        body = bytearray(self.BODY_SIZE)
        off  = 0

        if self.node_type == 0:  # interno
            for i in range(self.num_keys):
                k_bytes = keyc.pack_key(self.keys[i])
                body[off:off+keyc.size] = k_bytes
                off += keyc.size
            off += (self.ORDER - self.num_keys) * keyc.size
            for i in range(self.num_keys + 1):
                struct.pack_into("<i", body, off, self.pointers[i])
                off += 4
        else:  # hoja
            for i in range(self.num_keys):
                k_bytes = keyc.pack_key(self.keys[i])
                body[off:off+keyc.size] = k_bytes
                off += keyc.size
                struct.pack_into("<i", body, off, self.pointers[i])
                off += 4
        return hdr + bytes(body)

    @classmethod
    def unpack(cls, buf: bytes) -> "BPlusNode":
        keyc = cls.KEYC
        hdr  = buf[:cls.HEADER_SIZE]
        body = buf[cls.HEADER_SIZE:]
        n = cls._unpack_header(hdr)
        n.keys, n.pointers = [], []
        off = 0

        if n.node_type == 0:  # interno
            for _ in range(n.num_keys):
                kb = body[off:off+keyc.size]; off += keyc.size
                n.keys.append(keyc.unpack_key(kb))
            off += (cls.ORDER - n.num_keys) * keyc.size
            for _ in range(n.num_keys + 1):
                p, = struct.unpack_from("<i", body, off); off += 4
                n.pointers.append(p)
        else:  # hoja
            for _ in range(n.num_keys):
                kb = body[off:off+keyc.size]; off += keyc.size
                ro, = struct.unpack_from("<i", body, off); off += 4
                n.keys.append(keyc.unpack_key(kb))
                n.pointers.append(ro)
        return n

# ---------------------------------------------------------------------
# Árbol B+ on-disk
# ---------------------------------------------------------------------
class BPlusTree:
    HEADER_FMT  = "<ii"                        # root_ptr (offset), total_nodes (contiguos)
    HEADER_SIZE = struct.calcsize(HEADER_FMT)

    def __init__(self, table: str, column_type: str, idx_name: Optional[str] = None,
                 order: int = 256):
        base = "/app/src/dbms/data_index"
        os.makedirs(base, exist_ok=True)
        self.path = os.path.join(base, f"{table}_{idx_name or 'bplustree'}.idx")

        self.kc = KeyCodec(column_type)
        BPlusNode.init_layout(order, self.kc)

        if not os.path.exists(self.path):
            with open(self.path, "wb") as f:
                root_off = self.HEADER_SIZE
                total    = 1
                f.write(struct.pack(self.HEADER_FMT, root_off, total))
                root = BPlusNode(node_type=1, is_root=1, num_keys=0, parent_ptr=-1, next_leaf=-1)
                f.write(root.pack())

    # =========================
    # TMP: versiones *_f que usan el MISMO file handle
    # =========================
    def _read_header_f(self, f) -> Tuple[int, int]:
        f.seek(0)
        return struct.unpack(self.HEADER_FMT, f.read(self.HEADER_SIZE))

    def _write_header_f(self, f, root_ptr: Optional[int] = None, total_nodes: Optional[int] = None):
        cur_root, cur_total = self._read_header_f(f)
        if root_ptr    is None: root_ptr    = cur_root
        if total_nodes is None: total_nodes = cur_total
        f.seek(0)
        f.write(struct.pack(self.HEADER_FMT, root_ptr, total_nodes))

    def _node_offset_by_index(self, index: int) -> int:
        return self.HEADER_SIZE + index * BPlusNode.NODE_SIZE

    def _read_node_f(self, f, off: int) -> BPlusNode:
        f.seek(off)
        return BPlusNode.unpack(f.read(BPlusNode.NODE_SIZE))

    def _write_node_f(self, f, node: BPlusNode, off: int):
        f.seek(off)
        f.write(node.pack())

    def _alloc_node_f(self, f, node_type: int) -> int:
        root_off, total = self._read_header_f(f)
        new_off = self._node_offset_by_index(total)
        self._write_node_f(f, BPlusNode(node_type=node_type), new_off)
        self._write_header_f(f, total_nodes=total + 1)
        return new_off

    # ----------------- Helpers -----------------
    @staticmethod
    def _bin_search_internal(node: BPlusNode, key) -> int:
        i = bisect.bisect_right(node.keys, key)
        return min(i, len(node.pointers) - 1)

    @staticmethod
    def _insert_leaf_sorted(node: BPlusNode, key, row_off: int):
        i = bisect.bisect_left(node.keys, key)
        node.keys.insert(i, key)
        node.pointers.insert(i, row_off)
        node.num_keys += 1

    @staticmethod
    def _insert_internal_sorted(node: BPlusNode, key, right_child_off: int):
        i = bisect.bisect_left(node.keys, key)
        node.keys.insert(i, key)
        node.pointers.insert(i + 1, right_child_off)
        node.num_keys += 1

    def _min_keys(self) -> int:
        return BPlusNode.ORDER // 2

    # -----------------------------------------------------------------
    # API
    # -----------------------------------------------------------------
    def _descend_to_leaf_f(self, f, key) -> BPlusNode:
        """TMP: baja hasta la hoja usando el mismo file handle."""
        root_off, _ = self._read_header_f(f)
        node = self._read_node_f(f, root_off)
        while node.node_type == 0:
            idx_child = self._bin_search_internal(node, key)
            node = self._read_node_f(f, node.pointers[idx_child])
        return node

    def search(self, key) -> List[int]:
        """
        Busca y retorna TODOS los row_off con clave == key.
        TMP: abre el archivo una sola vez (rb) y recorre hojas con el mismo handle.
        Lógica del árbol intacta; solo menos I/O.
        """
        res: List[int] = []
        with open(self.path, "rb") as f:  # TMP: una sola apertura
            node = self._descend_to_leaf_f(f, key)

            bisect_left = bisect.bisect_left
            bisect_right = bisect.bisect_right
            cur = node
            while True:
                i = bisect_left(cur.keys, key)
                if i < cur.num_keys and cur.keys and cur.keys[i] == key:
                    j = bisect_right(cur.keys, key, i, cur.num_keys)
                    if j > i:
                        res.extend(cur.pointers[i:j])
                if cur.next_leaf == -1:
                    break
                nxt = self._read_node_f(f, cur.next_leaf)  # TMP: mismo handle
                if nxt.num_keys == 0 or (nxt.keys and nxt.keys[0] > key):
                    break
                cur = nxt
        return res

    def search_range(self, lo, hi) -> List[int]:
        """
        Retorna los row_off con lo <= key <= hi.
        TMP: una sola apertura (rb) y uso del mismo handle en la caminata por next_leaf.
        Lógica y estructura igual; solo I/O consolidada.
        """
        if lo > hi:
            lo, hi = hi, lo

        res: List[int] = []
        with open(self.path, "rb") as f:  # TMP: una sola apertura
            node = self._descend_to_leaf_f(f, lo)

            bisect_left = bisect.bisect_left
            bisect_right = bisect.bisect_right

            cur = node
            i = bisect_left(cur.keys, lo)
            while True:
                nk = cur.num_keys
                if nk == 0:
                    break

                # Fast path si hoja completa dentro del rango
                if cur.keys[0] >= lo and cur.keys[nk - 1] <= hi:
                    res.extend(cur.pointers[i:nk])
                else:
                    j = bisect_right(cur.keys, hi, i, nk)
                    if j > i:
                        res.extend(cur.pointers[i:j])
                    # si hi cae en esta hoja, terminamos
                    if j < nk:
                        break

                if cur.next_leaf == -1:
                    break
                nxt = self._read_node_f(f, cur.next_leaf)  # TMP: mismo handle
                if nxt.num_keys == 0 or nxt.keys[0] > hi:
                    break
                cur = nxt
                i = 0  # siguientes hojas desde el inicio

        return res

    def insert(self, key, row_off: int):
        """
        Inserta (key,row_off). Si hay split, propaga; si la raíz se parte, crea nueva raíz.
        TMP: uso de un único handle r+b durante toda la inserción recursiva.
        """
        with open(self.path, "r+b") as f:
            root_ptr, _ = self._read_header_f(f)
            split = self._insert_recursive_f(f, key, row_off, root_ptr)
            if split is not None:
                pk, new_child = split
                old_root_off = root_ptr

                new_root = BPlusNode(node_type=0, is_root=1, num_keys=1)
                new_root.keys     = [pk]
                new_root.pointers = [old_root_off, new_child]

                old_root = self._read_node_f(f, old_root_off)
                old_root.is_root = 0
                self._write_node_f(f, old_root, old_root_off)

                new_root_off = self._alloc_node_f(f, node_type=0)
                self._write_node_f(f, new_root, new_root_off)
                self._write_header_f(f, root_ptr=new_root_off)

    def _insert_recursive_f(self, f, key, row_off: int, node_off: int):
        node = self._read_node_f(f, node_off)

        if node.node_type == 1:
            self._insert_leaf_sorted(node, key, row_off)
            if node.num_keys <= BPlusNode.ORDER:
                self._write_node_f(f, node, node_off)
                return None
            return self._split_leaf_f(f, node, node_off)

        child_off = node.pointers[self._bin_search_internal(node, key)]
        res = self._insert_recursive_f(f, key, row_off, child_off)
        if res is None:
            return None

        pk, right_off = res
        self._insert_internal_sorted(node, pk, right_off)
        if node.num_keys <= BPlusNode.ORDER:
            self._write_node_f(f, node, node_off)
            return None
        return self._split_internal_f(f, node, node_off)

    # ----------------- Splits (mismo handle) -----------------
    def _split_leaf_f(self, f, node: BPlusNode, node_off: int):
        mid = node.num_keys // 2

        right_off = self._alloc_node_f(f, node_type=1)
        right = BPlusNode(node_type=1, num_keys=node.num_keys - mid,
                          parent_ptr=node.parent_ptr, next_leaf=node.next_leaf)
        right.keys     = node.keys[mid:]
        right.pointers = node.pointers[mid:]

        node.keys     = node.keys[:mid]
        node.pointers = node.pointers[:mid]
        node.num_keys = len(node.keys)
        node.next_leaf = right_off

        self._write_node_f(f, node, node_off)
        self._write_node_f(f, right, right_off)
        return (right.keys[0], right_off)

    def _split_internal_f(self, f, node: BPlusNode, node_off: int):
        mid = node.num_keys // 2
        promoted = node.keys[mid]

        right_off = self._alloc_node_f(f, node_type=0)
        right = BPlusNode(node_type=0, num_keys=len(node.keys) - mid - 1,
                          parent_ptr=node.parent_ptr)
        right.keys     = node.keys[mid + 1:]
        right.pointers = node.pointers[mid + 1:]

        node.keys     = node.keys[:mid]
        node.pointers = node.pointers[:mid + 1]
        node.num_keys = len(node.keys)

        self._write_node_f(f, node, node_off)
        self._write_node_f(f, right, right_off)
        return (promoted, right_off)

    # -----------------------------------------------------------------
    # Borrado + Rebalanceo (mismo handle)
    # -----------------------------------------------------------------
    def delete(self, key) -> List[int]:
        """
        Elimina TODAS las ocurrencias de 'key' y retorna sus row_off.
        TMP: una sola apertura (r+b) durante todo el rebalance.
        """
        with open(self.path, "r+b") as f:
            leaf_off, leaf, stack = self._find_leaf_with_stack_f(f, key)

            i = bisect.bisect_left(leaf.keys, key)
            if i >= leaf.num_keys or (leaf.keys and leaf.keys[i] != key):
                return [-1]
            j = bisect.bisect_right(leaf.keys, key)

            removed = leaf.pointers[i:j]
            del leaf.keys[i:j]
            del leaf.pointers[i:j]
            leaf.num_keys = len(leaf.keys)
            self._write_node_f(f, leaf, leaf_off)

            root_off, _ = self._read_header_f(f)
            if leaf_off == root_off:
                return removed if removed else [-1]

            if leaf.num_keys >= self._min_keys():
                self._fix_parent_separator_after_leftmost_change_f(f, stack, leaf_off, leaf)
                return removed

            self._fix_underflow_leaf_f(f, leaf_off, leaf, stack)
            self._maybe_shrink_root_f(f)
            return removed

    def _find_leaf_with_stack_f(self, f, key):
        root_off, _ = self._read_header_f(f)
        node_off = root_off
        node = self._read_node_f(f, node_off)
        stack = []
        while node.node_type == 0:
            idx = self._bin_search_internal(node, key)
            stack.append((node_off, node, idx))
            node_off = node.pointers[idx]
            node = self._read_node_f(f, node_off)
        return node_off, node, stack

    def _fix_parent_separator_after_leftmost_change_f(self, f, stack, child_off, child_node):
        if not stack or child_node.num_keys == 0:
            return
        parent_off, parent, idx = stack[-1]
        if idx > 0 and parent.keys[idx - 1] != child_node.keys[0]:
            parent.keys[idx - 1] = child_node.keys[0]
            self._write_node_f(f, parent, parent_off)

    def _fix_underflow_leaf_f(self, f, leaf_off, leaf, stack):
        if not stack:
            return
        parent_off, parent, idx = stack[-1]
        mink = self._min_keys()

        left_off  = parent.pointers[idx - 1] if idx > 0 else None
        right_off = parent.pointers[idx + 1] if idx + 1 < len(parent.pointers) else None
        left  = self._read_node_f(f, left_off)  if left_off  is not None else None
        right = self._read_node_f(f, right_off) if right_off is not None else None

        if left and left.num_keys > mink:
            leaf.keys.insert(0, left.keys.pop())
            leaf.pointers.insert(0, left.pointers.pop())
            left.num_keys -= 1
            leaf.num_keys += 1
            parent.keys[idx - 1] = leaf.keys[0]
            self._write_node_f(f, left, left_off)
            self._write_node_f(f, leaf, leaf_off)
            self._write_node_f(f, parent, parent_off)
            return

        if right and right.num_keys > mink:
            leaf.keys.append(right.keys.pop(0))
            leaf.pointers.append(right.pointers.pop(0))
            right.num_keys -= 1
            leaf.num_keys += 1
            parent.keys[idx] = right.keys[0]
            self._write_node_f(f, right, right_off)
            self._write_node_f(f, leaf, leaf_off)
            self._write_node_f(f, parent, parent_off)
            return

        if left:
            left.keys.extend(leaf.keys)
            left.pointers.extend(leaf.pointers)
            left.num_keys = len(left.keys)
            left.next_leaf = leaf.next_leaf
            self._write_node_f(f, left, left_off)
            self._remove_child_from_parent_f(f, stack, idx, merge_left=True)
        elif right:
            leaf.keys.extend(right.keys)
            leaf.pointers.extend(right.pointers)
            leaf.num_keys = len(leaf.keys)
            leaf.next_leaf = right.next_leaf
            self._write_node_f(f, leaf, leaf_off)
            self._remove_child_from_parent_f(f, stack, idx, merge_left=False)

    def _remove_child_from_parent_f(self, f, stack, idx_in_parent, merge_left: bool):
        parent_off, parent, _ = stack[-1]
        if merge_left:
            del parent.keys[idx_in_parent - 1]
            del parent.pointers[idx_in_parent]
        else:
            del parent.keys[idx_in_parent]
            del parent.pointers[idx_in_parent + 1]
        parent.num_keys = len(parent.keys)
        self._write_node_f(f, parent, parent_off)

        root_off, _ = self._read_header_f(f)
        if parent_off == root_off or parent.num_keys >= self._min_keys():
            return
        self._fix_underflow_internal_f(f, stack)

    def _fix_underflow_internal_f(self, f, stack):
        while len(stack) >= 2:
            parent_off, parent, g_idx = stack.pop()
            grand_off, grand, gg_idx = stack[-1]
            mink = self._min_keys()

            left_off  = grand.pointers[gg_idx - 1] if gg_idx > 0 else None
            right_off = grand.pointers[gg_idx + 1] if gg_idx + 1 < len(grand.pointers) else None
            left  = self._read_node_f(f, left_off)  if left_off  is not None else None
            right = self._read_node_f(f, right_off) if right_off is not None else None

            if left and left.num_keys > mink:
                k = left.keys.pop()
                p = left.pointers.pop()
                left.num_keys -= 1
                parent.keys.insert(0, grand.keys[gg_idx - 1])
                parent.pointers.insert(0, p)
                parent.num_keys += 1
                grand.keys[gg_idx - 1] = k
                self._write_node_f(f, left, left_off)
                self._write_node_f(f, parent, parent_off)
                self._write_node_f(f, grand, grand_off)
                return

            if right and right.num_keys > mink:
                k = right.keys.pop(0)
                p = right.pointers.pop(0)
                right.num_keys -= 1
                parent.keys.append(grand.keys[gg_idx])
                parent.pointers.append(p)
                parent.num_keys += 1
                grand.keys[gg_idx] = k
                self._write_node_f(f, right, right_off)
                self._write_node_f(f, parent, parent_off)
                self._write_node_f(f, grand, grand_off)
                return

            if left:
                left.keys.append(grand.keys[gg_idx - 1])
                left.keys.extend(parent.keys)
                left.pointers.extend(parent.pointers)
                left.num_keys = len(left.keys)
                self._write_node_f(f, left, left_off)

                del grand.keys[gg_idx - 1]
                del grand.pointers[gg_idx]
                grand.num_keys = len(grand.keys)
                self._write_node_f(f, grand, grand_off)
            elif right:
                parent.keys.append(grand.keys[gg_idx])
                parent.keys.extend(right.keys)
                parent.pointers.extend(right.pointers)
                parent.num_keys = len(parent.keys)
                self._write_node_f(f, parent, parent_off)

                del grand.keys[gg_idx]
                del grand.pointers[gg_idx + 1]
                grand.num_keys = len(grand.keys)
                self._write_node_f(f, grand, grand_off)
            else:
                return

            root_off, _ = self._read_header_f(f)
            if grand_off == root_off or grand.num_keys >= self._min_keys():
                return

    def _maybe_shrink_root_f(self, f):
        root_off, _ = self._read_header_f(f)
        root = self._read_node_f(f, root_off)
        if root.node_type == 0 and root.num_keys == 0 and len(root.pointers) >= 1:
            new_root_off = root.pointers[0]
            new_root = self._read_node_f(f, new_root_off)
            new_root.is_root = 1
            self._write_node_f(f, new_root, new_root_off)
            self._write_header_f(f, root_ptr=new_root_off)
