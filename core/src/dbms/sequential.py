import os
import struct
import math
from typing import List, Optional, Tuple

# ------------------ Punteros y convenciones ------------------

DELETED = -1  # next_ptr == -1 => tombstone (borrado lógico)

def dptr(i: int) -> int:
    """Puntero a D (1-based)."""
    if i < 1:
        raise ValueError("dptr(i) requiere i>=1")
    return i

def aptr(i: int) -> int:
    """Puntero a A (1-based). a(1)=-2, a(2)=-3, ... Usamos negativos <= -2."""
    if i < 1:
        raise ValueError("aptr(i) requiere i>=1")
    return -(i + 1)

def is_end(p: int) -> bool:
    """Fin de lista lógica."""
    return p == 0

def loc(p: int) -> Tuple[bool, int]:
    """
    Convierte un puntero entero (next_ptr) a (is_aux, idx 1-based).
    Lanza si p es fin o tombstone.
    """
    if p == 0 or p == DELETED:
        raise ValueError("puntero fin o tombstone no tiene ubicación")
    return (False, p) if p > 0 else (True, -p - 1)

# ------------------ Layout binario ------------------
# Entrada: key:int32, offset:uint64, next_ptr:int32
ENTRY_FMT = "<iQi"
ENTRY_SIZE = struct.calcsize(ENTRY_FMT)

# Header: main_count:int32, aux_count:int32, head_ptr:int32
HDR_FMT = "<iii"
HDR_SIZE = struct.calcsize(HDR_FMT)


class SFEntry:
    """Entrada (key, offset, next_ptr)."""
    __slots__ = ("key", "offset", "next_ptr")

    def __init__(self, key: int, offset: int, next_ptr: int = 0):
        if offset < 0:
            raise ValueError("offset debe ser no-negativo")
        self.key = int(key)
        self.offset = int(offset)  # guardamos offsets como uint64
        self.next_ptr = int(next_ptr)

    def pack(self) -> bytes:
        """Empaqueta a bytes según ENTRY_FMT."""
        return struct.pack(ENTRY_FMT, int(self.key), int(self.offset), int(self.next_ptr))

    @staticmethod
    def unpack(buf: bytes) -> "SFEntry":
        """Crea SFEntry desde bytes."""
        k, off, nxt = struct.unpack(ENTRY_FMT, buf)
        return SFEntry(int(k), int(off), int(nxt))

    def deleted(self) -> bool:
        """True si está marcado como tombstone."""
        return self.next_ptr == DELETED


