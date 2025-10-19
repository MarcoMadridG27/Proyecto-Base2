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

    # Header de bucket: d (prof. local), count, next_ptr, suffix
    BKT_HDR_FMT  = "<iiii"
    BKT_HDR_SIZE = struct.calcsize(BKT_HDR_FMT)

    # Puntero nulo real (¡no uses 0! el primer bucket puede estar en offset 0)
    NULL_PTR = -1

    def __init__(self,
                 table: str,
                 column_type: str,
                 idx_name: Optional[str] = None,
                 D: int = 9,
                 bucket_capacity: int = 100,
                 max_chain: int = 2):
        """
        - column_type: 'i' (int32), 'f' (float32), 'Ns' (cadena fija, ej. '20s')
        - D: profundidad global inicial (>=1)
        - bucket_capacity: entradas por bucket
        - max_chain: longitud máxima de overflow antes de rehash global
        """
        base_dir = "/app/src/dbms/data_index"
        os.makedirs(base_dir, exist_ok=True)
        name = f"{table}_{(idx_name or 'extendible')}"
        self.index_path = os.path.join(base_dir, f"{name}.dir")
        self.data_path  = os.path.join(base_dir, f"{name}.bkt")

        self.bucket_capacity = bucket_capacity
        self.KEY_FMT = column_type
        self.MAX_CHAIN = max_chain

        # Entrada (key, row_off)
        self.ENTRY_FMT  = f"<{self.KEY_FMT}i"
        self.ENTRY_SIZE = struct.calcsize(self.ENTRY_FMT)
        self.BUCKET_SIZE = self.BKT_HDR_SIZE + self.bucket_capacity * self.ENTRY_SIZE

        # Inicializa si no existen
        if (not os.path.exists(self.index_path)) or (not os.path.exists(self.data_path)):
            self._init_files(max(1, D))

    # ===== inicialización =====

    def _init_files(self, D: int):
        """Crea directorio y dos buckets base (d=1) y reparte por último bit."""
        dir_count = 1 << D
        with open(self.index_path, "wb") as fi, open(self.data_path, "wb") as fb:
            fi.write(struct.pack(self.IDX_HDR_FMT, D, dir_count))
            b0 = self._alloc_bucket(fb, local_depth=1, suffix=0)
            b1 = self._alloc_bucket(fb, local_depth=1, suffix=1)
            for idx in range(dir_count):
                bin_idx = bin(idx)[2:].zfill(D)
                ptr = b0 if bin_idx[-1] == "0" else b1
                fi.write(struct.pack(self.DIR_CELL_FMT, ptr))

    def _alloc_bucket(self, fb, local_depth: int, suffix: int) -> int:
        """Reserva un bucket vacío al final y devuelve su offset (¡puede ser 0!)."""
        off = fb.seek(0, os.SEEK_END)   # 0 para el primer bucket
        fb.write(struct.pack(self.BKT_HDR_FMT, local_depth, 0, self.NULL_PTR, suffix))
        fb.write(b"\x00" * (self.bucket_capacity * self.ENTRY_SIZE))
        return off

    # ===== directorio =====

    def _read_index_header(self) -> Tuple[int, int]:
        with open(self.index_path, "rb") as f:
            return struct.unpack(self.IDX_HDR_FMT, f.read(self.IDX_HDR_SIZE))

    def _write_index_header(self, D: int, dir_count: int):
        with open(self.index_path, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(self.IDX_HDR_FMT, D, dir_count))

    def _read_dir_cell(self, idx: int) -> int:
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            return struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0]

    def _write_dir_cell(self, idx: int, bucket_ptr: int):
        with open(self.index_path, "r+b") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            f.write(struct.pack(self.DIR_CELL_FMT, bucket_ptr))

    def _read_all_dir_cells(self) -> List[int]:
        D, dir_count = self._read_index_header()
        cells = []
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE)
            for _ in range(dir_count):
                cells.append(struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0])
        return cells

    def _write_all_dir_cells(self, cells: List[int]):
        D, dir_count = self._read_index_header()
        if len(cells) != dir_count:
            raise ValueError("Tamaño de celdas no coincide con dir_count.")
        with open(self.index_path, "r+b") as f:
            f.seek(self.IDX_HDR_SIZE)
            for ptr in cells:
                f.write(struct.pack(self.DIR_CELL_FMT, ptr))

    def _double_directory(self):
        """Rehash global: D := D+1, duplica celdas (copia punteros)."""
        D, dir_count = self._read_index_header()
        old_cells = self._read_all_dir_cells()
        new_cells = [0] * (dir_count * 2)
        for i, ptr in enumerate(old_cells):
            new_cells[i] = ptr
            new_cells[i + dir_count] = ptr
        self._write_index_header(D + 1, dir_count * 2)
        self._write_all_dir_cells(new_cells)

    def _scan_dir_cells_pointing_to(self, bucket_off: int) -> List[int]:
        """Índices de celdas que apuntan a bucket_off (para split local)."""
        D, dir_count = self._read_index_header()
        idxs = []
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE)
            for i in range(dir_count):
                ptr = struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0]
                if ptr == bucket_off:
                    idxs.append(i)
        return idxs

    def _unique_base_buckets(self) -> List[int]:
        """Conjunto de offsets de buckets base (únicos) a partir del directorio."""
        cells = self._read_all_dir_cells()
        # No hay NULL_PTR en el directorio en este diseño, pero por robustez:
        return sorted(set(ptr for ptr in cells if ptr != self.NULL_PTR))

    # ===== buckets =====

    def _write_bucket_header(self, off: int, d: int, cnt: int, nxt: int, suffix: int):
        with open(self.data_path, "r+b") as f:
            f.seek(off)
            f.write(struct.pack(self.BKT_HDR_FMT, d, cnt, nxt, suffix))

    def _read_bucket(self, off: int):
        """Retorna (d, count, next_ptr, suffix, entries_list)."""
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
        """idx = hash(key) % dir_count (2^D)."""
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

    # ===== utilidades de cadena =====

    def _collect_chain(self, base_off: int) -> List[Tuple[object, int]]:
        """Base + todos los overflow (usa NULL_PTR)."""
        all_entries: List[Tuple[object, int]] = []
        off = base_off
        while off != self.NULL_PTR:
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            all_entries.extend(entries[:cnt])
            off = nxt
        return all_entries

    def _chain_length(self, base_off: int) -> int:
        """# de nodos de overflow (no cuenta base)."""
        length = 0
        off = base_off
        first = True
        while off != self.NULL_PTR:
            if first:
                first = False
            else:
                length += 1
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            off = nxt
        return length

    # ===== split local =====

    def _split_bucket(self, base_off: int, d: int, suffix: int):
        """
        Divide en dos hijos con d' = d+1 y sufijos "0+suffix" y "1+suffix".
        Solo reasigna celdas que apuntaban a base_off.
        """
        D, dir_count = self._read_index_header()
        new_depth = d + 1

        s0 = "0" + bin(suffix)[2:].zfill(d)
        s1 = "1" + bin(suffix)[2:].zfill(d)

        with open(self.data_path, "r+b") as fb:
            new_off_right = self._alloc_bucket(fb, local_depth=new_depth, suffix=int(s1, 2))
        # Reusa base como hijo izquierdo
        self._write_bucket(base_off, new_depth, 0, self.NULL_PTR, int(s0, 2), [])

        idxs = self._scan_dir_cells_pointing_to(base_off)
        for idx in idxs:
            last_bits = bin(idx)[2:].zfill(D)[-new_depth:]
            if last_bits == s0:
                self._write_dir_cell(idx, base_off)
            else:
                self._write_dir_cell(idx, new_off_right)

    # ===== rehash global (todas las cadenas) =====

    def _rehash_all_overflow_chains(self):
        """
        Aumenta D en 1 (duplica directorio) y reinyecta **TODAS** las entradas de
        **todas** las cadenas de overflow de **todos los buckets base**.
        Corta la cadena en cada base (base.next := NULL_PTR) y vacía buckets de overflow.
        No toca las entradas que están en el base (éstas permanecen).
        """
        # 1) Duplicar directorio
        self._double_directory()

        # 2) Recolectar entradas de TODAS las cadenas, base por base
        bases = self._unique_base_buckets()
        to_reinsert: List[Tuple[object, int]] = []

        for base_off in bases:
            d0, c0, nxt0, s0, e0 = self._read_bucket(base_off)
            off = nxt0
            # recorrer overflow
            while off != self.NULL_PTR:
                d, cnt, nxt, suffix, entries = self._read_bucket(off)
                to_reinsert.extend(entries[:cnt])
                # vaciar bucket de overflow
                self._write_bucket(off, d, 0, self.NULL_PTR, suffix, [])
                off = nxt
            # cortar cadena del base (mantener sus entradas intactas)
            if nxt0 != self.NULL_PTR:
                self._write_bucket(base_off, d0, c0, self.NULL_PTR, s0, e0)

        # 3) Reinsertar entradas recolectadas bajo el nuevo D
        for k, ro in to_reinsert:
            self.insert(k, ro)

    # ===== búsqueda =====

    def search(self, key) -> List[int]:
        """Devuelve row_off con clave == key (base + overflow)."""
        D, dir_count = self._read_index_header()
        idx = self._hash_mod(key, dir_count)
        bkt_off = self._read_dir_cell(idx)

        res: List[int] = []
        cur_off = bkt_off
        while cur_off != self.NULL_PTR:
            d, cnt, nxt, suffix, entries = self._read_bucket(cur_off)
            for i in range(cnt):
                k, ro = entries[i]
                if k == key:
                    res.append(ro)
            cur_off = nxt
        return res

    # ===== inserción =====

    def insert(self, key, row_off):
        """
        1) Si el base tiene espacio: insertar.
        2) Si está lleno y d < D: split local, recolectar base+cadena y reinsertar.
        3) Si está lleno y d == D:
           - Si cadena supera MAX_CHAIN: **rehash global de todas las cadenas** y reintentar.
           - Si no: encadenar bucket nuevo si el último está lleno.
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

        # Caso 3: d == D → controlar overflow por longitud de cadena
        chain_len = self._chain_length(bkt_off)
        if chain_len >= self.MAX_CHAIN:
            # *** REHASH GLOBAL ***
            self._rehash_all_overflow_chains()
            # Reintentar ya con D+1
            self.insert(key, row_off)
            return

        # Insertar en el último bucket de la cadena (o crear uno nuevo al final)
        off = bkt_off
        last_off = bkt_off
        last_hdr = (d, cnt, nxt, suffix, entries)
        while off != self.NULL_PTR:
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
            with open(self.data_path, "r+b") as fb:
                new_off = self._alloc_bucket(fb, local_depth=d2, suffix=s2)
            self._write_bucket(last_off, d2, c2, new_off, s2, e2)
            self._write_bucket(new_off, d2, 1, self.NULL_PTR, s2, [(key, row_off)])

    # ===== borrado =====

    def delete(self, key) -> List[int]:
        """
        Elimina todas las ocurrencias de 'key' (base + cadena).
        Compacta por swap con el último válido.
        Si un overflow queda vacío, lo salta.
        Si el BASE queda vacío, redirige celdas del directorio a su siguiente.
        """
        D, dir_count = self._read_index_header()
        idx = self._hash_mod(key, dir_count)

        base_off = self._read_dir_cell(idx)
        removed: List[int] = []

        prev_off = self.NULL_PTR
        prev_hdr = None  # (d, cnt, nxt, suffix)
        cur_off = base_off

        while cur_off != self.NULL_PTR:
            d, cnt, nxt, suffix, entries = self._read_bucket(cur_off)
            changed = False

            if cnt > 0:
                i = 0
                while i < cnt:
                    if entries[i][0] == key:
                        removed.append(entries[i][1])
                        cnt -= 1
                        if i < cnt:
                            entries[i] = entries[cnt]
                        changed = True
                    else:
                        i += 1

            if changed:
                self._write_bucket(cur_off, d, cnt, nxt, suffix, entries)

                if cnt == 0:
                    if prev_off != self.NULL_PTR:
                        # saltar bucket vacío en la cadena
                        pd, pcnt, pnxt, psuffix = prev_hdr
                        self._write_bucket_header(prev_off, pd, pcnt, nxt, psuffix)
                        cur_off = nxt
                        continue
                    else:
                        # base vacío: redirigir celdas del directorio al siguiente
                        for i_dir in self._scan_dir_cells_pointing_to(cur_off):
                            self._write_dir_cell(i_dir, nxt)
                        cur_off = nxt
                        continue

            prev_off = cur_off
            prev_hdr = (d, cnt, nxt, suffix)
            cur_off = nxt

        return removed if removed else [-1]