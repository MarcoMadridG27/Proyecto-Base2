import os
import struct
import bisect
from typing import List, Tuple, Optional, Iterable

# =========================
# Parámetros principales
# =========================
BLOCK_FACTOR   = 256    # Registros por página de datos / overflow (capacidad fija)
INDEX_FACTOR   = 128    # Separadores por página de índice (L1/L2)
BUILD_PAGES_TR = 500    # Nº de páginas L3 "objetivo" para disparar el primer build (pre-build)

# =========================
# Serialización de claves
# =========================
class KeyCodec:
    """
    Codificador/decodificador de claves a tamaño fijo para escritura en disco.
    Soporta:
      - "i"  -> int32 LE
      - "f"  -> float32 LE
      - "Ns" -> string UTF-8 de longitud fija N (relleno con 0x00)
    """
    def __init__(self, kind: str):
        self.kind = kind
        if kind == "i":
            self.size, self.fmt = 4, "<i"
        elif kind == "f":
            self.size, self.fmt = 4, "<f"
        elif kind.endswith("s") and kind[:-1].isdigit():
            self.size, self.fmt = int(kind[:-1]), None
        else:
            raise ValueError(f"Tipo no soportado: {kind}")

    def pack(self, key) -> bytes:
        """Convierte una clave Python al bloque fijo de bytes correspondiente."""
        if self.kind == "i":
            return struct.pack(self.fmt, int(key))
        if self.kind == "f":
            return struct.pack(self.fmt, float(key))
        b = key if isinstance(key, (bytes, bytearray)) else str(key).encode("utf-8")
        return b[:self.size].ljust(self.size, b"\x00")

    def unpack(self, b: bytes):
        """Convierte bytes persistidos a clave Python del tipo configurado."""
        if self.kind in ("i", "f"):
            return struct.unpack(self.fmt, b)[0]
        # Para string fija, se recorta padding 0x00 y espacios finales.
        return b.decode("utf-8", errors="ignore").rstrip("\x00").rstrip()

    def cmp(self, a, b) -> int:
        """Comparación total compatible con bisect (retorna -1/0/1)."""
        return (a > b) - (a < b)

# =========================
# Página de datos (L3)
# =========================
class _DataPage:
    """
    Página de datos (nivel 3). Contiene pares (key, row_off) ordenados por key
    y un puntero a la primera página de overflow (si la hubiera).
    """
    HDR_FMT = "<ii"  # count, next_overflow
    HDR_SZ  = struct.calcsize(HDR_FMT)

    def __init__(self, kc: KeyCodec, entries=None, next_overflow=-1):
        self.kc = kc
        self.entries = entries or []     # [(key, row_off)] en orden por key
        self.next_overflow = next_overflow

    @property
    def ENTRY_SZ(self): return self.kc.size + 4
    @property
    def PAGE_SZ(self):  return self.HDR_SZ + BLOCK_FACTOR * self.ENTRY_SZ

    def pack(self) -> bytes:
        """Serializa la página completa a tamaño fijo (incluye padding)."""
        buf = bytearray(self.PAGE_SZ)
        struct.pack_into(self.HDR_FMT, buf, 0, len(self.entries), self.next_overflow)
        off = self.HDR_SZ
        for k, ro in self.entries[:BLOCK_FACTOR]:
            kb = self.kc.pack(k)
            buf[off:off+self.kc.size] = kb; off += self.kc.size
            struct.pack_into("<i", buf, off, int(ro)); off += 4
        return bytes(buf)

    @classmethod
    def unpack_from(cls, kc: KeyCodec, raw: bytes) -> "_DataPage":
        """Reconstruye una página desde bytes de disco."""
        cnt, nxt = struct.unpack_from(cls.HDR_FMT, raw, 0)
        entries, off = [], cls.HDR_SZ
        for _ in range(min(cnt, BLOCK_FACTOR)):
            k = kc.unpack(raw[off:off+kc.size]); off += kc.size
            ro, = struct.unpack_from("<i", raw, off); off += 4
            entries.append((k, ro))
        return _DataPage(kc, entries, nxt)

    def is_full(self) -> bool:
        """Indica si ya se alcanzó la capacidad de la página."""
        return len(self.entries) >= BLOCK_FACTOR

    def insert_sorted(self, key, ro):
        """Inserta preservando el orden por clave (O(n))."""
        ks = [x[0] for x in self.entries]
        i = bisect.bisect_left(ks, key)
        self.entries.insert(i, (key, ro))

