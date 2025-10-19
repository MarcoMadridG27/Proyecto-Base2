import os
import struct
import math
from typing import Optional, Tuple, List

# ============================================================
# Convención de punteros (1-based)
# ============================================================
DELETED_PTR = -1

def dptr(i: int) -> int:
    """Convierte un índice a puntero de la región principal (D)."""
    if i < 1:
        raise ValueError("d(i) requiere i >= 1")
    return i

def aptr(i: int) -> int:
    """Convierte un índice a puntero de la región auxiliar (A)."""
    if i < 1:
        raise ValueError("a(i) requiere i >= 1")
    return -(i + 1)  # evita colisión con -1

def is_end(p: int) -> bool:
    """¿Es el puntero fin de lista lógica?"""
    return p == 0

def ptr_to_loc(p: int) -> Tuple[bool, int]:
    """
    Convierte puntero a (is_aux, idx) para registros válidos.
    p>0 => d(idx)     ; p<0 y != -1  => a(idx)
    """
    if p == 0 or p == DELETED_PTR:
        raise ValueError("Puntero fin/eliminado no tiene ubicación de registro")
    return (False, p) if p > 0 else (True, -p - 1)

# ============================================================
# Registro: payload + next_ptr
# Formato (definido por la clase, seteado por SequentialFile)
# ============================================================
class EntrySF:
    emp_format: str = ""   # se setea desde SequentialFile
    value_kind: str = ""   # se setea desde SequentialFile

    def __init__(self, offset: int, value, next_ptr: int = 0):
        self.offset = offset
        self.value = value
        self.next_ptr = next_ptr

    def pack(self) -> bytes:
        """Empaqueta el registro según el formato actual."""
        kind = EntrySF.value_kind
        if not EntrySF.emp_format:
            raise RuntimeError("EntrySF.emp_format no inicializado")

        if kind == "i":
            return struct.pack(EntrySF.emp_format, self.offset, int(self.value), self.next_ptr)
        elif kind == "f":
            return struct.pack(EntrySF.emp_format, self.offset, float(self.value), self.next_ptr)
        elif kind.endswith("s"):
            # strings de longitud fija
            n = int(kind[:-1])
            if isinstance(self.value, bytes):
                vb = self.value[:n].ljust(n, b" ")
            else:
                vb = str(self.value).encode("utf-8")[:n].ljust(n, b" ")
            return struct.pack(EntrySF.emp_format, self.offset, vb, self.next_ptr)
        else:
            raise ValueError(f"Tipo de valor no soportado para pack(): {kind}")

    @staticmethod
    def unpack(buf: bytes) -> "EntrySF":
        """Desempaqueta un registro desde bytes."""
        if not EntrySF.emp_format:
            raise RuntimeError("EntrySF.emp_format no inicializado")
        offset, value_raw, next_ptr = struct.unpack(EntrySF.emp_format, buf)

        kind = EntrySF.value_kind
        if kind.endswith("s"):
            # decodificar string fijo
            value = value_raw.decode("utf-8", errors="ignore").rstrip(" ")
        else:
            value = value_raw
        return EntrySF(offset, value, next_ptr)

    def is_deleted(self) -> bool:
        """¿El registro está marcado como deleted (tombstone)?"""
        return self.next_ptr == DELETED_PTR

# ============================================================
# Header: main_count, aux_count, head_ptr
# ============================================================
HEADER_FORMAT = "<iii"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

