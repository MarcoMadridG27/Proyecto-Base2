# core/file_manager.py
import os

class FileManager:
    """
    Maneja operaciones de bajo nivel sobre archivos binarios (.dat).
    Se apoya en RecordSchema para empacar y desempacar registros.
    """

    def __init__(self, filename, schema):
        """
        filename: ruta del archivo binario (ej. "restaurantes.dat")
        schema: instancia de RecordSchema
        """
        self.filename = filename
        self.schema = schema

        # Si no existe, creamos el archivo vacío
        if not os.path.exists(filename):
            with open(filename, "wb") as f:
                pass

    def append_record(self, record_dict):
        data = self.schema.pack(record_dict)
        print(f"[DEBUG] Empacando registro: {record_dict}")
        print(f"[DEBUG] Bytes generados: {len(data)} -> {data[:50]}...")  # primeras 50 bytes
        with open(self.filename, "ab") as f:
            offset = f.tell()
            print(f"[DEBUG] Offset antes de escribir: {offset}")
            f.write(data)
            print(f"[DEBUG] Nuevo tamaño archivo: {f.tell()}")
        return offset


    def read_record(self, offset):
        """
        Lee un registro desde el offset dado.
        """
        with open(self.filename, "rb") as f:
            f.seek(offset)
            binary = f.read(self.schema.size)
            if not binary or len(binary) < self.schema.size:
                return None
        return self.schema.unpack(binary)

    def update_record(self, offset, new_record_dict):
        """
        Sobrescribe un registro en un offset específico.
        """
        data = self.schema.pack(new_record_dict)
        with open(self.filename, "r+b") as f:
            f.seek(offset)
            f.write(data)

    def delete_record(self, offset):
        """
        Marca un registro como borrado (tombstone).
        En este caso, sobrescribimos con bytes nulos.
        """
        with open(self.filename, "r+b") as f:
            f.seek(offset)
            f.write(b"\x00" * self.schema.size)

    def scan_all(self):
        """
        Devuelve todos los registros válidos en el archivo.
        """
        records = []
        with open(self.filename, "rb") as f:
            while True:
                binary = f.read(self.schema.size)
                if not binary or len(binary) < self.schema.size:
                    break
                # Ignorar registros "borrados"
                if binary.strip(b"\x00") == b"":
                    continue
                records.append(self.schema.unpack(binary))
        return records
    