import os
from typing import List, Dict, Any

# Simple global counters for disk access metrics (per-process, resettable)
disk_accesses = 0

def reset_disk_accesses():
    global disk_accesses
    disk_accesses = 0

def inc_disk_access(n: int = 1):
    global disk_accesses
    disk_accesses += n

def get_disk_accesses() -> int:
    return disk_accesses


class FileManager:
    """
    Maneja operaciones de bajo nivel sobre archivos binarios (.dat).
    Se apoya en RecordSchema para empacar y desempacar registros.
    """

    def __init__(self, filename: str, schema):
        self.filename = filename
        self.schema = schema
        # asegurar directorio y archivo
        dirpath = os.path.dirname(filename)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        if not os.path.exists(filename):
            with open(filename, 'wb'):
                pass

    def append_record(self, record_dict: Dict[str, Any]) -> int:
        """Empaqueta y añade un registro al final del archivo de datos. Devuelve el offset."""
        data = self.schema.pack(record_dict)
        with open(self.filename, 'ab') as f:
            offset = f.tell()
            f.write(data)
        return offset

    def read_record(self, offset: int):
        """Lee un registro desde el offset dado. Retorna None si no hay suficiente espacio."""
        with open(self.filename, 'rb') as f:
            f.seek(offset)
            binary = f.read(self.schema.size)
            if not binary or len(binary) < self.schema.size:
                return None
        try:
            inc_disk_access(1)
        except Exception:
            pass
        return self.schema.unpack(binary)

    def update_record(self, offset: int, new_record_dict: Dict[str, Any]):
        data = self.schema.pack(new_record_dict)
        with open(self.filename, 'r+b') as f:
            f.seek(offset)
            f.write(data)

    def delete_record(self, offset: int):
        """Marca un registro como borrado (tombstone) sobrescribiendo con ceros."""
        with open(self.filename, 'r+b') as f:
            f.seek(offset)
            f.write(b'\x00' * self.schema.size)

    def scan_all(self) -> List[Any]:
        """Devuelve todos los registros válidos en el archivo y contabiliza accesos a disco."""
        records = []
        with open(self.filename, 'rb') as f:
            while True:
                binary = f.read(self.schema.size)
                if not binary or len(binary) < self.schema.size:
                    break
                # Ignorar registros "borrados"
                if binary.strip(b'\x00') == b'':
                    continue
                try:
                    inc_disk_access(1)
                except Exception:
                    pass
                records.append(self.schema.unpack(binary))
        return records

    