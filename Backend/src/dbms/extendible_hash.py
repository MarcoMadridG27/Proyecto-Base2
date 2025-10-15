import os
import struct
from typing import List, Tuple, Optional

class ExtendibleHash:
    """
    Índice de Hash Extensible con directorio en disco.

    Archivos:
      - <name>.dir : header(D, dir_count) + dir_count celdas (cell_idx, bucket_ptr)
      - <name>.bkt : buckets encadenables (d, count, next_ptr, suffix, entries...)

    Lógica:
      - D: profundidad global (tamaño del directorio = 2^D celdas)
      - Cada bucket tiene d (profundidad local) y suffix (últimos d bits que atiende)
      - Para ubicar bucket: idx = hash(key) % 2^D, se toma la celda idx del directorio,
        se sigue su puntero y se verifica que los últimos d bits de idx == suffix.
      - Split: si bucket lleno y d < D ⇒ crear dos hijos con d' = d+1 y sufijos:
          s0 = suffix
          s1 = (1 << d) | suffix
        Redistribuir SÓLO las celdas del directorio que apuntaban al bucket base
        según el bit nuevo ( (cell_idx >> d) & 1 ). Reinserción de entradas.
      - Overflow: si d == D ⇒ crear bucket overflow y encadenar.
    """

    # ===== formatos =====
    IDX_HDR_FMT  = "<ii"   # D, dir_count
    IDX_HDR_SIZE = struct.calcsize(IDX_HDR_FMT)
    DIR_CELL_FMT = "<ii"   # cell_idx, bucket_ptr
    DIR_CELL_SIZE = struct.calcsize(DIR_CELL_FMT)

    BKT_HDR_FMT  = "<iiii" # d, count, next_ptr, suffix
    BKT_HDR_SIZE = struct.calcsize(BKT_HDR_FMT)

    def __init__(self, table: str, column_type: str, idx_name: Optional[str] = None,
                 D: int = 3, bucket_capacity: int = 15):
        base_dir = "/app/src/dbms/data_index"
        os.makedirs(base_dir, exist_ok=True)
        name = f"{table}_{(idx_name or 'extendible')}"
        self.index_path = os.path.join(base_dir, f"{name}.dir")
        self.data_path  = os.path.join(base_dir, f"{name}.bkt")

        self.bucket_capacity = bucket_capacity
        self.KEY_FMT = column_type

        self.ENTRY_FMT  = f"<{self.KEY_FMT}i"  # (key, row_off)
        self.ENTRY_SIZE = struct.calcsize(self.ENTRY_FMT)
        self.BUCKET_SIZE = self.BKT_HDR_SIZE + self.bucket_capacity * self.ENTRY_SIZE

        # Inicializar archivos si no existen: D>=1, dos buckets base (d=1, suffix=0/1)
        if (not os.path.exists(self.index_path)) or (not os.path.exists(self.data_path)):
            self._init_files(max(1, D))

    # =================== init helpers ===================

    def _init_files(self, D: int):
        dir_count = pow(2,D)
        with open(self.index_path, "wb") as fi, open(self.data_path, "wb") as fb:
            # header del directorio
            fi.write(struct.pack(self.IDX_HDR_FMT, D, dir_count))
            # crear dos buckets base (vacíos): d=1, suffix=0 y suffix=1
            b0 = self._alloc_bucket(fb, local_depth=1, suffix=0)
            b1 = self._alloc_bucket(fb, local_depth=1, suffix=1)
            # poblar celdas: último bit (LSB) decide
            for idx in range(dir_count):
                id = str(bin(idx))
                if id[-1] == "0":
                    fi.write(struct.pack(self.DIR_CELL_FMT, int(id), b0))
                else:
                    fi.write(struct.pack(self.DIR_CELL_FMT, int(id), b1))

    def _alloc_bucket(self, fb, local_depth: int, suffix: int) -> int:
        """
        Reserva un bucket vacío al final del .bkt y retorna su offset (puntero).
        """
        off = fb.seek(0, os.SEEK_END)
        fb.write(struct.pack(self.BKT_HDR_FMT, local_depth, 0, 0, suffix))
        fb.write(b"\x00" * (self.bucket_capacity * self.ENTRY_SIZE))
        return off

    # =================== directorio ===================

    def _read_index_header(self) -> Tuple[int, int]:
        with open(self.index_path, "rb") as f:
            return struct.unpack(self.IDX_HDR_FMT, f.read(self.IDX_HDR_SIZE))

    def _read_dir_cell(self, idx: int) -> Tuple[int, int]:
        """
        Lee la celda del directorio en posición idx.
        Retorna (cell_idx, bucket_ptr).
        """
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            return struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))

    def _write_dir_cell(self, idx: int, cell_idx: int, bucket_ptr: int):
        with open(self.index_path, "r+b") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            f.write(struct.pack(self.DIR_CELL_FMT, cell_idx, bucket_ptr))

    def _scan_dir_cells_pointing_to(self, bucket_off: int) -> List[int]:
        """
        Retorna todos los índices 'i' del directorio cuyas celdas apuntan a bucket_off.
        (Se usa en split para reasignar sólo esas celdas.)
        """
        D, dir_count = self._read_index_header()
        idxs = []
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE)
            for i in range(dir_count):
                cell_idx, ptr = struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))
                if ptr == bucket_off:
                    idxs.append(i)
        return idxs

    # =================== buckets ===================

    def _read_bucket(self, off: int):
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
            # escribir exactamente bucket_capacity slots
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

    # =================== hash y bits ===================

    def _hash_mod(self, key, dir_count: int) -> int:
        """
        idx = hash(key) % dir_count, con hash estable:

        - str: acumulativo base 257 (primo). Enmascaramos con 0x7fffffff para
               mantener 31 bits positivos:
                 h = (h * 257 + ch) & 0x7fffffff
        - int: (int(key) & 0x7fffffff) % dir_count
        - float: int(abs(key)*1_000_003) & 0x7fffffff  -> % dir_count
        """
        if self.KEY_FMT.endswith("s"):
            s = key if isinstance(key, str) else str(key)
            h = 0
            for ch in s.encode("utf-8"):
                h = (h * 257 + ch) & 0x7fffffff  # multiplica y suma; fija 31 bits
            return h % dir_count
        elif self.KEY_FMT == "i":
            return (int(key) & 0x7fffffff) % dir_count
        else:
            return (int(abs(float(key)) * 1_000_003) & 0x7fffffff) % dir_count

    @staticmethod
    def _last_bits(x: int, d: int) -> int:
        """Devuelve los últimos d bits de x: x & ((1<<d)-1)."""
        if d <= 0:
            return 0
        return x & ((1 << d) - 1)

    # =================== búsqueda ===================

    def search(self, key) -> List[int]:
        """
        Busca offsets con clave == key:
          idx = hash(key) % 2^D
          celda = directorio[idx]  (verifica cell_idx)
          bucket base -> seguir encadenamiento comparando suffix con idx.
        """
        D, dir_count = self._read_index_header()
        idx = int(self._hash_mod(key, dir_count)) #DEBERIA RETORNAR UN BIN DE D bits

        # leer la celda idx
        cell_idx, bkt_off = self._read_dir_cell(idx)

        res = []
        # recorrer bucket base y su cadena
        while bkt_off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(bkt_off)

            for i in range(cnt):
                k, ro = entries[i]
                if k == key:
                    res.append(ro)
            bkt_off = nxt

        return res

    # =================== inserción ===================

    def insert(self, key, row_off):
        """
        Insertar (key, row_off):
          - Si bucket base tiene espacio: insertar y listo.
          - Si lleno y d<D: split -> dos hijos con d+1, sufijos 0sufijo / 1sufijo,
            redistribuir celdas del directorio que apuntaban a base, reinserción.
          - Si lleno y d==D: overflow (encadenar).
        """
        D, dir_count = self._read_index_header()
        idx = int(self._hash_mod(key, dir_count))

        cell_idx, bkt_off = self._read_dir_cell(idx)
        d, cnt, nxt, suffix, entries = self._read_bucket(bkt_off)

        # caso 1: hay espacio en el bucket base
        if cnt < self.bucket_capacity:
            if cnt < len(entries):
                entries[cnt] = (key, row_off)
            else:
                entries.append((key, row_off))
            cnt += 1
            self._write_bucket(bkt_off, d, cnt, nxt, suffix, entries)
            return

        # caso 2: split local si d < D
        if d < D:
            old_entries = self._collect_chain(bkt_off)  # Recoge todas las entradas del bucket base y su cadena.
            self._split_bucket(bkt_off, d, suffix)
            for i in range(len(old_entries)):
                k, ro = old_entries[i]
                self.insert(k, ro)
            self.insert(key, row_off)
            return

        # caso 3: overflow si d == D
        off=bkt_off
        while off != 0:
            bkt_off = off
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            off = nxt
        # si hay espacio en el bucket encadenado
        if cnt < self.bucket_capacity:
            if cnt < len(entries):
                entries[cnt] = (key, row_off)
            else:
                entries.append((key, row_off))
            cnt += 1
            self._write_bucket(bkt_off, d, cnt, nxt, suffix, entries)
            return
        else:
            with open(self.data_path, "r+b") as fb:
                new_off = self._alloc_bucket(fb, local_depth=d, suffix=suffix)
        # encadenar y escribir nueva entrada en el overflow
        self._write_bucket(bkt_off, d, cnt, new_off, suffix, entries)
        self._write_bucket(new_off, d, 1, 0, suffix, [(key, row_off)])
        return

    # =================== split ===================

    def _collect_chain(self, base_off: int) -> List[Tuple[object, int]]:
        """Reúne TODAS las (key, row_off) del bucket base y su cadena."""
        all_entries: List[Tuple[object, int]] = []
        off = base_off
        while off != 0:
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            all_entries.extend(entries[:cnt])
            off = nxt
        return all_entries



