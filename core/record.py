# core/record.py
import struct
from datetime import datetime

class RecordSchema:
    """
    Maneja el esquema de una tabla y genera formato binario para registros.
    """

    def __init__(self, columns):
        """
        columns: lista de diccionarios con estructura:
            [
                {"name": "id", "type": "INT"},
                {"name": "nombre", "type": "VARCHAR[20]"},
                {"name": "fechaRegistro", "type": "DATE"},
                {"name": "ubicacion", "type": "FLOAT"}   # o ARRAY[FLOAT]
            ]
        """
        self.columns = columns
        self.format = self._build_format(columns)
        self.size = struct.calcsize(self.format)

    def _build_format(self, columns):
        fmt = ""
        for col in columns:
            ctype = col["type"].upper()
            if ctype == "INT":
                fmt += "i"   # 4 bytes
            elif ctype == "FLOAT":
                fmt += "f"   # 4 bytes
            elif ctype.startswith("VARCHAR"):
                n = int(ctype.split("[")[1].strip("]"))
                fmt += f"{n}s"
            elif ctype == "DATE":
                fmt += "10s"  # AAAA-MM-DD
            elif ctype.startswith("ARRAY[FLOAT]"):
                # Por simplicidad, asumimos tamaño fijo de 2 floats (ej. lat, lon)
                fmt += "ff"
            else:
                raise ValueError(f"Tipo de dato no soportado: {ctype}")
        return fmt

    def pack(self, values):
        """
        Convierte una lista o dict de valores a bytes según el esquema.
        """
        if isinstance(values, dict):
            values = [values[col["name"]] for col in self.columns]

        packed = []
        for col, val in zip(self.columns, values):
            ctype = col["type"].upper()
            if ctype == "INT":
                packed.append(int(val))
            elif ctype == "FLOAT":
                packed.append(float(val))
            elif ctype.startswith("VARCHAR"):
                n = int(ctype.split("[")[1].strip("]"))
                packed.append(str(val).encode().ljust(n, b" "))
            elif ctype == "DATE":
                # Guardamos como string YYYY-MM-DD
                if isinstance(val, datetime):
                    val = val.strftime("%Y-%m-%d")
                packed.append(str(val).encode().ljust(10, b" "))
            elif ctype.startswith("ARRAY[FLOAT]"):
                # val debe ser lista/tupla de 2 floats
                packed.extend([float(val[0]), float(val[1])])
        return struct.pack(self.format, *packed)

    def unpack(self, binary):
        """
        Convierte bytes a un dict con nombres de columna y valores.
        """
        unpacked = struct.unpack(self.format, binary)
        record = {}
        i = 0
        for col in self.columns:
            ctype = col["type"].upper()
            if ctype == "INT":
                record[col["name"]] = unpacked[i]
                i += 1
            elif ctype == "FLOAT":
                record[col["name"]] = unpacked[i]
                i += 1
            elif ctype.startswith("VARCHAR"):
                record[col["name"]] = unpacked[i].decode().strip()
                i += 1
            elif ctype == "DATE":
                record[col["name"]] = unpacked[i].decode().strip()
                i += 1
            elif ctype.startswith("ARRAY[FLOAT]"):
                record[col["name"]] = [unpacked[i], unpacked[i+1]]
                i += 2
        return record