class SequentialFile:
    """
    Archivo secuencial + zona auxiliar con lista lógica ordenada:
      - Región principal (D) compacta y ordenada
      - Región auxiliar (A) para inserciones
      - Punteros next_ptr para mantener orden lógico
      - Reorganización periódica volcando A→D
    """

    def __init__(self, table: str, column_type: str, idx_name: str | None = None):
        base_dir = "/app/src/dbms/data_index"
        os.makedirs(base_dir, exist_ok=True)

        # nombre del archivo: usa el nombre del índice si viene
        if idx_name:
            self.filename = os.path.join(base_dir, f"{table}_{idx_name}.dat")
        else:
            self.filename = os.path.join(base_dir, f"{table}_index_sequential.dat")

        # guardar kind/tamaños 1 sola vez
        self.value_kind = column_type
        if column_type == "i":
            self.value_size = 4
        elif column_type == "f":
            self.value_size = 4
        elif column_type.endswith("s"):
            self.value_size = int(column_type[:-1])
        else:
            raise ValueError(f"Tipo no soportado: {column_type}")

        self.emp_format = f"<i{column_type}i"
        self.record_size = struct.calcsize(self.emp_format)

        EntrySF.emp_format = self.emp_format
        EntrySF.value_kind = self.value_kind

        if not os.path.exists(self.filename):
            with open(self.filename, "wb") as f:
                f.write(struct.pack(HEADER_FORMAT, 0, 0, 0))

    # ---------------- Header I/O ----------------

    def _get_header(self) -> Tuple[int, int, int]:
        with open(self.filename, "rb") as f:
            f.seek(0)
            return struct.unpack(HEADER_FORMAT, f.read(HEADER_SIZE))

    def _set_header(self, main_count: int, aux_count: int, head_ptr: int):
        with open(self.filename, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(HEADER_FORMAT, main_count, aux_count, head_ptr))

    # ---------------- Offsets ----------------

    def _offs_d(self, i: int) -> int:
        return HEADER_SIZE + (i - 1) * self.record_size

    def _offs_a(self, i: int, base_main: Optional[int] = None) -> int:
        if base_main is None:
            base_main, _, _ = self._get_header()
        return HEADER_SIZE + base_main * self.record_size + (i - 1) * self.record_size

    # ---------------- Registro I/O (con fd opcional para evitar reabrir) ----------------

    def _read_rec(self, is_aux: bool, idx: int, base_main: Optional[int] = None, f=None) -> EntrySF:
        """
        Lee un registro D/A. Si `f` es un archivo abierto, se reutiliza (mejor rendimiento).
        """
        close = False
        if f is None:
            f = open(self.filename, "rb")
            close = True
        try:
            f.seek(self._offs_a(idx, base_main) if is_aux else self._offs_d(idx))
            return EntrySF.unpack(f.read(self.record_size))
        finally:
            if close:
                f.close()

    def _write_rec(self, is_aux: bool, idx: int, rec: EntrySF, base_main: Optional[int] = None, f=None):
        """
        Escribe un registro D/A. Si `f` es un archivo abierto, se reutiliza (mejor rendimiento).
        """
        close = False
        if f is None:
            f = open(self.filename, "r+b")
            close = True
        try:
            f.seek(self._offs_a(idx, base_main) if is_aux else self._offs_d(idx))
            f.write(rec.pack())
        finally:
            if close:
                f.close()

    # ---------------- Búsqueda binaria en D ----------------

    def _lower_bound_d(self, key) -> int:
        """
        Primera posición en D con valor >= key. Si D vacío, retorna 1.
        """
        print(self.filename)
        main_count, _, _ = self._get_header()
        if main_count == 0:
            return 1
        l, r, ans = 1, main_count, main_count + 1
        with open(self.filename, "rb") as f:
            while l <= r:
                m = (l + r) // 2
                rec = self._read_rec(False, m, main_count, f)
                if rec.value >= key:
                    ans = m
                    r = m - 1
                else:
                    l = m + 1
        return ans

    # ---------------- Consultas ----------------

    def search_range(self, lo, hi) -> List[int]:
        """
        Retorna offsets con value en [lo, hi].
        Complejidad: O(log N + K). Usa lower_bound en D y luego camina la lista lógica
        desde el predecesor en D (o head si no existe), para NO perder nodos en AUX.
        """
        if lo > hi:
            lo, hi = hi, lo

        main_count, _, head_ptr = self._get_header()
        res: List[int] = []
        if head_ptr == 0 or main_count == 0:
            return res

        # 1) lower_bound en D
        lb = self._lower_bound_d(lo)

        # 2) predecesor en D: j = lb-1 (saltando d(j) borrados)
        with open(self.filename, "rb") as f:
            j = min(lb - 1, main_count)
            while j >= 1:
                cand = self._read_rec(False, j, main_count, f)
                if not cand.is_deleted():
                    # arrancamos DESPUÉS del predecesor en la lista lógica
                    start_ptr = cand.next_ptr
                    break
                j -= 1
            else:
                # no hay predecesor válido en D; arrancamos desde head
                start_ptr = head_ptr

            # 3) Caminar la lista lógica hasta pasar hi
            cur = start_ptr
            while not is_end(cur):
                is_aux, idx = ptr_to_loc(cur)
                node = self._read_rec(is_aux, idx, main_count, f)

                if node.is_deleted():
                    cur = node.next_ptr
                    continue

                # si nos pasamos del rango, podemos cortar (lista lógica ordenada)
                if node.value > hi:
                    break

                if node.value >= lo:
                    res.append(node.offset)

                cur = node.next_ptr

        return res

    def search(self, key) -> List[int]:
        """
        Retorna offsets de registros con value == key.
        """
        main_count, _, head_ptr = self._get_header()
        if head_ptr == 0:
            return []
        ans: List[int] = []
        with open(self.filename, "rb") as f:
            # Comenzamos desde head; alternativa: saltar cerca con lower_bound
            cur = head_ptr
            while cur != 0:
                is_aux, idx = ptr_to_loc(cur)
                node = self._read_rec(is_aux, idx, main_count, f)
                if node.is_deleted():
                    cur = node.next_ptr
                    continue
                if node.value == key:
                    ans.append(node.offset)
                elif node.value > key:
                    break
                cur = node.next_ptr
        return ans

    # ---------------- Inserciones ----------------

    def insert(self, col_value, off_set):
        """
        Inserta SIEMPRE en AUX y lo encadena ordenadamente:
          - Buscar posición (apoyado en D con lower_bound)
          - Enlazar prev -> new -> cur
          - Reorganizar periódicamente (A → D)
        """
        main_count, aux_count, head_ptr = self._get_header()

        # 0) Guardar en AUX (1-based)
        new_idx = aux_count + 1
        emp = EntrySF(off_set, col_value, next_ptr=0)

        with open(self.filename, "r+b") as f:
            # Escribir en AUX
            self._write_rec(True, new_idx, emp, main_count, f)
            new_ptr = aptr(new_idx)
            aux_count += 1

            # Si lista vacía: new como head y listo
            if head_ptr == 0:
                head_ptr = new_ptr
                # actualizar header y evaluar reorganización
                self._set_header(main_count, aux_count, head_ptr)
                self._maybe_reorganize()
                return

            # 1) Usar lower_bound en D para ubicar vecino izquierdo en D
            lb = self._lower_bound_d(emp.value)
            j = min(lb - 1, main_count)

            # Saltar registros d(j) borrados hacia atrás
            while j >= 1:
                cand = self._read_rec(False, j, main_count, f)
                if not cand.is_deleted():
                    break
                j -= 1

            # 2) Decidir prev_ptr y cur_ptr (caso general cubre insert al inicio)
            if j >= 1:
                prev_ptr = dptr(j)
                cur_ptr = self._read_rec(False, j, main_count, f).next_ptr
            else:
                prev_ptr = 0
                cur_ptr = head_ptr

            # 3) Avanzar mientras cur.value < nuevo.value
            while not is_end(cur_ptr):
                is_aux, idx = ptr_to_loc(cur_ptr)
                node = self._read_rec(is_aux, idx, main_count, f)
                if node.is_deleted():
                    cur_ptr = node.next_ptr
                    continue
                if node.value < emp.value:
                    prev_ptr = cur_ptr
                    cur_ptr = node.next_ptr
                else:
                    break

            # 4) Enlazar prev -> new -> cur
            emp.next_ptr = cur_ptr
            self._write_rec(True, new_idx, emp, main_count, f)

            if prev_ptr == 0:
                head_ptr = new_ptr
            else:
                p_is_aux, p_idx = ptr_to_loc(prev_ptr)
                prev_node = self._read_rec(p_is_aux, p_idx, main_count, f)
                prev_node.next_ptr = new_ptr
                self._write_rec(p_is_aux, p_idx, prev_node, main_count, f)

        # Actualizar header (fuera del with para flush)
        self._set_header(main_count, aux_count, head_ptr)
        self._maybe_reorganize()

    # ---------------- Borrado ----------------

    def delete(self, key) -> List[int]:
        """
        Marca como tombstone el primer registro con value == key.
        Retorna el offset real de ese registro o 0 si no se encontró.
        """
        main_count, aux_count, head_ptr = self._get_header()
        if head_ptr == 0:
            return [-1]
        res: List[int] = []
        with open(self.filename, "r+b") as f:
            cur_ptr = head_ptr
            while not is_end(cur_ptr):
                is_aux, idx = ptr_to_loc(cur_ptr)
                node = self._read_rec(is_aux, idx, main_count, f)
                if node.value > key:
                    break
                if node.value == key and not node.is_deleted():
                    node.next_ptr = DELETED_PTR
                    self._write_rec(is_aux, idx, node, main_count, f)
                    res.append(node.offset)
                cur_ptr = node.next_ptr
        return res

    # ---------------- Política de reorganización ----------------

    def _maybe_reorganize(self):
        """
        Política menos agresiva para grandes volúmenes:
          disparar cuando AUX supere max(64, 4*log2(main+1))
        Ajusta esos parámetros a tu gusto según tu dataset.
        """
        main_count, aux_count, _ = self._get_header()
        k = int(math.log2(max(1, main_count + 1))) * 4
        threshold = max(64, k)
        if aux_count > threshold:
            self.reorganize()

    # ---------------- Reorganización ----------------
    def reorganize(self):
        """
        Vuelca la lista lógica a D compacto en un archivo temporal en una pasada,
        reutilizando _read_rec/_write_rec con file handles abiertos.
        """
        main_count, aux_count, head_ptr = self._get_header()
        if head_ptr == 0:
            self._set_header(0, 0, 0)
            return

        tmp_path = self.filename + ".tmp"

        # Abrimos el original solo para leer, y el temporal para escribir
        with open(self.filename, "rb") as fr, open(tmp_path, "wb+") as fw:
            # Header provisional en el temporal
            fw.write(struct.pack(HEADER_FORMAT, 0, 0, 0))

            base_main = main_count        # base para leer A correctamente del original
            cur = head_ptr
            i = 0
            cap = main_count + aux_count + 16  # margen defensivo

            prev_entry = None   # EntrySF del d(i-1) recién escrito (en el temporal)
            prev_idx   = None   # índice i-1 en D temporal

            while not is_end(cur) and i < cap:
                is_aux, idx = ptr_to_loc(cur)
                node = self._read_rec(is_aux, idx, base_main, fr)  # lee del original

                if not node.is_deleted():
                    i += 1
                    # Creamos el EntrySF que irá a d(i) en el temporal (next_ptr provisional=0)
                    cur_entry = EntrySF(node.offset, node.value, next_ptr=0)

                    # Si ya escribimos d(i-1), enlazarlo -> d(i) y reescribirlo en el temporal
                    if prev_entry is not None and prev_idx is not None:
                        prev_entry.next_ptr = dptr(i)
                        self._write_rec(False, prev_idx, prev_entry, None, fw)

                    # Escribir d(i) en el temporal usando _write_rec
                    self._write_rec(False, i, cur_entry, None, fw)

                    # Actualizar "prev" para el próximo lazo
                    prev_entry = cur_entry
                    prev_idx   = i

                cur = node.next_ptr

            new_main = i
            new_head = dptr(1) if new_main >= 1 else 0

            # Header final en el temporal
            fw.seek(0)
            fw.write(struct.pack(HEADER_FORMAT, new_main, 0, new_head))

        # Reemplazo atómico
        os.replace(tmp_path, self.filename)