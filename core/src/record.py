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
            
            # Limpiar valor (quitar comillas si vienen del parser)
            if isinstance(val, str):
                val = val.strip().strip("'\"")
            
            try:
                if ctype == "INT":
                    packed.append(int(val) if val else 0)
                    
                elif ctype == "FLOAT":
                    packed.append(float(val) if val else 0.0)
                    
                elif ctype.startswith("VARCHAR"):
                    n = int(ctype.split("[")[1].strip("]"))
                    val_str = str(val) if val else ""
                    packed.append(val_str.encode('utf-8')[:n].ljust(n, b" "))
                    
                elif ctype == "DATE":
                    # Manejar diferentes formatos de fecha
                    if isinstance(val, datetime):
                        val = val.strftime("%Y-%m-%d")
                    elif val:
                        # Convertir DD-MM-YYYY o similar a YYYY-MM-DD
                        val_str = str(val)
                        # Si viene en formato DD-MM-YYYY
                        if "-" in val_str and len(val_str.split("-")) == 3:
                            parts = val_str.split("-")
                            if len(parts[0]) <= 2:  # DD-MM-YYYY
                                val_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        val = val_str[:10]
                    else:
                        val = "0000-00-00"
                        
                    packed.append(val.encode('utf-8').ljust(10, b" "))
                    
                elif ctype.startswith("ARRAY[FLOAT]"):
                    # val debe ser lista/tupla de 2 floats
                    if isinstance(val, (list, tuple)):
                        packed.extend([float(val[0]), float(val[1])])
                    else:
                        packed.extend([0.0, 0.0])
                        
            except Exception as e:
                print(f"Error empaquetando columna {col['name']} con valor '{val}': {e}")
                # Valores por defecto en caso de error
                if ctype == "INT":
                    packed.append(0)
                elif ctype == "FLOAT":
                    packed.append(0.0)
                elif ctype.startswith("VARCHAR"):
                    n = int(ctype.split("[")[1].strip("]"))
                    packed.append(b" " * n)
                elif ctype == "DATE":
                    packed.append(b"0000-00-00")
                elif ctype.startswith("ARRAY[FLOAT]"):
                    packed.extend([0.0, 0.0])
        
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
