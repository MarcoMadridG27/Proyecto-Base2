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
            # cadenas de longitud fija (e.g., "16s")
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
                # quitar padding y decodificar
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
    ORDER: int = 256            # nº máximo de claves por nodo
    KEYC: KeyCodec = None       # codec para serializar claves

    HEADER_FMT  = "<BBiii"      # node_type, is_root, num_keys, parent_ptr, next_leaf
    HEADER_SIZE = struct.calcsize(HEADER_FMT)
    BODY_SIZE   = None          # calculado por init_layout
    NODE_SIZE   = None          # HEADER_SIZE + BODY_SIZE

    @classmethod
    def init_layout(cls, order: int, keyc: KeyCodec):
        """
        Configura tamaños de nodo según:
          - ORDER (capacidad máxima de claves)
          - tamaño de la clave (KeyCodec)
        """
        cls.ORDER = order
        cls.KEYC  = keyc
        key_bytes = keyc.size
        # Para asegurar tamaño fijo, se reserva el mayor de ambos cuerpos (interno/hoja):
        internal_bytes = order * key_bytes + (order + 1) * 4   # keys + child pointers
        leaf_bytes     = order * (key_bytes + 4)               # (key,row_off) por entrada
        cls.BODY_SIZE = max(internal_bytes, leaf_bytes)
        cls.NODE_SIZE = cls.HEADER_SIZE + cls.BODY_SIZE

    def __init__(self, node_type=1, is_root=0, num_keys=0, parent_ptr=-1, next_leaf=-1):
        self.node_type  = node_type
        self.is_root    = is_root
        self.num_keys   = num_keys
        self.parent_ptr = parent_ptr
        self.next_leaf  = next_leaf          # válido solo en hojas; enlaza hojas vecinas
        self.keys: List = []                 # en interno: claves; en hoja: claves
        self.pointers: List[int] = []        # en interno: hijos; en hoja: row_off

    # ----------------- Serialización del header -----------------
    def _pack_header(self) -> bytes:
        """Empaqueta el header del nodo a bytes (tamaño fijo)."""
        return struct.pack(self.HEADER_FMT, self.node_type, self.is_root,
                           self.num_keys, self.parent_ptr, self.next_leaf)

    @classmethod
    def _unpack_header(cls, buf: bytes) -> "BPlusNode":
        """Crea un nodo con campos de header a partir de bytes (sin arrays)."""
        t, r, nk, par, nxt = struct.unpack(cls.HEADER_FMT, buf)
        return cls(t, r, nk, par, nxt)

    # ----------------- Serialización del nodo completo -----------------
    def pack(self) -> bytes:
        """
        Empaqueta el nodo completo a un buffer de tamaño fijo:
          HEADER + BODY (keys/pointers reales + padding).
        """
        keyc = self.KEYC
        hdr  = self._pack_header()
        body = bytearray(self.BODY_SIZE)
        off  = 0

        if self.node_type == 0:  # interno
            # escribir claves utilizadas
            for i in range(self.num_keys):
                k_bytes = keyc.pack_key(self.keys[i])
                body[off:off+keyc.size] = k_bytes
                off += keyc.size
            # saltar padding de claves no usadas
            off += (self.ORDER - self.num_keys) * keyc.size
            # escribir punteros a hijos (num_keys + 1)
            if(self.num_keys > 0):
                for i in range(self.num_keys + 1):
                    struct.pack_into("<i", body, off, self.pointers[i])
                    off += 4
            # el resto se deja en cero (ya está)
        else:                    # hoja
            # escribir pares (key,row_off) utilizados
            for i in range(self.num_keys):
                k_bytes = keyc.pack_key(self.keys[i])
                body[off:off+keyc.size] = k_bytes
                off += keyc.size
                struct.pack_into("<i", body, off, self.pointers[i])
                off += 4
            # el resto se deja en cero
        return hdr + bytes(body)

    @classmethod
    def unpack(cls, buf: bytes) -> "BPlusNode":
        """
        Reconstruye un nodo desde bytes:
          - lee header
          - reconstruye keys/pointers según node_type y num_keys
        """
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
            # saltar padding de claves
            off += (cls.ORDER - n.num_keys) * keyc.size
            # leer punteros a hijos
            for _ in range(n.num_keys + 1):
                p, = struct.unpack_from("<i", body, off)
                off += 4
                n.pointers.append(p)
        else:                  # hoja
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
        """
        Crea/abre el archivo de índice:
          - Si no existe: crea header y una hoja vacía como raíz.
          - 'order' controla la capacidad (máx. claves por nodo).
        """
        base = "/app/src/dbms/data_index"
        os.makedirs(base, exist_ok=True)
        self.path = os.path.join(base, f"{table}_{idx_name or 'bplustree'}.idx")

        # Inicializar codec y layout de nodo según el tipo de clave y el orden.
        self.kc = KeyCodec(column_type)
        BPlusNode.init_layout(order, self.kc)

        # Archivo nuevo: header + raíz hoja vacía
        if not os.path.exists(self.path):
            with open(self.path, "wb") as f:
                root_off = self.HEADER_SIZE           # primera página de nodo después del header
                total    = 1                          # ya tendremos 1 nodo (la raíz)
                f.write(struct.pack(self.HEADER_FMT, root_off, total))
                root = BPlusNode(node_type=1, is_root=1, num_keys=0, parent_ptr=-1, next_leaf=-1)
                f.write(root.pack())

    # ----------------- Header I/O -----------------
    def _read_header(self) -> Tuple[int, int]:
        """Lee (root_ptr, total_nodes)."""
        with open(self.path, "rb") as f:
            f.seek(0)
            return struct.unpack(self.HEADER_FMT, f.read(self.HEADER_SIZE))

    def _write_header(self, root_ptr: Optional[int] = None, total_nodes: Optional[int] = None):
        """
        Escribe (root_ptr, total_nodes). Si un campo es None, conserva el valor actual.
        """
        cur_root, cur_total = self._read_header()
        if root_ptr    is None: root_ptr    = cur_root
        if total_nodes is None: total_nodes = cur_total
        with open(self.path, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(self.HEADER_FMT, root_ptr, total_nodes))

    # ----------------- Node I/O -----------------
    def _node_offset_by_index(self, index: int) -> int:
        """Devuelve el offset físico donde se guarda el nodo #index (contiguos)."""
        return self.HEADER_SIZE + index * BPlusNode.NODE_SIZE

    def _read_node(self, off: int) -> BPlusNode:
        """Lee un nodo completo desde 'off'."""
        with open(self.path, "rb") as f:
            f.seek(off)
            return BPlusNode.unpack(f.read(BPlusNode.NODE_SIZE))

    def _write_node(self, node: BPlusNode, off: int):
        """Escribe un nodo completo en 'off'."""
        with open(self.path, "r+b") as f:
            f.seek(off)
            f.write(node.pack())

    def _alloc_node(self, node_type: int) -> int:
        """
        Reserva un nuevo nodo vacío al final del archivo y devuelve su offset.
        NOTA: el nodo se crea sin claves (num_keys=0).
        """
        root_off, total = self._read_header()
        new_off = self._node_offset_by_index(total)  # siguiente posición contigua
        self._write_node(BPlusNode(node_type=node_type), new_off)
        self._write_header(total_nodes=total + 1)
        return new_off

    # ----------------- Helpers -----------------
    @staticmethod
    def _bin_search_internal(node: BPlusNode, key) -> int:
        """
        En un nodo interno, devuelve el índice de hijo por donde bajar (bisect_right),
        es decir, el 1er puntero estrictamente a la derecha de 'key'.
        """
        i = bisect.bisect_right(node.keys, key)
        return min(i, len(node.pointers) - 1)

    @staticmethod
    def _insert_leaf_sorted(node: BPlusNode, key, row_off: int):
        """
        Inserta (key,row_off) en una hoja manteniendo el orden por clave.
        Soporta duplicados (se insertan contiguos usando bisect_left).
        """
        i = bisect.bisect_left(node.keys, key)
        node.keys.insert(i, key)
        node.pointers.insert(i, row_off)
        node.num_keys += 1

    @staticmethod
    def _insert_internal_sorted(node: BPlusNode, key, right_child_off: int):
        """
        Inserta en un nodo interno:
          - 'key' promovida
          - 'right_child_off' a su derecha
        """
        i = bisect.bisect_left(node.keys, key)
        node.keys.insert(i, key)
        node.pointers.insert(i + 1, right_child_off)
        node.num_keys += 1

    def _min_keys(self) -> int:
        """
        Mínimo de claves permitido por nodo (umbral de underflow).
        Usamos ORDER//2, que es estándar.
        """
        return BPlusNode.ORDER // 2

    # -----------------------------------------------------------------
    # API
    # -----------------------------------------------------------------
    def search(self, key) -> List[int]:
        """
        Busca y retorna TODOS los row_off con clave == key.
        Baja por internos y una vez en una hoja:
          - recorre en la hoja y, si necesita, salta a hojas vecinas por next_leaf.
        """
        root_off, _ = self._read_header()
        node = self._read_node(root_off)

        # bajar hasta llegar a una hoja
        while node.node_type == 0:
            idx_child = self._bin_search_internal(node, key)
            node = self._read_node(node.pointers[idx_child])

        # recorrido dentro de la(s) hoja(s)
        res: List[int] = []
        i = bisect.bisect_left(node.keys, key)  # primera posición posible
        cur = node
        while True:
            while i < cur.num_keys and cur.keys[i] == key:
                res.append(cur.pointers[i])
                i += 1
            # si la siguiente hoja empieza con clave > key, ya no hay más
            if cur.next_leaf == -1:
                break
            nxt = self._read_node(cur.next_leaf)
            if nxt.num_keys == 0 or nxt.keys[0] > key:
                break
            cur, i = nxt, 0
        return res

    def search_range(self, lo, hi) -> List[int]:
        """
        Retorna los row_off con lo <= key <= hi.
        Baja hacia la hoja donde caería 'lo' y recorre hojas por next_leaf
        hasta que las claves superen 'hi'.
        """
        if lo > hi:
            lo, hi = hi, lo

        root_off, _ = self._read_header()
        node = self._read_node(root_off)

        # bajar orientado por 'lo'
        while node.node_type == 0:
            idx_child = self._bin_search_internal(node, lo)
            node = self._read_node(node.pointers[idx_child])

        # recorrer hojas agregando en el rango [lo, hi]
        res: List[int] = []
        cur, i = node, bisect.bisect_left(node.keys, lo)
        while True:
            while i < cur.num_keys:
                k = cur.keys[i]
                if k > hi:
                    return res
                res.append(cur.pointers[i])
                i += 1
            if cur.next_leaf == -1:
                break
            cur, i = self._read_node(cur.next_leaf), 0
        return res

    def insert(self, key, row_off: int):
        """
        Inserta (key,row_off). En caso de overflow:
          - divide hoja (split) y promueve la primera clave de la nueva hoja derecha
          - propaga splits hacia arriba si es necesario
          - si la raíz se divide, crea nueva raíz
        """
        root_ptr, _ = self._read_header()
        split = self._insert_recursive(key, row_off, root_ptr)

        # si la raíz devolvió split, crear una nueva raíz interna con 2 hijos
        if split is not None:
            pk, new_child = split
            old_root_off = root_ptr

            new_root = BPlusNode(node_type=0, is_root=1, num_keys=1)
            new_root.keys     = [pk]
            new_root.pointers = [old_root_off, new_child]

            # desmarcar la vieja raíz
            old_root = self._read_node(old_root_off)
            old_root.is_root = 0
            self._write_node(old_root, old_root_off)

            # persistir nueva raíz
            new_root_off = self._alloc_node(node_type=0)
            self._write_node(new_root, new_root_off)
            self._write_header(root_ptr=new_root_off)

    # ----------------- Inserción recursiva -----------------
    def _insert_recursive(self, key, row_off: int, node_off: int):
        """
        Inserta en el subárbol con raíz en 'node_off'.
        Devuelve None si no hubo split; si hubo, retorna (clave_promovida, offset_hijo_derecho).
        """
        node = self._read_node(node_off)

        if node.node_type == 1:
            # insertar en hoja
            self._insert_leaf_sorted(node, key, row_off)
            if node.num_keys <= BPlusNode.ORDER:
                self._write_node(node, node_off)
                return None
            # hoja overflow → dividir hoja
            return self._split_leaf(node, node_off)

        # interno: bajar y luego, si el hijo se partió, insertar clave promovida
        child_off = node.pointers[self._bin_search_internal(node, key)]
        res = self._insert_recursive(key, row_off, child_off)
        if res is None:
            return None

        pk, right_off = res
        self._insert_internal_sorted(node, pk, right_off)
        if node.num_keys <= BPlusNode.ORDER:
            self._write_node(node, node_off)
            return None
        # interno overflow → dividir interno
        return self._split_internal(node, node_off)

    # ----------------- Splits -----------------
    def _split_leaf(self, node: BPlusNode, node_off: int):
        """
        Divide una hoja en dos:
          - left: conserva la primera mitad
          - right: nueva hoja con la segunda mitad
          - la clave promovida es la 1ª clave de la hoja derecha
        """
        mid = node.num_keys // 2

        right_off = self._alloc_node(node_type=1)
        right = BPlusNode(node_type=1, num_keys=node.num_keys - mid,
                          parent_ptr=node.parent_ptr, next_leaf=node.next_leaf)
        right.keys     = node.keys[mid:]
        right.pointers = node.pointers[mid:]

        node.keys     = node.keys[:mid]
        node.pointers = node.pointers[:mid]
        node.num_keys = len(node.keys)
        node.next_leaf = right_off

        self._write_node(node, node_off)
        self._write_node(right, right_off)
        return (right.keys[0], right_off)

    def _split_internal(self, node: BPlusNode, node_off: int):
        """
        Divide un nodo interno:
          - promueve la clave central
          - left: claves/punteros < promovida
          - right: claves/punteros > promovida
        """
        mid = node.num_keys // 2
        promoted = node.keys[mid]

        right_off = self._alloc_node(node_type=0)
        right = BPlusNode(node_type=0, num_keys=len(node.keys) - mid - 1,
                          parent_ptr=node.parent_ptr)
        right.keys     = node.keys[mid + 1:]
        right.pointers = node.pointers[mid + 1:]

        node.keys     = node.keys[:mid]
        node.pointers = node.pointers[:mid + 1]
        node.num_keys = len(node.keys)

        self._write_node(node, node_off)
        self._write_node(right, right_off)
        return (promoted, right_off)

    # -----------------------------------------------------------------
    # Borrado + Rebalanceo
    # -----------------------------------------------------------------
    def _find_leaf_with_stack(self, key):
        """
        Baja hasta la hoja que contendría 'key' guardando la ruta:
        retorna (leaf_off, leaf_node, stack_de_padres) donde
        stack = [(parent_off, parent_node, child_idx), ...]
        """
        root_off, _ = self._read_header()
        node_off = root_off
        node = self._read_node(node_off)
        stack = []
        while node.node_type == 0:
            idx = self._bin_search_internal(node, key)
            stack.append((node_off, node, idx))
            node_off = node.pointers[idx]
            node = self._read_node(node_off)
        return node_off, node, stack

    def delete(self, key) -> List[int]:
        """
        Elimina TODAS las ocurrencias de 'key' y retorna sus row_off.
        Si no existe: [-1].
        Realiza rebalanceo (préstamos o fusiones) y compacta la raíz si queda trivial.
        """
        leaf_off, leaf, stack = self._find_leaf_with_stack(key)

        # rango [i:j] de claves == key dentro de la hoja
        i = bisect.bisect_left(leaf.keys, key)
        if i >= leaf.num_keys or (leaf.keys and leaf.keys[i] != key):
            return [-1]
        j = bisect.bisect_right(leaf.keys, key)

        removed = leaf.pointers[i:j]
        del leaf.keys[i:j]
        del leaf.pointers[i:j]
        leaf.num_keys = len(leaf.keys)
        self._write_node(leaf, leaf_off)

        # si la hoja es la raíz, simplemente terminamos
        root_off, _ = self._read_header()
        if leaf_off == root_off:
            return removed if removed else [-1]

        # si no hay underflow, quizá hay que ajustar un separador del padre
        if leaf.num_keys >= self._min_keys():
            self._fix_parent_separator_after_leftmost_change(stack, leaf_off, leaf)
            return removed

        # underflow: arreglar pidiendo prestado o fusionando
        self._fix_underflow_leaf(leaf_off, leaf, stack)
        self._maybe_shrink_root()   # si la raíz quedó trivial, compactar
        return removed

    # ----------------- Helpers de rebalance -----------------
    def _fix_parent_separator_after_leftmost_change(self, stack, child_off, child_node):
        """
        Si cambió la primera clave del hijo (p.ej., borramos varias y se movió),
        hay que actualizar el separador correspondiente en el padre (si idx>0).
        """
        if not stack or child_node.num_keys == 0:
            return
        parent_off, parent, idx = stack[-1]
        # si el hijo NO es el más a la izquierda, el separador es keys[idx-1]
        if idx > 0 and parent.keys[idx - 1] != child_node.keys[0]:
            parent.keys[idx - 1] = child_node.keys[0]
            self._write_node(parent, parent_off)

    def _fix_underflow_leaf(self, leaf_off, leaf, stack):
        """
        Repara una hoja con menos de min_keys:
          - intenta tomar 1 entrada del vecino izq/der
          - si no se puede, fusiona con un vecino y ajusta el padre
        """
        if not stack:
            return
        parent_off, parent, idx = stack[-1]
        mink = self._min_keys()

        left_off  = parent.pointers[idx - 1] if idx > 0 else None
        right_off = parent.pointers[idx + 1] if idx + 1 < len(parent.pointers) else None
        left  = self._read_node(left_off)  if left_off  is not None else None
        right = self._read_node(right_off) if right_off is not None else None

        # pedir prestado al izquierdo
        if left and left.num_keys > mink:
            leaf.keys.insert(0, left.keys.pop())
            leaf.pointers.insert(0, left.pointers.pop())
            left.num_keys -= 1
            leaf.num_keys += 1
            parent.keys[idx - 1] = leaf.keys[0]
            self._write_node(left, left_off)
            self._write_node(leaf, leaf_off)
            self._write_node(parent, parent_off)
            return

        # pedir prestado al derecho
        if right and right.num_keys > mink:
            leaf.keys.append(right.keys.pop(0))
            leaf.pointers.append(right.pointers.pop(0))
            right.num_keys -= 1
            leaf.num_keys += 1
            parent.keys[idx] = right.keys[0]
            self._write_node(right, right_off)
            self._write_node(leaf, leaf_off)
            self._write_node(parent, parent_off)
            return

        # no se pudo pedir → fusionar
        if left:
            # fusionar: left <- leaf
            left.keys.extend(leaf.keys)
            left.pointers.extend(leaf.pointers)
            left.num_keys = len(left.keys)
            left.next_leaf = leaf.next_leaf
            self._write_node(left, left_off)
            self._remove_child_from_parent(stack, idx, merge_left=True)
        elif right:
            # fusionar: leaf <- right
            leaf.keys.extend(right.keys)
            leaf.pointers.extend(right.pointers)
            leaf.num_keys = len(leaf.keys)
            leaf.next_leaf = right.next_leaf
            self._write_node(leaf, leaf_off)
            self._remove_child_from_parent(stack, idx, merge_left=False)

    def _remove_child_from_parent(self, stack, idx_in_parent, merge_left: bool):
        """
        Elimina del padre el separador y puntero del hijo que desapareció
        después de una fusión, y repara si el padre cae por debajo del mínimo.
        """
        parent_off, parent, _ = stack[-1]
        if merge_left:
            # desapareció el hijo en idx_in_parent → eliminar separador idx-1
            del parent.keys[idx_in_parent - 1]
            del parent.pointers[idx_in_parent]
        else:
            # desapareció el hijo en idx_in_parent+1 → eliminar separador idx
            del parent.keys[idx_in_parent]
            del parent.pointers[idx_in_parent + 1]
        parent.num_keys = len(parent.keys)
        self._write_node(parent, parent_off)

        root_off, _ = self._read_header()
        if parent_off == root_off or parent.num_keys >= self._min_keys():
            return
        # si el padre también cayó por debajo, arreglar en cadena hacia arriba
        self._fix_underflow_internal(stack)

    def _fix_underflow_internal(self, stack):
        """
        Repara underflow en nodos internos:
          - intenta pedir prestado de un hermano
          - si no, fusiona y sigue subiendo si es necesario
        """
        while len(stack) >= 2:
            parent_off, parent, g_idx = stack.pop()       # el nodo con underflow
            grand_off, grand, gg_idx = stack[-1]          # su padre
            mink = self._min_keys()

            left_off  = grand.pointers[gg_idx - 1] if gg_idx > 0 else None
            right_off = grand.pointers[gg_idx + 1] if gg_idx + 1 < len(grand.pointers) else None
            left  = self._read_node(left_off)  if left_off  is not None else None
            right = self._read_node(right_off) if right_off is not None else None

            # pedir al izquierdo
            if left and left.num_keys > mink:
                k = left.keys.pop()
                p = left.pointers.pop()
                left.num_keys -= 1
                parent.keys.insert(0, grand.keys[gg_idx - 1])
                parent.pointers.insert(0, p)
                parent.num_keys += 1
                grand.keys[gg_idx - 1] = k
                self._write_node(left, left_off)
                self._write_node(parent, parent_off)
                self._write_node(grand, grand_off)
                return

            # pedir al derecho
            if right and right.num_keys > mink:
                k = right.keys.pop(0)
                p = right.pointers.pop(0)
                right.num_keys -= 1
                parent.keys.append(grand.keys[gg_idx])
                parent.pointers.append(p)
                parent.num_keys += 1
                grand.keys[gg_idx] = k
                self._write_node(right, right_off)
                self._write_node(parent, parent_off)
                self._write_node(grand, grand_off)
                return

            # fusionar (preferir con el izquierdo si existe)
            if left:
                left.keys.append(grand.keys[gg_idx - 1])      # separador baja
                left.keys.extend(parent.keys)
                left.pointers.extend(parent.pointers)
                left.num_keys = len(left.keys)
                self._write_node(left, left_off)

                del grand.keys[gg_idx - 1]
                del grand.pointers[gg_idx]
                grand.num_keys = len(grand.keys)
                self._write_node(grand, grand_off)
            elif right:
                parent.keys.append(grand.keys[gg_idx])        # separador baja
                parent.keys.extend(right.keys)
                parent.pointers.extend(right.pointers)
                parent.num_keys = len(parent.keys)
                self._write_node(parent, parent_off)

                del grand.keys[gg_idx]
                del grand.pointers[gg_idx + 1]
                grand.num_keys = len(grand.keys)
                self._write_node(grand, grand_off)
            else:
                return  # no hay hermanos, no debería ocurrir

            # si el abuelo cae por debajo, continuar hacia arriba
            root_off, _ = self._read_header()
            if grand_off == root_off or grand.num_keys >= self._min_keys():
                return

    def _maybe_shrink_root(self):
        """
        Si la raíz es un interno vacío (0 claves), contrae el árbol:
          - su único hijo pasa a ser la nueva raíz y se marca is_root=1.
        """
        root_off, _ = self._read_header()
        root = self._read_node(root_off)
        if root.node_type == 0 and root.num_keys == 0 and len(root.pointers) >= 1:
            new_root_off = root.pointers[0]
            new_root = self._read_node(new_root_off)
            # marcar nueva raíz correctamente
            new_root.is_root = 1
            self._write_node(new_root, new_root_off)
            # header apunta a la nueva raíz
            self._write_header(root_ptr=new_root_off)