# =========================
# Página de overflow
# =========================
class _OverflowPage:
    """
    Página de overflow encadenada. Cada página se mantiene ordenada localmente,
    pero el encadenamiento completo NO garantiza orden global estricto.
    """
    HDR_FMT = "<ii"  # count, next_overflow
    HDR_SZ  = struct.calcsize(HDR_FMT)

    def __init__(self, kc: KeyCodec, entries=None, next_overflow=-1):
        self.kc = kc
        self.entries = entries or []     # [(key, row_off)] ordenados localmente
        self.next_overflow = next_overflow

    @property
    def ENTRY_SZ(self): return self.kc.size + 4
    @property
    def PAGE_SZ(self):  return self.HDR_SZ + BLOCK_FACTOR * self.ENTRY_SZ

    def pack(self) -> bytes:
        """Serializa la página completa a tamaño fijo (incluye padding)."""
        buf = bytearray(self.PAGE_SZ)
        struct.pack_into(self.HDR_FMT, buf, 0, len(self.entries), self.next_overflow)
        off = self.HDR_SZ
        for k, ro in self.entries[:BLOCK_FACTOR]:
            kb = self.kc.pack(k)
            buf[off:off+self.kc.size] = kb; off += self.kc.size
            struct.pack_into("<i", buf, off, int(ro)); off += 4
        return bytes(buf)

    @classmethod
    def unpack_from(cls, kc: KeyCodec, raw: bytes) -> "_OverflowPage":
        """Reconstruye una página de overflow desde bytes de disco."""
        cnt, nxt = struct.unpack_from(cls.HDR_FMT, raw, 0)
        entries, off = [], cls.HDR_SZ
        for _ in range(min(cnt, BLOCK_FACTOR)):
            k = kc.unpack(raw[off:off+kc.size]); off += kc.size
            ro, = struct.unpack_from("<i", raw, off); off += 4
            entries.append((k, ro))
        return _OverflowPage(kc, entries, nxt)

    def is_full(self) -> bool:
        """Indica si ya se alcanzó la capacidad de la página."""
        return len(self.entries) >= BLOCK_FACTOR

    def insert_sorted(self, key, ro):
        """Inserta preservando el orden local de la página (O(n))."""
        ks = [x[0] for x in self.entries]
        i = bisect.bisect_left(ks, key)
        self.entries.insert(i, (key, ro))

