# B+Tree persistente con claves int/float/string (tamaño fijo) y valores=row_off int32
# - Estructura en disco inmutable (no se cambia el layout).
# - Optimizaciones:
#     * Uso de UN SOLO file handle por operación (search, search_range, insert, delete).
#     * search_range “raw-scan”: evita construir objetos/arrays por hoja; hace poda por min/max
#       y bisect DIRECTO sobre el buffer de bytes del nodo hoja.
#     * Copia de offsets en bloque con struct.unpack_from para el tramo útil.
#
# Nota: si vas a variar ORDER, intenta aproximar el tamaño del nodo a una página (≈4 KiB).
#       Con claves de 4B y row_off de 4B, la entrada de hoja mide 8B. Para ≈4 KiB:
#       ORDER ≈ (4096 - HEADER_SIZE) // 8  => con HEADER_FMT "<BBiii" => 14B => ~509.

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
      - "Ns" : cadena UTF-8 de longitud fija N (relleno con \x00)
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
      - is_root  : 1 si este nodo es la raíz
      - num_keys : número de claves válidas
      - parent_ptr, next_leaf: metadatos (next_leaf solo se usa en hojas)
      - Interno => keys[0..num_keys-1], pointers[0..num_keys] (offsets de hijos)
      - Hoja    => pares (key,row_off) con num_keys entradas
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
            # padding de claves no usadas
            off += (self.ORDER - self.num_keys) * keyc.size
            if self.num_keys>0:
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
    # I/O con UN solo handle (*_f)
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

    # ----------------- Helpers de navegación -----------------
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
    # Lectura RAW para rango (sin inflar objetos por hoja)
    # -----------------------------------------------------------------
    def _read_node_raw_f(self, f, off: int) -> bytes:
        """Lee el bloque completo del nodo en un buffer raw."""
        f.seek(off)
        return f.read(BPlusNode.NODE_SIZE)

    def _leaf_bounds_by_bisect_raw(self, raw: bytes, lo, hi) -> Tuple[int, int, int]:
        """
        Devuelve (left, right, nk) para una hoja usando el buffer raw.
        - No construye listas.
        - Realiza dos búsquedas binarias leyendo claves por posición.
        """
        kc = self.kc
        hdr_sz = BPlusNode.HEADER_SIZE
        node_type, is_root, nk, parent_ptr, next_leaf = struct.unpack_from(BPlusNode.HEADER_FMT, raw, 0)
        if node_type != 1 or nk == 0:
            return 0, 0, nk

        entry_sz = kc.size + 4
        base = hdr_sz

        def key_at(i: int):
            p = base + i * entry_sz
            return kc.unpack_key(raw[p:p+kc.size])

        # bsearch izquierda: primera clave >= lo
        L, R = 0, nk
        while L < R:
            m = (L + R) // 2
            if key_at(m) < lo:
                L = m + 1
            else:
                R = m
        left = L

        # bsearch derecha: primera clave > hi
        L, R = 0, nk
        while L < R:
            m = (L + R) // 2
            if key_at(m) <= hi:
                L = m + 1
            else:
                R = m
        right = L
        return left, right, nk

    # -----------------------------------------------------------------
    # API de navegación
    # -----------------------------------------------------------------
    def _descend_to_leaf_f(self, f, key) -> BPlusNode:
        """Baja hasta la hoja usando el mismo file handle."""
        root_off, _ = self._read_header_f(f)
        node = self._read_node_f(f, root_off)
        while node.node_type == 0:
            idx_child = self._bin_search_internal(node, key)
            node = self._read_node_f(f, node.pointers[idx_child])
        return node

    def _find_leaf_with_stack_f(self, f, key):
        """Como _descend_to_leaf_f, pero retorna también offset y stack para rebalanceos/borrado."""
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

    # -----------------------------------------------------------------
    # BÚSQUEDA EXACTA
    # -----------------------------------------------------------------
    def search(self, key) -> List[int]:
        """
        Busca y retorna TODOS los row_off con clave == key.
        - Un solo handle (rb).
        - Pase por hojas via next_leaf solo si la siguiente hoja todavía podría contener la clave.
        """
        res: List[int] = []
        with open(self.path, "rb") as f:
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
                nxt = self._read_node_f(f, cur.next_leaf)
                if nxt.num_keys == 0 or (nxt.keys and nxt.keys[0] > key):
                    break
                cur = nxt
        return res

    # -----------------------------------------------------------------
    # BÚSQUEDA POR RANGO OPTIMIZADA (raw-scan)
    # -----------------------------------------------------------------
    def search_range(self, lo, hi) -> List[int]:
        """
        Retorna los row_off con lo <= key <= hi.
        - Baja a la hoja de 'lo' y recorre next_leaf hasta pasar 'hi'.
        - Poda por hoja usando min/max sin deserializar todo.
        - Tramo útil por hoja via bisect sobre el buffer raw (sin listas).
        - Copia offsets por bloque.
        """
        if lo > hi:
            lo, hi = hi, lo

        res: List[int] = []
        with open(self.path, "rb") as f:
            # Conseguimos el offset de la hoja inicial sin inflar todas luego
            leaf_off, _, _ = self._find_leaf_with_stack_f(f, lo)
            cur_off = leaf_off

            kc = self.kc
            hdr_sz = BPlusNode.HEADER_SIZE
            entry_sz = kc.size + 4

            while cur_off != -1:
                raw = self._read_node_raw_f(f, cur_off)
                node_type, is_root, nk, parent_ptr, next_leaf = struct.unpack_from(BPlusNode.HEADER_FMT, raw, 0)
                if node_type != 1 or nk == 0:
                    break

                base = hdr_sz
                # min y max de la hoja para poda rápida
                first_k = kc.unpack_key(raw[base:base+kc.size])
                last_pos = base + (nk - 1) * entry_sz
                last_k  = kc.unpack_key(raw[last_pos:last_pos+kc.size])

                if last_k < lo:
                    cur_off = next_leaf
                    continue
                if first_k > hi:
                    break

                # tramo útil con bisect sobre raw
                left, right, _ = self._leaf_bounds_by_bisect_raw(raw, lo, hi)
                if right > left:
                    # Bloque contiguo de row_off (int32) justo después de cada key
                    # Offset dentro del raw hasta el primer row_off elegido:
                    p = base + left * entry_sz + kc.size
                    count = right - left
                    # Desempaqueta count enteros contiguos desde p
                    res.extend(struct.unpack_from("<" + "i"*count, raw, p))

                cur_off = next_leaf

        return res

    # -----------------------------------------------------------------
    # INSERCIÓN (misma lógica; un solo handle)
    # -----------------------------------------------------------------
    def insert(self, key, row_off: int):
        """
        Inserta (key,row_off). Si hay split, se promociona y se crean nodos nuevos.
        - Un único handle r+b durante toda la inserción.
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
    # BORRADO + Rebalanceo (un solo handle)
    # -----------------------------------------------------------------
    def delete(self, key) -> List[int]:
        """
        Elimina TODAS las ocurrencias de 'key' y retorna sus row_off.
        - Un solo handle r+b para toda la operación.
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
            parent.keys[idx] = right.keys[0] if right.num_keys > 0 else parent.keys[idx]
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
