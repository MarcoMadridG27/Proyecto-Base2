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
        self.delmap_path = filename + ".del"
        # asegurar directorio y archivo
        dirpath = os.path.dirname(filename)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        if not os.path.exists(filename):
            with open(filename, 'wb'):
                pass
        # ensure delmap exists and is synced to file
        self._sync_delmap()

    def append_record(self, record_dict: Dict[str, Any]) -> int:
        """Empaqueta y añade un registro al final del archivo de datos. Devuelve el offset."""
        data = self.schema.pack(record_dict)
        with open(self.filename, 'ab') as f:
            offset = f.tell()
            f.write(data)
        # append a 0 flag to delmap (not deleted)
        with open(self.delmap_path, 'ab') as df:
            df.write(b'\x00')
        return offset

    def read_record(self, offset: int):
        """Lee un registro desde el offset dado. Retorna None si no hay suficiente espacio."""
        with open(self.filename, 'rb') as f:
            f.seek(offset)
            binary = f.read(self.schema.size)
            if not binary or len(binary) < self.schema.size:
                return None
        # determine record index and check delmap
        idx = offset // self.schema.size
        try:
            with open(self.delmap_path, 'rb') as df:
                df.seek(idx)
                flag = df.read(1)
                if not flag or flag == b'\x01':
                    # logically deleted
                    return None
        except Exception:
            # if delmap missing/unreadable, fallback to previous empty-record detection
            if binary.strip(b'\x00') == b'':
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
        """Marca un registro como borrado (tombstone) en el sidecar .del file (no borra físicamente)."""
        idx = offset // self.schema.size
        # mark flag as 1
        with open(self.delmap_path, 'r+b') as df:
            df.seek(idx)
            df.write(b'\x01')

    def scan_all(self) -> List[Any]:
        """Devuelve todos los registros válidos en el archivo y contabiliza accesos a disco."""
        records = []
        # iterate by record index and use delmap to detect logical deletions
        try:
            fsize = os.path.getsize(self.filename)
        except Exception:
            return records
        total = fsize // self.schema.size
        with open(self.filename, 'rb') as f, open(self.delmap_path, 'rb') as df:
            for idx in range(total):
                flag = df.read(1)
                binrec = f.read(self.schema.size)
                if not binrec or len(binrec) < self.schema.size:
                    break
                if flag == b'\x01':
                    # logically deleted
                    continue
                try:
                    inc_disk_access(1)
                except Exception:
                    pass
                records.append(self.schema.unpack(binrec))
        return records

    # ---------------- Delmap helpers ----------------
    def _sync_delmap(self):
        """Ensure the delmap exists and matches the current number of records.

        If delmap missing, create it scanning the data file: mark 0 for non-empty records, 1 for zeroed.
        """
        try:
            fsize = os.path.getsize(self.filename)
        except Exception:
            fsize = 0
        total = fsize // self.schema.size if self.schema.size > 0 else 0

        # if delmap exists, ensure length matches; otherwise rebuild
        if os.path.exists(self.delmap_path):
            try:
                dsize = os.path.getsize(self.delmap_path)
            except Exception:
                dsize = 0
            if dsize == total:
                return

        # build delmap by scanning data file
        with open(self.filename, 'rb') as f, open(self.delmap_path, 'wb') as df:
            for i in range(total):
                binrec = f.read(self.schema.size)
                if not binrec or len(binrec) < self.schema.size:
                    df.write(b'\x01')
                elif binrec.strip(b'\x00') == b'':
                    df.write(b'\x01')
                else:
                    df.write(b'\x00')


    