# =========================
# Página de índice (L1/L2)
# =========================
class _IndexPage:
    """
    Página de índice de factor m:
      - size: nº de separadores utilizados
      - keys[0..m-1]: claves separadoras
      - pages[0..m]: punteros a páginas hijas
    Invariante de búsqueda: se hace floor(key) con bisect_right(keys_usadas).
    """
    def __init__(self, kc: KeyCodec, m: int = INDEX_FACTOR):
        self.kc, self.m, self.size = kc, m, 0
        self.keys  = [None] * m
        self.pages = [0] * (m + 1)

    @property
    def PAGE_SZ(self): return 4 + self.m * self.kc.size + (self.m + 1) * 4

    def pack(self) -> bytes:
        """
        Serializa la página de índice. Para claves no usadas (None) se escribe
        padding de ceros (no se invoca pack de KeyCodec para evitar cast inválido).
        """
        buf = bytearray(self.PAGE_SZ)
        struct.pack_into("<i", buf, 0, self.size)
        off = 4
        for i in range(self.m):
            if self.keys[i] is None:
                kb = b"\x00" * self.kc.size
            else:
                kb = self.kc.pack(self.keys[i])
            buf[off:off+self.kc.size] = kb; off += self.kc.size
        for i in range(self.m + 1):
            struct.pack_into("<i", buf, off, int(self.pages[i])); off += 4
        return bytes(buf)

    @classmethod
    def unpack_from(cls, kc: KeyCodec, raw: bytes, m: int = INDEX_FACTOR) -> "_IndexPage":
        """Reconstruye una página de índice desde bytes de disco."""
        ip = _IndexPage(kc, m)
        if not raw:
            return ip
        ip.size, = struct.unpack_from("<i", raw, 0)
        off, ks = 4, []
        for _ in range(m):
            ks.append(kc.unpack(raw[off:off+kc.size])); off += kc.size
        ip.keys = ks
        ps = []
        for _ in range(m + 1):
            p, = struct.unpack_from("<i", raw, off); off += 4
            ps.append(p)
        ip.pages = ps
        return ip

    def insert_separator(self, key, page_ptr: int) -> bool:
        """
        Inserta un separador 'key' y el puntero 'page_ptr' a su derecha.
        Retorna False si la página ya está llena (no se inserta).
        """
        if self.size >= self.m:
            return False
        i = self.size - 1
        while i >= 0 and self.keys[i] is not None and self.keys[i] > key:
            self.keys[i+1] = self.keys[i]
            self.pages[i+2] = self.pages[i+1]
            i -= 1
        self.keys[i+1] = key
        self.pages[i+2] = page_ptr
        self.size += 1
        return True

    def floor_child(self, key) -> int:
        """
        Aplica floor(key) con bisect_right sobre las 'size' primeras keys.
        Retorna el puntero de página hijo por donde continuar.
        """
        if self.size == 0:
            return self.pages[0]
        used = [self.keys[i] for i in range(self.size)]
        pos = bisect.bisect_right(used, key)
        return self.pages[pos]