class SequentialFile:
    """
    Índice secuencial D/A persistente:
      - insert/add: siempre escribe en A y encadena en orden por key
      - search: usa binaria en D y luego camina la lista lógica
      - reorganize: compacta D en orden y vacía A según umbral log2
    """

    def __init__(self, table_name: str, column: str, index_dir: str = "data/indexes"):
        os.makedirs(index_dir, exist_ok=True)
        self.path = os.path.join(index_dir, f"{table_name}__{column}.sidx")
        if not os.path.exists(self.path):
            with open(self.path, "wb") as f:
                f.write(struct.pack(HDR_FMT, 0, 0, 0))  # main=0, aux=0, head=0

    # ------------------ Header I/O ------------------

    def _hdr_get(self) -> Tuple[int, int, int]:
        """Lee (main_count, aux_count, head_ptr)."""
        with open(self.path, "rb") as f:
            f.seek(0)
            m, a, h = struct.unpack(HDR_FMT, f.read(HDR_SIZE))
            return int(m), int(a), int(h)

    def _hdr_set(self, m: int, a: int, h: int) -> None:
        """Escribe header asegurando ints."""
        with open(self.path, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(HDR_FMT, int(m), int(a), int(h)))

    # ------------------ Offsets de D/A ------------------

    def _off_d(self, i: int) -> int:
        """Offset byte de d(i) (1-based)."""
        return HDR_SIZE + (i - 1) * ENTRY_SIZE

    def _off_a(self, i: int, base: Optional[int] = None) -> int:
        """Offset byte de a(i) (1-based). base = main_count estable para lecturas."""
        if base is None:
            base, _, _ = self._hdr_get()
        return HDR_SIZE + base * ENTRY_SIZE + (i - 1) * ENTRY_SIZE

    # ------------------ Entrada I/O ------------------

    def _read(self, is_aux: bool, idx: int, base: Optional[int] = None) -> SFEntry:
        """Lee entrada de D/A (1-based)."""
        with open(self.path, "rb") as f:
            f.seek(self._off_a(idx, base) if is_aux else self._off_d(idx))
            return SFEntry.unpack(f.read(ENTRY_SIZE))

    def _write(self, is_aux: bool, idx: int, e: SFEntry, base: Optional[int] = None) -> None:
        """Escribe entrada de D/A (1-based)."""
        with open(self.path, "r+b") as f:
            f.seek(self._off_a(idx, base) if is_aux else self._off_d(idx))
            f.write(e.pack())

    # ------------------ Búsqueda binaria en D ------------------

    def _lb(self, key: int) -> int:
        """
        lower_bound en D: primer i con d(i).key >= key.
        Si no hay, retorna m+1. D debe estar ordenado tras reorganize().
        """
        m, _, _ = self._hdr_get()
        l, r, ans = 1, m, m + 1
        while l <= r:
            mid = (l + r) // 2
            e = self._read(False, mid, m)
            if e.key >= key:
                ans = mid
                r = mid - 1
            else:
                l = mid + 1
        return ans

    # ================== API pública esperada por el manager ==================

    def add(self, key: int, offset: int) -> None:
        """Alias público para insertar una pareja (key, offset)."""
        self._insert(SFEntry(key, offset))

    def search(self, key: int) -> List[int]:
        """
        Devuelve lista de offsets que tienen exactamente 'key'.
        Si no hay, lista vacía. Esto es lo que usa tu SchemaManager.
        """
        m, _, h = self._hdr_get()
        if h == 0:
            return []

        # 1) intento de hit directo en D
        lb = self._lb(key)
        if 1 <= lb <= m:
            e = self._read(False, lb, m)
            if not e.deleted() and e.key == key:
                return [e.offset]

        # 2) arrancar desde sucesor del predecesor vivo en D; si no hay, head
        j = min(lb - 1, m)
        while j >= 1:
            dj = self._read(False, j, m)
            if not dj.deleted():
                start = dj.next_ptr
                break
            j -= 1
        else:
            start = h

        out: List[int] = []
        cur = start
        while not is_end(cur):
            a1, i1 = loc(cur)
            node = self._read(a1, i1, m)
            if node.deleted():
                cur = node.next_ptr
                continue
            if node.key > key:
                break
            if node.key == key:
                out.append(node.offset)
            cur = node.next_ptr
        return out

    # ================== Implementación interna de inserción ==================

    def _insert(self, e: SFEntry) -> None:
        """
        Inserta SIEMPRE en A y encadena en orden por key.
        Reorganiza cuando A supera floor(log2(|D|+1)).
        """
        m, a, h = self._hdr_get()

        # 1) persistir en A
        idx = a + 1
        e.next_ptr = 0
        self._write(True, idx, e, m)
        a += 1
        newp = aptr(idx)

        # 2) lista vacía
        if h == 0:
            self._hdr_set(m, a, newp)
            self._maybe_reorg()
            return

        # 3) predecesor en D (saltando borrados)
        lb = self._lb(e.key)
        j = min(lb - 1, m)
        while j >= 1:
            dj = self._read(False, j, m)
            if not dj.deleted():
                break
            j -= 1

        # 4) decidir prev y cur
        if j >= 1:
            prev_ptr = dptr(j)
            cur_ptr = self._read(False, j, m).next_ptr
        else:
            head_entry = self._read(*loc(h), m)
            if e.key <= head_entry.key:
                # insertar como nuevo head
                e.next_ptr = h
                self._write(True, idx, e, m)
                self._hdr_set(m, a, newp)
                self._maybe_reorg()
                return
            prev_ptr = 0
            cur_ptr = h

        # 5) avanzar por punteros
        while not is_end(cur_ptr):
            a1, i1 = loc(cur_ptr)
            node = self._read(a1, i1, m)
            if node.deleted():
                cur_ptr = node.next_ptr
                continue
            if node.key < e.key:
                prev_ptr = cur_ptr
                cur_ptr = node.next_ptr
            else:
                break

        # 6) enlazar prev -> new -> cur
        e.next_ptr = cur_ptr
        self._write(True, idx, e, m)

        if prev_ptr == 0:
            h = newp
        else:
            pa, pi = loc(prev_ptr)
            prev = self._read(pa, pi, m)
            prev.next_ptr = newp
            self._write(pa, pi, prev, m)

        self._hdr_set(m, a, h)
        self._maybe_reorg()

    # ================== Mantenimiento (reorganización) ==================

    def _maybe_reorg(self) -> None:
        """Umbral simple: cuando A > floor(log2(|D|+1)), ejecuta reorganize()."""
        m, a, _ = self._hdr_get()
        k = int(math.log2(max(1, m + 1)))
        if a > k:
            self.reorganize()

    def reorganize(self) -> None:
        """
        Reconstruye D siguiendo la lista lógica desde head, ignora tombstones,
        y deja A vacía. Head queda en d(1) o 0 si está vacío.
        """
        m, a, h = self._hdr_get()
        if h == 0:
            self._hdr_set(0, 0, 0)
            return

        base = m  # fija la base para leer A correctamente
        ordered: List[SFEntry] = []
        cur = h
        seen = 0
        cap = m + a + 8  # límite de seguridad anti-bucle

        while not is_end(cur) and seen < cap:
            a1, i1 = loc(cur)
            e = self._read(a1, i1, base)
            if not e.deleted():
                ordered.append(e)
            cur = e.next_ptr
            seen += 1

        # Escribir D ordenado y reencadenado d(1)->d(2)->...->END
        newm = len(ordered)
        with open(self.path, "r+b") as f:
            for i, e in enumerate(ordered, start=1):
                e.next_ptr = dptr(i + 1) if i < newm else 0
                f.seek(self._off_d(i))
                f.write(e.pack())

        self._hdr_set(newm, 0, dptr(1) if newm >= 1 else 0)

    # ================== (Opcional) Borrado en el índice ==================

    def remove(self, key: int, offset: Optional[int] = None) -> int:
        """
        Quita entradas del índice para 'key'. Si 'offset' se especifica, solo esa.
        Devuelve cuántas entradas se marcaron como DELETED y se desenlazaron.
        Tu SchemaManager hoy no llama a esto; lo dejo por si lo quieres usar.
        """
        m, a, h = self._hdr_get()
        if h == 0:
            return 0

        lb = self._lb(key)
        j = min(lb - 1, m)
        while j >= 1:
            dj = self._read(False, j, m)
            if not dj.deleted():
                break
            j -= 1

        prev_ptr = dptr(j) if j >= 1 else 0
        cur_ptr = self._read(False, j, m).next_ptr if j >= 1 else h
        removed = 0

        while not is_end(cur_ptr):
            a1, i1 = loc(cur_ptr)
            node = self._read(a1, i1, m)

            if node.key > key:
                break

            if node.key == key and (offset is None or node.offset == offset):
                nxt = node.next_ptr
                # desenlazar
                if prev_ptr == 0:
                    h = nxt
                else:
                    pa, pi = loc(prev_ptr)
                    prev = self._read(pa, pi, m)
                    prev.next_ptr = nxt
                    self._write(pa, pi, prev, m)
                # tombstone
                node.next_ptr = DELETED
                self._write(a1, i1, node, m)
                removed += 1
                cur_ptr = nxt
                if offset is not None:
                    break
                continue

            prev_ptr = cur_ptr
            cur_ptr = node.next_ptr

        self._hdr_set(m, a, h)
        return removed
