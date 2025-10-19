import os
import struct
from typing import List, Tuple, Optional

class ExtendibleHash:
    # Header del directorio: D (profundidad global), dir_count (2^D)
    IDX_HDR_FMT  = "<ii"
    IDX_HDR_SIZE = struct.calcsize(IDX_HDR_FMT)

    # Celda del directorio: bucket_ptr
    DIR_CELL_FMT  = "<i"
    DIR_CELL_SIZE = struct.calcsize(DIR_CELL_FMT)

    # Header de bucket: d (prof. local), count (#entradas), next_ptr (encadenado), suffix (bits que atiende)
    BKT_HDR_FMT  = "<iiii"
    BKT_HDR_SIZE = struct.calcsize(BKT_HDR_FMT)

    def __init__(self,
                 table: str,
                 column_type: str,
                 idx_name: Optional[str] = None,
                 D: int = 9,
                 bucket_capacity: int = 100,
                 max_chain: int = 2):
        """
        Crea/abre archivos del índice.
        - column_type: 'i' (int32), 'f' (float32), 'Ns' (cadena fija, ej. '20s')
        - D: profundidad inicial global (>=1)
        - bucket_capacity: entradas por bucket
        - max_chain: longitud máxima de overflow antes de forzar rehash
        """
        base_dir = "/app/src/dbms/data_index"
        os.makedirs(base_dir, exist_ok=True)
        name = f"{table}_{(idx_name or 'extendible')}"
        self.index_path = os.path.join(base_dir, f"{name}.dir")
        self.data_path  = os.path.join(base_dir, f"{name}.bkt")

        self.bucket_capacity = bucket_capacity
        self.KEY_FMT = column_type
        self.MAX_CHAIN = max_chain

        # Entrada en bucket = (key, row_off)
        self.ENTRY_FMT  = f"<{self.KEY_FMT}i"
        self.ENTRY_SIZE = struct.calcsize(self.ENTRY_FMT)
        self.BUCKET_SIZE = self.BKT_HDR_SIZE + self.bucket_capacity * self.ENTRY_SIZE

        # Si no existen los archivos, inicializa con D>=1 y dos buckets base (d=1, suffix=0/1)
        if (not os.path.exists(self.index_path)) or (not os.path.exists(self.data_path)):
            self._init_files(max(1, D))

    # ===== inicialización =====

    def _init_files(self, D: int):
        """
        Crea el directorio y dos buckets base (d=1) y reparte las celdas por el último bit.
        Mantiene tu lógica de comparar el último bit como string binario.
        """
        dir_count = 1 << D
        with open(self.index_path, "wb") as fi, open(self.data_path, "wb") as fb:
            fi.write(struct.pack(self.IDX_HDR_FMT, D, dir_count))
            b0 = self._alloc_bucket(fb, local_depth=1, suffix=0)
            b1 = self._alloc_bucket(fb, local_depth=1, suffix=1)
            for idx in range(dir_count):
                bin_idx = bin(idx)[2:].zfill(D)
                if bin_idx[-1] == "0":
                    fi.write(struct.pack(self.DIR_CELL_FMT, b0))
                else:
                    fi.write(struct.pack(self.DIR_CELL_FMT, b1))

    def _alloc_bucket(self, fb, local_depth: int, suffix: int) -> int:
        """
        Reserva un bucket vacío al final del archivo .bkt y devuelve su offset.
        """
        off = fb.seek(0, os.SEEK_END)
        fb.write(struct.pack(self.BKT_HDR_FMT, local_depth, 0, 0, suffix))
        fb.write(b"\x00" * (self.bucket_capacity * self.ENTRY_SIZE))
        return off

    # ===== directorio =====

    def _read_index_header(self) -> Tuple[int, int]:
        with open(self.index_path, "rb") as f:
            return struct.unpack(self.IDX_HDR_FMT, f.read(self.IDX_HDR_SIZE))

    def _write_index_header(self, D: int, dir_count: int):
        """
        Actualiza solo el header del directorio.
        """
        with open(self.index_path, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(self.IDX_HDR_FMT, D, dir_count))

    def _read_dir_cell(self, idx: int) -> int:
        """
        Devuelve el puntero de bucket guardado en la celda idx del directorio.
        """
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            return struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0]

    def _write_dir_cell(self, idx: int, bucket_ptr: int):
        """
        Escribe el puntero de bucket en la celda idx del directorio.
        """
        with open(self.index_path, "r+b") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            f.write(struct.pack(self.DIR_CELL_FMT, bucket_ptr))

    def _read_all_dir_cells(self) -> List[int]:
        """
        Lee todas las celdas del directorio en una lista.
        """
        D, dir_count = self._read_index_header()
        cells = []
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE)
            for _ in range(dir_count):
                cells.append(struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0])
        return cells

    def _write_all_dir_cells(self, cells: List[int]):
        """
        Escribe de una vez todas las celdas del directorio desde una lista.
        """
        D, dir_count = self._read_index_header()
        if len(cells) != dir_count:
            raise ValueError("Tamaño de celdas no coincide con dir_count.")
        with open(self.index_path, "r+b") as f:
            f.seek(self.IDX_HDR_SIZE)
            for ptr in cells:
                f.write(struct.pack(self.DIR_CELL_FMT, ptr))

    def _double_directory(self):
        """
        Rehash global del directorio: D := D+1 y duplica celdas (copia punteros).
        """
        D, dir_count = self._read_index_header()
        old_cells = self._read_all_dir_cells()
        new_cells = [0] * (dir_count * 2)
        for i, ptr in enumerate(old_cells):
            new_cells[i] = ptr
            new_cells[i + dir_count] = ptr
        self._write_index_header(D + 1, dir_count * 2)
        self._write_all_dir_cells(new_cells)

    def _scan_dir_cells_pointing_to(self, bucket_off: int) -> List[int]:
        """
        Retorna los índices de celdas que apuntan a bucket_off.
        (Se usa en split local para reasignar solo esas celdas.)
        """
        D, dir_count = self._read_index_header()
        idxs = []
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE)
            for i in range(dir_count):
                ptr = struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0]
                if ptr == bucket_off:
                    idxs.append(i)
        return idxs

    # ===== buckets =====

    def _write_bucket_header(self, off: int, d: int, cnt: int, nxt: int, suffix: int):
        """
        Actualiza solo el header de un bucket en 'off' (no toca entradas).
        """
        with open(self.data_path, "r+b") as f:
            f.seek(off)
            f.write(struct.pack(self.BKT_HDR_FMT, d, cnt, nxt, suffix))

    def _read_bucket(self, off: int):
        """
        Lee header + todas las entradas (incluyendo espacios vacíos).
        Retorna (d, count, next_ptr, suffix, entries_list)
        """
        with open(self.data_path, "rb") as f:
            f.seek(off)
            d, cnt, nxt, suffix = struct.unpack(self.BKT_HDR_FMT, f.read(self.BKT_HDR_SIZE))
            entries = []
            for _ in range(self.bucket_capacity):
                raw = f.read(self.ENTRY_SIZE)
                if not raw:
                    break
                key_raw, row_off = struct.unpack(self.ENTRY_FMT, raw)
                if self.KEY_FMT.endswith("s"):
                    key = key_raw.decode("utf-8", errors="ignore").rstrip(" ")
                else:
                    key = key_raw
                entries.append((key, row_off))
        return d, cnt, nxt, suffix, entries

    def _write_bucket(self, off: int, d: int, cnt: int, nxt: int, suffix: int,
                      entries: List[Tuple[object, int]]):
        """
        Escribe header + entries (rellena con ceros hasta la capacidad del bucket).
        """
        with open(self.data_path, "r+b") as f:
            f.seek(off)
            f.write(struct.pack(self.BKT_HDR_FMT, d, cnt, nxt, suffix))
            for i in range(self.bucket_capacity):
                if i < len(entries):
                    k, ro = entries[i]
                    if self.KEY_FMT.endswith("s"):
                        n = int(self.KEY_FMT[:-1])
                        kb = str(k).encode("utf-8")[:n].ljust(n, b" ")
                        f.write(struct.pack(self.ENTRY_FMT, kb, ro))
                    else:
                        f.write(struct.pack(self.ENTRY_FMT, k, ro))
                else:
                    f.write(b"\x00" * self.ENTRY_SIZE)

    # ===== hash =====

    def _hash_mod(self, key, dir_count: int) -> int:
        """
        idx = hash(key) % dir_count (dir_count = 2^D)
        Mantiene tu comportamiento: enteros, flotantes y cadenas.
        """
        if self.KEY_FMT.endswith("s"):
            s = key if isinstance(key, str) else str(key)
            h = 0
            for ch in s.encode("utf-8"):
                h = (h * 257 + ch) & 0x7fffffff
            return h % dir_count
        elif self.KEY_FMT == "i":
            return (int(key) & 0x7fffffff) % dir_count
        else:
            return (int(abs(float(key)) * 1_000_003) & 0x7fffffff) % dir_count

    # ===== utilidades de cadena (overflow) =====

    def _collect_chain(self, base_off: int) -> List[Tuple[object, int]]:
        """
        Reúne todas las entradas del bucket base y su cadena (para reinsertar en split local).
        """
        all_entries: List[Tuple[object, int]] = []
        off = base_off
        while off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            all_entries.extend(entries[:cnt])
            off = nxt
        return all_entries

    def _chain_length(self, base_off: int) -> int:
        """
        Retorna el número de eslabones de overflow (no cuenta el base).
        """
        length = 0
        off = base_off
        while off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            if nxt != 0:
                length += 1
            off = nxt
        return length

    # ===== split local =====

    def _split_bucket(self, base_off: int, d: int, suffix: int):
        """
        Divide el bucket base en dos hijos con d' = d+1 y sufijos "0+suffix" y "1+suffix".
        Mantiene tu forma de componer y comparar sufijos como strings binarios.
        Solo reasigna celdas del directorio que originalmente apuntaban a base_off.
        """
        D, dir_count = self._read_index_header()
        new_depth = d + 1

        # Construye los nuevos sufijos como cadenas binarias (manteniendo tu diseño)
        s0 = "0" + bin(suffix)[2:].zfill(d)
        s1 = "1" + bin(suffix)[2:].zfill(d)

        # Crea el bucket derecho y reescribe el izquierdo (base) con d' y nuevo suffix
        with open(self.data_path, "r+b") as fb:
            new_off_right = self._alloc_bucket(fb, local_depth=new_depth, suffix=int(s1, 2))
            self._write_bucket(base_off, new_depth, 0, 0, int(s0, 2), [])

        # Solo modificamos las celdas que apuntaban a base_off
        idxs = self._scan_dir_cells_pointing_to(base_off)

        # Comparamos por los últimos new_depth bits del índice en forma de string
        for idx in idxs:
            last_bits = bin(idx)[2:].zfill(D)[-new_depth:]
            if last_bits == s0:
                self._write_dir_cell(idx, base_off)      # hijo izquierdo
            else:
                self._write_dir_cell(idx, new_off_right) # hijo derecho

    # ===== rehash de cadena =====

    def _rehash_overflow_chain(self, base_off: int):
        """
        Aumenta D en 1 y reinyecta solo las entradas de los buckets encadenados,
        cortando la cadena en el base (nxt := 0). No mueve entradas del base.
        """
        # duplicamos el directorio (D := D+1)
        self._double_directory()

        # recolectar entradas de la cadena (no del base)
        d0, c0, nxt0, s0, e0 = self._read_bucket(base_off)
        off = nxt0
        to_reinsert: List[Tuple[object, int]] = []

        while off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            to_reinsert.extend(entries[:cnt])
            # vacía el bucket encadenado (opcional: queda disponible)
            self._write_bucket(off, d, 0, 0, suffix, [])
            off = nxt

        # cortar la cadena del base
        self._write_bucket(base_off, d0, c0, 0, s0, e0)

        # reinsertar esas entradas con el nuevo D
        for k, ro in to_reinsert:
            self.insert(k, ro)

    # ===== búsqueda =====

    def search(self, key) -> List[int]:
        """
        Busca y devuelve todos los row_off cuya clave == key, recorriendo el base y su cadena.
        """
        D, dir_count = self._read_index_header()
        idx = self._hash_mod(key, dir_count)
        bkt_off = self._read_dir_cell(idx)

        res: List[int] = []
        while bkt_off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(bkt_off)
            for i in range(cnt):
                k, ro = entries[i]
                if k == key:
                    res.append(ro)
            bkt_off = nxt
        return res

    # ===== inserción =====

    def insert(self, key, row_off):
        """
        Inserta (key, row_off):
          1) Si el bucket base tiene espacio: insertar.
          2) Si está lleno y d < D: split local, recolectar base+cadena y reinsertar.
          3) Si está lleno y d == D:
             - Si la cadena supera MAX_CHAIN: rehash de la cadena (D := D+1, reinserción solo de overflow), reintentar.
             - Si no supera: agregar al final de la cadena (crear nuevo bucket si el último está lleno).
        """
        D, dir_count = self._read_index_header()
        idx = self._hash_mod(key, dir_count)

        bkt_off = self._read_dir_cell(idx)
        d, cnt, nxt, suffix, entries = self._read_bucket(bkt_off)

        # Caso 1: espacio en el base
        if cnt < self.bucket_capacity:
            if cnt < len(entries):
                entries[cnt] = (key, row_off)
            else:
                entries.append((key, row_off))
            cnt += 1
            self._write_bucket(bkt_off, d, cnt, nxt, suffix, entries)
            return

        # Caso 2: split local si d < D
        if d < D:
            all_entries = self._collect_chain(bkt_off)  # base + cadena (entradas válidas)
            self._split_bucket(bkt_off, d, suffix)
            for k, ro in all_entries:
                self.insert(k, ro)
            self.insert(key, row_off)
            return

        # Caso 3: d == D → overflow controlado por longitud de cadena
        chain_len = self._chain_length(bkt_off)
        if chain_len >= self.MAX_CHAIN:
            # Forzar rehash de la cadena (no del base)
            self._rehash_overflow_chain(bkt_off)
            # Reintentar la inserción ya con D+1
            self.insert(key, row_off)
            return

        # Insertar en el último bucket de la cadena (o crear uno nuevo al final)
        off = bkt_off
        last_off = bkt_off
        last_hdr = (d, cnt, nxt, suffix, entries)
        while off != 0:
            last_off = off
            d2, c2, n2, s2, e2 = self._read_bucket(off)
            last_hdr = (d2, c2, n2, s2, e2)
            off = n2

        d2, c2, n2, s2, e2 = last_hdr
        if c2 < self.bucket_capacity:
            if c2 < len(e2):
                e2[c2] = (key, row_off)
            else:
                e2.append((key, row_off))
            c2 += 1
            self._write_bucket(last_off, d2, c2, n2, s2, e2)
        else:
            # El último está lleno: encadenar uno nuevo y escribir ahí
            with open(self.data_path, "r+b") as fb:
                new_off = self._alloc_bucket(fb, local_depth=d2, suffix=s2)
            self._write_bucket(last_off, d2, c2, new_off, s2, e2)
            self._write_bucket(new_off, d2, 1, 0, s2, [(key, row_off)])

    # ===== borrado =====

    def delete(self, key) -> List[int]:
        """
        Elimina todas las ocurrencias de 'key' en base + cadena.
        Compacta localmente con 'swap con el último válido'.
        Si un bucket NO base queda vacío, lo salta en el encadenamiento (actualiza solo header del previo).
        Si el bucket BASE queda vacío, re-dirige todas las celdas del directorio que lo apuntaban a su 'nxt'.
        Devuelve los row_off eliminados o [-1] si no encontró.
        """
        D, dir_count = self._read_index_header()
        idx = self._hash_mod(key, dir_count)

        base_off = self._read_dir_cell(idx)
        if base_off == 0:
            return [-1]

        removed: List[int] = []

        prev_off = 0
        prev_hdr = None   # (d, cnt, nxt, suffix) del bucket previo
        cur_off = base_off

        while cur_off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(cur_off)
            changed = False

            if cnt > 0:
                i = 0
                while i < cnt:
                    if entries[i][0] == key:
                        removed.append(entries[i][1])
                        cnt -= 1
                        if i < cnt:
                            entries[i] = entries[cnt]  # compactación local
                        changed = True
                    else:
                        i += 1

            if changed:
                self._write_bucket(cur_off, d, cnt, nxt, suffix, entries)

                # Si queda vacío, hay que ajustar encadenamiento
                if cnt == 0:
                    if prev_off != 0:
                        # bucket de overflow vacío: hacer prev.next_ptr = nxt (solo header)
                        pd, pcnt, pnxt, psuffix = prev_hdr
                        self._write_bucket_header(prev_off, pd, pcnt, nxt, psuffix)
                        cur_off = nxt
                        continue
                    else:
                        # base vacío: apuntar celdas del directorio al siguiente
                        for i_dir in self._scan_dir_cells_pointing_to(cur_off):
                            self._write_dir_cell(i_dir, nxt)
                        cur_off = nxt
                        continue

            prev_off = cur_off
            prev_hdr = (d, cnt, nxt, suffix)
            cur_off = nxt

        return removed if removed else [-1]