# =========================
# ISAM 3 niveles
# =========================
class ISAMIndex:
    """
    ISAM de 3 niveles:
      - L3: páginas de datos ordenadas por clave (capacidad BLOCK_FACTOR).
      - Overflow: encadenamiento de páginas para manejar desbordes por página L3.
      - L2/L1: índices en dos niveles sobre primeras claves de páginas L3.
      - Pre-build: registros "pending" en disco hasta llegar al umbral y construir.
    """
    META_FMT = "<i"  # built flag (0/1)
    META_SZ  = struct.calcsize(META_FMT)

    def __init__(self, table: str, column_type: str, idx_name: Optional[str] = None,
                 block_factor: int = BLOCK_FACTOR, index_factor: int = INDEX_FACTOR,
                 build_pages_trigger: int = BUILD_PAGES_TR):
        """
        Prepara archivos y metadatos. Si no hay build inicial, se usa el archivo
        'pending' (.pnd) para persistir inserts uno a uno sin perder datos.
        """
        base = "/app/src/dbms/data_index"
        os.makedirs(base, exist_ok=True)
        name = f"{table}_{idx_name or 'isam'}"
        self.fp_l1  = os.path.join(base, f"{name}.l1")   # índice raíz (nivel 1)
        self.fp_l2  = os.path.join(base, f"{name}.l2")   # índice intermedio (nivel 2)
        self.fp_l3  = os.path.join(base, f"{name}.l3")   # páginas de datos
        self.fp_ovf = os.path.join(base, f"{name}.ovf")  # páginas de overflow
        self.fp_pnd = os.path.join(base, f"{name}.pnd")  # registros pendientes (pre-build)
        self.fp_meta= os.path.join(base, f"{name}.meta") # bandera de build

        self.kc   = KeyCodec(column_type)
        self.IF   = int(index_factor)
        self.BTR  = int(build_pages_trigger)

        # Asegurar existencia de archivos vacíos
        for fp in [self.fp_l1, self.fp_l2, self.fp_l3, self.fp_ovf, self.fp_pnd, self.fp_meta]:
            if not os.path.exists(fp): open(fp, "wb").close()
        # Meta "built" inicial en 0 si no existe
        if os.path.getsize(self.fp_meta) < self.META_SZ:
            with open(self.fp_meta, "wb") as f: f.write(struct.pack(self.META_FMT, 0))

        # Objetos plantilla para tamaños fijos
        self._tmp_data = _DataPage(self.kc)
        self._tmp_ovf  = _OverflowPage(self.kc)
        self._tmp_idx  = _IndexPage(self.kc, self.IF)

    # ----- meta -----
    def _is_built(self) -> bool:
        """Lee la bandera 'built' (0 no construido / 1 construido)."""
        with open(self.fp_meta, "rb") as f:
            built, = struct.unpack(self.META_FMT, f.read(self.META_SZ))
        return built == 1

    def _set_built(self, v: int):
        """Actualiza la bandera 'built'."""
        with open(self.fp_meta, "r+b") as f:
            f.seek(0); f.write(struct.pack(self.META_FMT, v))

    # ----- offsets / IO helpers -----
    def _l3_off(self, no):  return no * self._tmp_data.PAGE_SZ
    def _ovf_off(self, no): return no * self._tmp_ovf.PAGE_SZ
    def _l2_off(self, no):  return no * self._tmp_idx.PAGE_SZ
    def _fsize(self, path): return os.path.getsize(path)

    def _read_l3(self, no):
        """Lee página L3 #no desde disco."""
        with open(self.fp_l3, "rb") as f:
            f.seek(self._l3_off(no)); raw = f.read(self._tmp_data.PAGE_SZ)
        return _DataPage.unpack_from(self.kc, raw)

    def _write_l3(self, no, pg):
        """Escribe página L3 #no en disco (tamaño fijo)."""
        with open(self.fp_l3, "r+b") as f:
            f.seek(self._l3_off(no)); f.write(pg.pack())

    def _append_l3(self, pg)->int:
        """Agrega una nueva página L3 al final y retorna su número (0-based)."""
        with open(self.fp_l3, "ab") as f: f.write(pg.pack())
        return (self._fsize(self.fp_l3)//self._tmp_data.PAGE_SZ) - 1

    def _read_ovf(self, no):
        """Lee página de overflow #no desde disco."""
        with open(self.fp_ovf, "rb") as f:
            f.seek(self._ovf_off(no)); raw = f.read(self._tmp_ovf.PAGE_SZ)
        return _OverflowPage.unpack_from(self.kc, raw)

    def _write_ovf(self, no, pg):
        """Escribe página de overflow #no en disco."""
        with open(self.fp_ovf, "r+b") as f:
            f.seek(self._ovf_off(no)); f.write(pg.pack())

    def _append_ovf(self, pg)->int:
        """Agrega una nueva página de overflow y retorna su número (0-based)."""
        with open(self.fp_ovf, "ab") as f: f.write(pg.pack())
        return (self._fsize(self.fp_ovf)//self._tmp_ovf.PAGE_SZ) - 1

    def _read_l2(self, no):
        """Lee página de índice L2 #no desde disco."""
        with open(self.fp_l2, "rb") as f:
            f.seek(self._l2_off(no)); raw = f.read(self._tmp_idx.PAGE_SZ)
        return _IndexPage.unpack_from(self.kc, raw, self.IF)

    def _write_l2(self, no, ip):
        """Escribe página de índice L2 #no en disco."""
        with open(self.fp_l2, "r+b") as f:
            f.seek(self._l2_off(no)); f.write(ip.pack())

    def _append_l2(self, ip)->int:
        """Agrega una página L2 y retorna su número (0-based)."""
        with open(self.fp_l2, "ab") as f: f.write(ip.pack())
        return (self._fsize(self.fp_l2)//self._tmp_idx.PAGE_SZ) - 1

    def _read_l1(self):
        """Lee la página L1 (raíz del índice)."""
        with open(self.fp_l1, "rb") as f:
            raw = f.read(self._tmp_idx.PAGE_SZ)
        return _IndexPage.unpack_from(self.kc, raw, self.IF)

    def _write_l1(self, ip):
        """Escribe la raíz L1 completa (única página de L1)."""
        with open(self.fp_l1, "r+b") as f:
            f.seek(0); f.write(ip.pack())

    # ----- pending (pre-build) -----
    def _pnd_esz(self): return self.kc.size + 4

    def _append_pnd(self, key, ro):
        """Anexa un par (key,row_off) a la cola de pendientes (pre-build)."""
        with open(self.fp_pnd, "ab") as f:
            f.write(self.kc.pack(key)); f.write(struct.pack("<i", int(ro)))

    def _iter_pnd(self)->Iterable[Tuple[object,int]]:
        """
        Devuelve una lista (lectura secuencial) de todos los pares pendientes
        persistidos. Se usa tanto para búsqueda pre-build como para el build.
        """
        esz = self._pnd_esz(); sz = self._fsize(self.fp_pnd)
        if sz == 0:
            return []
        out = []
        with open(self.fp_pnd, "rb") as f:
            for _ in range(sz//esz):
                kb = f.read(self.kc.size); ro, = struct.unpack("<i", f.read(4))
                out.append((self.kc.unpack(kb), ro))
        return out

    def _clear_pnd(self):
        """Limpia el archivo de pendientes (tras un build exitoso)."""
        open(self.fp_pnd, "wb").close()

    def _pnd_count(self):
        """Cantidad de entradas pendientes persistidas."""
        return self._fsize(self.fp_pnd)//self._pnd_esz()

    # =========================
    # API: INSERT
    # =========================
    def insert(self, key, row_off: int):
        """
        Inserción uno a uno:
          - Si no hay índice construido: persiste en 'pending' y dispara build
            cuando se alcance el umbral (BUILD_PAGES_TR * BLOCK_FACTOR).
          - Si ya hay índice: inserta en L3; si la página está llena, usa overflow.
        """
        if not self._is_built():
            self._append_pnd(key, row_off)
            if self._pnd_count() >= BUILD_PAGES_TR * BLOCK_FACTOR:
                self._build_from_pending()
            return

        # Caminar L1 → L2 → L3 para localizar la página objetivo
        l1 = self._read_l1()
        l2_no = l1.floor_child(key)
        l2 = self._read_l2(l2_no)
        l3_no = l2.floor_child(key)

        pg = self._read_l3(l3_no)
        if not pg.is_full():
            pg.insert_sorted(key, row_off)
            self._write_l3(l3_no, pg)
            return

        # Overflow: crear cadena o reutilizarla
        if pg.next_overflow == -1:
            new = _OverflowPage(self.kc, [(key, row_off)], -1)
            no  = self._append_ovf(new)
            pg.next_overflow = no
            self._write_l3(l3_no, pg)
            return

        # Buscar una página de overflow con espacio; si no hay, anexar una nueva al final
        cur, prev = pg.next_overflow, -1
        while cur != -1:
            ovf = self._read_ovf(cur)
            if not ovf.is_full():
                ovf.insert_sorted(key, row_off)
                self._write_ovf(cur, ovf)
                return
            prev, cur = cur, ovf.next_overflow

        new = _OverflowPage(self.kc, [(key, row_off)], -1)
        no  = self._append_ovf(new)
        last = self._read_ovf(prev); last.next_overflow = no; self._write_ovf(prev, last)

    # =========================
    # API: SEARCH (exacta)
    # =========================
    def search(self, key) -> List[int]:
        """
        Retorna todos los row_off asociados a 'key'.
        Nota: en overflow NO se asume orden global por toda la cadena, por eso
        no se hace early-break si una página tiene k > key.
        """
        if not self._is_built():
            return [ro for k, ro in self._iter_pnd() if k == key]

        l1 = self._read_l1()
        l2_no = l1.floor_child(key)
        l2 = self._read_l2(l2_no)
        l3_no = l2.floor_child(key)

        res, pg = [], self._read_l3(l3_no)

        # Buscar en la página principal con bisect
        ks = [x[0] for x in pg.entries]
        i = bisect.bisect_left(ks, key)
        while i < len(pg.entries) and pg.entries[i][0] == key:
            res.append(pg.entries[i][1]); i += 1

        # Recorrer TODA la cadena de overflow (sin early-break por orden global)
        nxt = pg.next_overflow
        while nxt != -1:
            ovf = self._read_ovf(nxt)
            for k, ro in ovf.entries:
                if k == key:
                    res.append(ro)
            nxt = ovf.next_overflow
        return res

    # =========================
    # API: SEARCH RANGE
    # =========================
    def search_range(self, lo, hi) -> List[int]:
        """
        Devuelve offsets con clave en [lo, hi].
        Recorrido dirigido por L1/L2 para tocar sólo las páginas L3 candidatas.
        En overflow se revisa toda la cadena por el mismo motivo que en search().
        """
        if self.kc.cmp(lo, hi) > 0:
            lo, hi = hi, lo
        res: List[int] = []

        if not self._is_built():
            for k, ro in self._iter_pnd():
                if self.kc.cmp(lo, k) <= 0 and self.kc.cmp(k, hi) <= 0:
                    res.append(ro)
            return res

        # L1: determinar rango de páginas L2 a visitar
        l1 = self._read_l1()
        start_l2 = l1.floor_child(lo); end_l2 = l1.floor_child(hi)
        all_l2 = [l1.pages[i] for i in range(l1.size + 1)]
        l2_list, seen = [], False
        for p in all_l2:
            if p == start_l2: seen = True
            if seen: l2_list.append(p)
            if p == end_l2: break

        # Por cada L2 elegido, visitar las L3 necesarias
        visited_l3 = set()
        for l2_no in l2_list:
            ip = self._read_l2(l2_no)

            l3_s = ip.floor_child(lo); l3_e = ip.floor_child(hi)
            all_l3 = [ip.pages[i] for i in range(ip.size + 1)]
            l3_list, s3 = [], False
            for p3 in all_l3:
                if p3 == l3_s: s3 = True
                if s3: l3_list.append(p3)
                if p3 == l3_e: break

            for l3_no in l3_list:
                if l3_no in visited_l3:
                    continue
                visited_l3.add(l3_no)
                pg = self._read_l3(l3_no)

                # Principal
                for k, ro in pg.entries:
                    if self.kc.cmp(k, lo) < 0:
                        continue
                    if self.kc.cmp(k, hi) > 0:
                        break
                    res.append(ro)

                # Overflow completo (sin early-break global)
                nxt = pg.next_overflow
                while nxt != -1:
                    ovf = self._read_ovf(nxt)
                    for k, ro in ovf.entries:
                        if self.kc.cmp(k, lo) < 0:
                            continue
                        if self.kc.cmp(k, hi) > 0:
                            continue
                        res.append(ro)
                    nxt = ovf.next_overflow
        return res

    # =========================
    # API: DELETE
    # =========================
    def delete(self, key) -> List[int]:
        """
        Elimina todas las ocurrencias de 'key' y devuelve sus row_off (o [-1]).
        En overflow, si una página queda vacía, se desenlaza de la cadena.
        """
        removed: List[int] = []

        # Pre-build: filtrar en pending y persistir los restantes
        if not self._is_built():
            pairs = list(self._iter_pnd())
            kept = []
            for k, ro in pairs:
                if k == key:
                    removed.append(ro)
                else:
                    kept.append((k, ro))
            open(self.fp_pnd, "wb").close()
            with open(self.fp_pnd, "ab") as f:
                for k, ro in kept:
                    f.write(self.kc.pack(k)); f.write(struct.pack("<i", int(ro)))
            return removed if removed else [-1]

        # Post-build: localizar página principal
        l1 = self._read_l1()
        l2_no = l1.floor_child(key)
        l2 = self._read_l2(l2_no)
        l3_no = l2.floor_child(key)

        # Principal: conservar los que no coinciden
        pg = self._read_l3(l3_no)
        kept = []
        for k, ro in pg.entries:
            if k == key:
                removed.append(ro)
            else:
                kept.append((k, ro))
        pg.entries = kept
        self._write_l3(l3_no, pg)

        # Overflow: recorrer, eliminar y reencadenar páginas vacías
        prev, cur = -1, pg.next_overflow
        while cur != -1:
            ovf = self._read_ovf(cur)
            kept, changed = [], False
            for k, ro in ovf.entries:
                if k == key:
                    removed.append(ro)
                    changed = True
                else:
                    kept.append((k, ro))

            if not kept:
                # Desenlazar esta página vacía
                nxt = ovf.next_overflow
                if prev == -1:
                    pg = self._read_l3(l3_no)
                    pg.next_overflow = nxt
                    self._write_l3(l3_no, pg)
                else:
                    p = self._read_ovf(prev)
                    p.next_overflow = nxt
                    self._write_ovf(prev, p)
                cur = nxt
            else:
                ovf.entries = kept
                self._write_ovf(cur, ovf)
                prev, cur = cur, ovf.next_overflow

        return removed if removed else [-1]

    # =========================
    # Build inicial (privado)
    # =========================
    def _build_from_pending(self):
        """
        Construye el ISAM a partir de todos los registros pendientes:
          1) Ordena por key.
          2) Empaqueta L3 (páginas llenas por BLOCK_FACTOR).
          3) Genera L2 con separadores (primera clave de cada L3).
          4) Genera L1 apuntando a páginas L2.
        Al final, limpia pending y marca 'built = 1'.
        """
        pairs = list(self._iter_pnd())
        if not pairs:
            self._set_built(1)
            return

        pairs.sort(key=lambda x: x[0])

        # Limpiar estructuras previas (si existían)
        for fp in [self.fp_l1, self.fp_l2, self.fp_l3, self.fp_ovf]:
            open(fp, "wb").close()

        # L3: empaquetar pares en páginas completas
        l3_first = []  # primeras claves de cada página L3
        for i in range(0, len(pairs), BLOCK_FACTOR):
            chunk = pairs[i:i+BLOCK_FACTOR]
            pg = _DataPage(self.kc, chunk, -1)
            if chunk:
                l3_first.append(chunk[0][0])
            self._append_l3(pg)

        # L2: agrupar páginas L3 por INDEX_FACTOR y producir separadores
        l2_pages = []  # números de página L2 creadas
        for j in range(0, len(l3_first), self.IF):
            ip = _IndexPage(self.kc, self.IF)
            ip.pages[0] = j
            end = min(j + self.IF, len(l3_first))
            for k in range(j + 1, end):
                ip.insert_separator(l3_first[k], k)
            l2_pages.append(self._append_l2(ip))

        # L1: raíz del índice debe APUNTAR a páginas L2 (no copiar una L2)
        if not l2_pages:
            # No hay L2 (caso extremo solo si no hubo L3), mantener raíz vacía apuntando a 0
            l1 = _IndexPage(self.kc, self.IF)
            l1.pages[0] = 0
        elif len(l2_pages) == 1:
            # Raíz con un solo hijo: pages[0] apunta a esa única página L2
            l1 = _IndexPage(self.kc, self.IF)
            l1.pages[0] = l2_pages[0]
        else:
            # Raíz con varios hijos L2: usar la 1ª clave válida de cada L2 como separador
            l1 = _IndexPage(self.kc, self.IF)
            l1.pages[0] = l2_pages[0]
            for i in range(1, len(l2_pages)):
                ip = self._read_l2(l2_pages[i])
                # Tomar el primer separador válido de la L2; si no hay, tomar la 1ª clave de su 1ª L3
                sep = ip.keys[0] if (ip.size > 0 and ip.keys[0] not in (None, "", 0)) else None
                if sep is None:
                    first_l3_no = ip.pages[0]
                    first_l3 = self._read_l3(first_l3_no)
                    if first_l3.entries:
                        sep = first_l3.entries[0][0]
                if sep is not None:
                    l1.insert_separator(sep, l2_pages[i])

        self._write_l1(l1)
        self._set_built(1)
        self._clear_pnd()