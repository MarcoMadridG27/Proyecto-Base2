import os
from typing import Dict, Any, Iterator, Tuple, Optional

class FileManager:
    """
    Archivo .dat de registros de tamaño fijo (no hay headers por registro).
    - Borrado = bytes a cero.
    - Devuelve offsets reales para poder indexar.
    """

    def __init__(self, filename: str, schema):
        self.filename = filename
        self.schema = schema
        if not os.path.exists(filename):
            with open(filename, "wb"):
                pass

    @property
    def record_size(self) -> int:
        return self.schema.size

    def file_size(self) -> int:
        return os.path.getsize(self.filename)

    def append_record(self, record_dict: Dict[str, Any]) -> int:
        """Empaca y escribe al final. Retorna offset (byte) donde empieza el registro."""
        data = self.schema.pack(record_dict)
        if len(data) != self.record_size:
            raise ValueError("Tamaño pack != schema.size")
        with open(self.filename, "ab") as f:
            off = f.tell()
            f.write(data)
        return off

    def read_record(self, offset: int) -> Optional[Dict[str, Any]]:
        """Lee en offset; None si fuera de rango o tombstone (todo \x00)."""
        if offset < 0 or offset + self.record_size > self.file_size():
            return None
        with open(self.filename, "rb") as f:
            f.seek(offset)
            buf = f.read(self.record_size)
        if len(buf) < self.record_size:
            return None
        if buf.strip(b"\x00") == b"":
            return None
        return self.schema.unpack(buf)

    def update_record(self, offset: int, new_record_dict: Dict[str, Any]) -> bool:
        """Sobrescribe en offset si es válido."""
        if offset < 0 or offset + self.record_size > self.file_size():
            return False
        data = self.schema.pack(new_record_dict)
        if len(data) != self.record_size:
            raise ValueError("Tamaño pack != schema.size")
        with open(self.filename, "r+b") as f:
            f.seek(offset)
            f.write(data)
        return True

    def delete_record(self, offset: int) -> bool:
        """Marca borrado escribiendo \x00 * record_size."""
        if offset < 0 or offset + self.record_size > self.file_size():
            return False
        with open(self.filename, "r+b") as f:
            f.seek(offset)
            f.write(b"\x00" * self.record_size)
        return True

    def scan_all(self) -> Iterator[Dict[str, Any]]:
        """Itera todos los registros válidos (no borrados)."""
        size = self.record_size
        end = self.file_size()
        with open(self.filename, "rb") as f:
            off = 0
            while off + size <= end:
                f.seek(off)
                buf = f.read(size)
                if len(buf) < size:
                    break
                if buf.strip(b"\x00") != b"":
                    yield self.schema.unpack(buf)
                off += size

    def scan_all_with_offsets(self) -> Iterator[Tuple[int, Dict[str, Any]]]:
        """Igual que scan_all, pero entrega también offset de cada registro."""
        size = self.record_size
        end = self.file_size()
        with open(self.filename, "rb") as f:
            off = 0
            while off + size <= end:
                f.seek(off)
                buf = f.read(size)
                if len(buf) < size:
                    break
                if buf.strip(b"\x00") != b"":
                    yield off, self.schema.unpack(buf)
                off += size
