# storage/sequential.py
import os
import math
import struct
from core.record import RecordSchema


class SequentialFile:
    def __init__(self, file_name: str, schema: RecordSchema, aux_file="aux.dat", aux_limit=3):
        self.file_name = file_name
        self.aux_file = aux_file
        self.aux_limit = aux_limit
        self.schema = schema

        # Crear archivos si no existen
        for f in [self.file_name, self.aux_file]:
            if not os.path.exists(f):
                open(f, "wb").close()

    def get_size(self, file_name):
        with open(file_name, "rb") as f:
            f.seek(0, 2)
            return f.tell() // self.schema.size

    def read_record(self, file_name, pos: int):
        with open(file_name, "rb") as f:
            f.seek(pos * self.schema.size)
            data = f.read(self.schema.size)
            if not data:
                return None
            return self.schema.unpack(data)

    def write_record(self, file_name, pos: int, record: dict):
        with open(file_name, "r+b") as f:
            f.seek(pos * self.schema.size)
            f.write(self.schema.pack(record))

    def insert_aux(self, record: dict):
        size_aux = self.get_size(self.aux_file)
        if size_aux >= self.aux_limit:
            self.reconstruct()
        with open(self.aux_file, "ab") as aux:
            aux.write(self.schema.pack(record))

    def _insert_ordered(self, record: dict, key_name="id"):
        size = self.get_size(self.file_name)
        left, right = 0, size - 1
        pos = size

        with open(self.file_name, "rb") as f:
            while left <= right:
                mid = (left + right) // 2
                f.seek(mid * self.schema.size)
                data = f.read(self.schema.size)
                if not data:
                    break
                rec = self.schema.unpack(data)
                if rec[key_name] == -1:
                    pos = mid
                    break
                elif rec[key_name] < record[key_name]:
                    left = mid + 1
                else:
                    pos = mid
                    right = mid - 1

        # Desplazar contenido para hacer espacio
        with open(self.file_name, "r+b") as f:
            f.seek(pos * self.schema.size)
            rest = f.read()
            f.seek((pos + 1) * self.schema.size)
            f.write(rest)
            f.seek(pos * self.schema.size)
            f.write(self.schema.pack(record))

    def reconstruct(self, key_name="id"):
        with open(self.aux_file, "rb") as aux:
            while True:
                data = aux.read(self.schema.size)
                if not data:
                    break
                rec = self.schema.unpack(data)
                if rec[key_name] != -1:
                    self._insert_ordered(rec, key_name=key_name)

        # Ajustar límite dinámicamente
        self.aux_limit = int(math.log(self.get_size(self.file_name) + self.aux_limit, 2))

        # Vaciar auxiliar
        open(self.aux_file, "wb").close()

    def search(self, key, key_name="id"):
        left, right = 0, self.get_size(self.file_name) - 1

        while left <= right:
            mid = (left + right) // 2
            rec = self.read_record(self.file_name, mid)
            if rec is None or rec[key_name] == -1:
                left = mid + 1
                continue
            if rec[key_name] == key:
                return rec
            elif key < rec[key_name]:
                right = mid - 1
            else:
                left = mid + 1

        # Buscar en aux.dat linealmente
        size = self.get_size(self.aux_file)
        for i in range(size):
            rec = self.read_record(self.aux_file, i)
            if rec and rec[key_name] == key:
                return rec
        return None

    def remove(self, key, key_name="id"):
        # Buscar en file principal
        left, right = 0, self.get_size(self.file_name) - 1
        with open(self.file_name, "r+b") as f:
            while left <= right:
                mid = (left + right) // 2
                f.seek(mid * self.schema.size)
                data = f.read(self.schema.size)
                if not data:
                    break
                rec = self.schema.unpack(data)
                if rec[key_name] == key:
                    rec[key_name] = -1
                    f.seek(mid * self.schema.size)
                    f.write(self.schema.pack(rec))
                    return True
                elif key < rec[key_name]:
                    right = mid - 1
                else:
                    left = mid + 1

        # Buscar en auxiliar
        size_aux = self.get_size(self.aux_file)
        with open(self.aux_file, "r+b") as f:
            for i in range(size_aux):
                f.seek(i * self.schema.size)
                data = f.read(self.schema.size)
                if not data:
                    continue
                rec = self.schema.unpack(data)
                if rec[key_name] == key:
                    rec[key_name] = -1
                    f.seek(i * self.schema.size)
                    f.write(self.schema.pack(rec))
                    return True
        return False

    def range_search(self, init_id, end_id, key_name="id"):
        results = []
        size = self.get_size(self.file_name)

        with open(self.file_name, "rb") as f:
            left, right = 0, size - 1
            start_pos = size
            while left <= right:
                mid = (left + right) // 2
                f.seek(mid * self.schema.size)
                data = f.read(self.schema.size)
                rec = self.schema.unpack(data)
                if rec[key_name] != -1 and rec[key_name] >= init_id:
                    start_pos = mid
                    right = mid - 1
                else:
                    left = mid + 1

            for i in range(start_pos, size):
                f.seek(i * self.schema.size)
                data = f.read(self.schema.size)
                if not data:
                    break
                rec = self.schema.unpack(data)
                if rec[key_name] == -1:
                    continue
                if rec[key_name] > end_id:
                    break
                results.append(rec)

        # Buscar en auxiliar
        size_aux = self.get_size(self.aux_file)
        with open(self.aux_file, "rb") as f:
            for i in range(size_aux):
                f.seek(i * self.schema.size)
                data = f.read(self.schema.size)
                if not data:
                    continue
                rec = self.schema.unpack(data)
                if rec[key_name] != -1 and init_id <= rec[key_name] <= end_id:
                    results.append(rec)

        results.sort(key=lambda r: r[key_name])
        return results

    def remove_all(self):
        open(self.file_name, "wb").close()
        open(self.aux_file, "wb").close()
