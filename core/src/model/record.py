import struct
from datetime import datetime
from typing import List, Dict, Any

class RecordSchema:
    """
    Esquema -> formato binario fijo (little-endian, sin padding extra).
    Tipos: INT(4B), FLOAT(8B), VARCHAR[n](nB), DATE("YYYY-MM-DD" 10B), ARRAY[FLOAT](2x8B).
    """

    def __init__(self, columns: List[Dict[str, str]]):
        self.columns = columns
        self.format = self._build_format(columns)   # ej. "<i20s10s"
        self.size = struct.calcsize(self.format)    # tamaño fijo del registro

    def _build_format(self, columns: List[Dict[str, str]]) -> str:
        fmt = "<"  # little-endian
        for col in columns:
            ctype = col["type"].upper().strip()
            if ctype == "INT":
                fmt += "i"
            elif ctype == "FLOAT":
                fmt += "f"
            elif ctype.startswith("VARCHAR"):
                # VARCHAR[20] -> 20s
                try:
                    # Primero aseguramos que el formato está en el tipo correcto
                    if "[" in ctype and "]" in ctype:
                        n = int(ctype.split("[", 1)[1].split("]", 1)[0])  # obtiene el número entre corchetes
                        if n <= 0: raise ValueError
                        fmt += f"{n}s"  # Retorna un formato de cadena de longitud variable
                    else:
                        raise ValueError(f"VARCHAR inválido: {ctype}")
                except Exception:
                    raise ValueError(f"VARCHAR inválido: {ctype}")
            elif ctype == "DATE":
                fmt += "10s"
            else:
                raise ValueError(f"Tipo no soportado: {ctype}")
        return fmt

    def _norm_date(self, val: Any) -> bytes:
        """Normaliza/convierte a 'YYYY-MM-DD' (10 bytes)."""
        if isinstance(val, datetime):
            s = val.strftime("%Y-%m-%d")
        elif isinstance(val, str):
            s = val.strip().strip("'\"")
            # intenta formatear a YYYY-MM-DD
            for pat in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
                try:
                    s = datetime.strptime(s, pat).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            s = s[:10]
        else:
            s = "0000-00-00"
        return s.encode("utf-8").ljust(10, b" ")

    def pack(self, values: Any) -> bytes:
        """
        Dict/list -> bytes. Sin NULLs: usa defaults (0, 0.0, "" rellenado, '0000-00-00').
        """
        if isinstance(values, dict):
            values = [values.get(c["name"], None) for c in self.columns]
        fields = []
        for col, val in zip(self.columns, values):
            ctype = col["type"].upper().strip()
            if isinstance(val, str):
                val = val.strip().strip("'\"")

            try:
                if ctype == "INT":
                    fields.append(int(val) if val is not None else 0)
                elif ctype == "FLOAT":
                    fields.append(float(val) if val is not None else 0.0)
                elif ctype.startswith("VARCHAR"):
                    n = int(ctype.split("[",1)[1].split("]",1)[0])
                    s = "" if val is None else str(val)
                    fields.append(s.encode("utf-8")[:n].ljust(n, b" "))
                elif ctype == "DATE":
                    fields.append(self._norm_date(val))
            except Exception:
                # fallback defensivo
                if ctype == "INT":
                    fields.append(0)
                elif ctype == "FLOAT":
                    fields.append(0.0)
                elif ctype.startswith("VARCHAR"):
                    n = int(ctype.split("[",1)[1].split("]",1)[0])
                    fields.append(b" " * n)
                elif ctype == "DATE":
                    fields.append(b"0000-00-00")
        return struct.pack(self.format, *fields)

    def unpack(self, binary: bytes) -> Dict[str, Any]:
        """Bytes -> dict (decodifica VARCHAR/DATE a str)."""
        vals = struct.unpack(self.format, binary)
        rec: Dict[str, Any] = {}
        i = 0
        for col in self.columns:
            name = col["name"]
            ctype = col["type"].upper().strip()
            if ctype == "INT":
                rec[name] = int(vals[i]); i += 1
            elif ctype == "FLOAT":
                rec[name] = float(vals[i]); i += 1
            elif ctype.startswith("VARCHAR"):
                rec[name] = vals[i].decode("utf-8", errors="ignore").rstrip(" "); i += 1
            elif ctype == "DATE":
                rec[name] = vals[i].decode("utf-8", errors="ignore").strip(); i += 1
        return rec
