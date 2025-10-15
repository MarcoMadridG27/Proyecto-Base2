import os
import struct
from typing import List, Tuple, Optional

class ExtendibleHash:
    """
    Índice de Hash Extensible con directorio en disco.
    """

    # ===== formatos =====
    IDX_HDR_FMT  = "<ii"   # D, dir_count
    IDX_HDR_SIZE = struct.calcsize(IDX_HDR_FMT)
    DIR_CELL_FMT = "<i"    # bucket_ptr
    DIR_CELL_SIZE = struct.calcsize(DIR_CELL_FMT)

    BKT_HDR_FMT  = "<iiii" # d, count, next_ptr, suffix
    BKT_HDR_SIZE = struct.calcsize(BKT_HDR_FMT)

    def __init__(self, table: str, column_type: str, idx_name: Optional[str] = None,
                 D: int = 10, bucket_capacity: int = 100):
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
                # Convertir el índice a binario
                bin_idx = bin(idx)[2:].zfill(D)  # Asegurarse de que tenga D bits
                # Usamos el último bit de la cadena binaria
                if bin_idx[-1] == "0":
                    fi.write(struct.pack(self.DIR_CELL_FMT, b0))
                else:
                    fi.write(struct.pack(self.DIR_CELL_FMT, b1))

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

    def _read_dir_cell(self, idx: int) -> int:
        """
        Lee la celda del directorio en posición idx.
        Retorna bucket_ptr.
        """
        with open(self.index_path, "rb") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            return struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))[0]

    def _write_dir_cell(self, idx: int, bucket_ptr: int):
        with open(self.index_path, "r+b") as f:
            f.seek(self.IDX_HDR_SIZE + idx * self.DIR_CELL_SIZE)
            f.write(struct.pack(self.DIR_CELL_FMT, bucket_ptr))

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
                ptr = struct.unpack(self.DIR_CELL_FMT, f.read(self.DIR_CELL_SIZE))
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

    # =================== búsqueda ===================

    def search(self, key) -> List[int]:
        """
        Busca offsets con clave == key:
          idx = hash(key) % 2^D
          celda = directorio[idx]  (verifica cell_idx)
          bucket base -> seguir encadenamiento comparando suffix con idx.
        """
        D, dir_count = self._read_index_header()
        idx = self._hash_mod(key, dir_count)
        bkt_off = self._read_dir_cell(idx)
        res = []
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
        idx = self._hash_mod(key, dir_count)

        bkt_off = self._read_dir_cell(idx)
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
        off = bkt_off
        last_off = bkt_off
        while off != 0:
            last_off = off
            d, cnt, nxt, suffix, entries = self._read_bucket(off)
            off = nxt
        # si hay espacio en el bucket encadenado
        if cnt < self.bucket_capacity:
            if cnt < len(entries):
                entries[cnt] = (key, row_off)
            else:
                entries.append((key, row_off))
            cnt += 1
            self._write_bucket(last_off, d, cnt, nxt, suffix, entries)
            return
        else:
            with open(self.data_path, "r+b") as fb:
                new_off = self._alloc_bucket(fb, local_depth=d, suffix=suffix)
        # encadenar y escribir nueva entrada en el overflow
        self._write_bucket(last_off, d, cnt, new_off, suffix, entries)
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

    def _split_bucket(self, base_off: int, d: int, suffix: int):
        """
        Divide el *bucket* base en dos (hijos) y los distribuye entre dos nuevos buckets:
        - El hijo izquierdo tendrá el sufijo 0 + sufijo original.
        - El hijo derecho tendrá el sufijo 1 + sufijo original.

        Redistribuye las celdas del directorio que apuntaban al *bucket* base según el sufijo.
        Si un *bucket* se llena, se encadenará con otro nuevo *bucket*.
        """
        D, dir_count = self._read_index_header()

        # Paso 1: Incrementar la profundidad de ambos nuevos buckets (d' = d + 1).
        new_depth = d + 1

        # Paso 2: Agregar un bit al principio del sufijo para los dos nuevos buckets:
        s0 = "0" + bin(suffix)[2:].zfill(d)  # 0 + sufijo
        s1 = "1" + bin(suffix)[2:].zfill(d)  # 1 + sufijo

        # Paso 3: Crear los nuevos buckets (ambos con la misma profundidad y sufijos diferentes).
        with open(self.data_path, "r+b") as fb:
            new_off_1 = self._alloc_bucket(fb, local_depth=new_depth, suffix=int(s1, 2))  # Crea el primer nuevo bucket.
            self._write_bucket(base_off, new_depth, 0, 0, int(s0, 2), [])  # Escribe el primer bucket con sufijo 0.

        # Paso 4: Obtener las celdas del directorio que apuntan al bucket base.
        idxs = self._scan_dir_cells_pointing_to(base_off)

        # Paso 5: Redistribuir las celdas del directorio entre los nuevos buckets, basándonos en los sufijos.
        for idx in idxs:
            if bin(idx)[2:].zfill(D)[-new_depth:] == s0:  # Compara con el último bit del sufijo 0
                self._write_dir_cell(idx, base_off)
            else:
                self._write_dir_cell(idx, new_off_1)
