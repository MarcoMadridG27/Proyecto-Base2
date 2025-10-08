import os
import struct
import math
from typing import Optional, Tuple, List

# ============================================================
# Convención de punteros (1-based)
# ============================================================
DELETED_PTR = -1

def dptr(i: int) -> int:
    """ Convierte un índice a puntero de la región principal (D). """
    if i < 1:
        raise ValueError("d(i) requiere i >= 1")
    return i

def aptr(i: int) -> int:
    """ Convierte un índice a puntero de la región auxiliar (A). """
    if i < 1:
        raise ValueError("a(i) requiere i >= 1")
    return -(i + 1)  # evita colisión con -1

def is_end(p: int) -> bool:
    """ Verifica si el puntero es el final de la lista (0). """
    return p == 0

def ptr_to_loc(p: int) -> Tuple[bool, int]:
    """ Convierte puntero a (is_aux, idx) para registros válidos. """
    if p == 0 or p == DELETED_PTR:
        raise ValueError("Puntero fin/eliminado no tiene ubicación de registro")
    return (False, p) if p > 0 else (True, -p - 1)

def label(p: int) -> str:
    """ Retorna una etiqueta legible del puntero. """
    if p == 0: return "END"
    if p == DELETED_PTR: return "DEL"
    return f"d({p})" if p > 0 else f"a({-p-1})"

# ============================================================
# Layout de registro (payload + next_ptr)
# ============================================================
EMP_FORMAT = ''  # Formato para (offset(en memoria secundaria), value(key), next_ptr)
FORMAT_VALUE = ''
class EntrySF:
    """ Registro con un valor y puntero al siguiente en la lista lógica. """

    def __init__(self, offset: int, value, next_ptr: int = 0):
        print(value)
        self.offset = offset
        self.value = value
        self.next_ptr = next_ptr

    def pack(self) -> bytes:
        """ Empaqueta el registro en formato binario de acuerdo al tipo de valor. """

        if FORMAT_VALUE=="i":
            # Para enteros, simplemente empaquetamos como un entero
            return struct.pack(EMP_FORMAT, self.offset, self.value, self.next_ptr)
        elif FORMAT_VALUE=="f":
            # Para flotantes, usamos el tipo de datos `f` para empaquetar
            return struct.pack(EMP_FORMAT, self.offset, self.value, self.next_ptr)
        elif FORMAT_VALUE[len(FORMAT_VALUE)-1]=="s":
            return struct.pack(EMP_FORMAT, self.offset, self.value.encode('utf-8'), self.next_ptr)
        else:
            raise ValueError(f"Tipo de valor no soportado: {type(self.value)}")

    @staticmethod
    def unpack(buf: bytes) -> "EntrySF":
        """ Desempaqueta un registro desde bytes. """

        # Intentamos desempaquetar el registro de forma dinámica
        offset, value, next_ptr = struct.unpack(EMP_FORMAT, buf)

        # Si `value` es un entero o flotante, no necesitamos decodificar.
        # Si es un string, lo decodificamos.
        try:
            value = value.decode("utf-8")  # Intentamos decodificar si es un string
        except AttributeError:
            pass  # Si no es un string, ignoramos el error y mantenemos el valor tal cual

        return EntrySF(offset, value, next_ptr)

    def is_deleted(self) -> bool:
        """ Verifica si el registro está marcado como eliminado (tombstone). """
        return self.next_ptr == DELETED_PTR

# ============================================================
# Header: main_count, aux_count, head_ptr
# ============================================================
HEADER_FORMAT = "<iii"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

class SequentialFile:
    """
    Archivo secuencial con:
      - Región principal (D)
      - Región auxiliar (A)
      - Lista lógica ordenada enlazada por next_ptr
    """
    def __init__(self, table: str, column_type: str):

        """ Inicializa el archivo secuencial con el tipo de columna (formato). """
        # Crear un formato para el registro con el tipo de columna adecuado.
        global FORMAT_VALUE
        FORMAT_VALUE = column_type
        self.column_type = column_type  # Esto es como '100s' o 'i'
        self.filename = os.path.join("data_index", f"{table}_index_sequential.dat")
        os.makedirs("data_index", exist_ok=True)

        # Definir formato de registro según la columna (ejemplo: 'i' para INT o '100s' para VARCHAR)
        global EMP_FORMAT
        EMP_FORMAT = f"<i{column_type}i"  # offset, value, next_ptr
        self.RECORD_SIZE = struct.calcsize(EMP_FORMAT)

        # Si el archivo no existe, crearlo
        if not os.path.exists(self.filename):
            print(f"El archivo {self.filename} no  existe")
            with open(self.filename, "wb") as f:
                f.write(struct.pack(HEADER_FORMAT, 0, 0, 0))  # D=0, A=0, head=0

    # Header I/O
    def _get_header(self) -> Tuple[int, int, int]:
        """ Obtiene la cabecera del archivo. """
        with open(self.filename, "rb") as f:
            f.seek(0)
            return struct.unpack(HEADER_FORMAT, f.read(HEADER_SIZE))

    def _set_header(self, main_count: int, aux_count: int, head_ptr: int):
        """ Establece la cabecera del archivo. """
        with open(self.filename, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(HEADER_FORMAT, main_count, aux_count, head_ptr))

    # Offsets para las regiones
    def _offs_d(self, i: int) -> int:
        return HEADER_SIZE + (i - 1) * self.RECORD_SIZE

    def _offs_a(self, i: int, base_main: Optional[int] = None) -> int:
        if base_main is None:
            base_main, _, _ = self._get_header()
        return HEADER_SIZE + base_main * self.RECORD_SIZE + (i - 1) * self.RECORD_SIZE

    # Registro I/O
    def _read_rec(self, is_aux: bool, idx: int, base_main: Optional[int] = None) -> EntrySF:
        """ Lee un registro desde el archivo (en D o A). """
        with open(self.filename, "rb") as f:
            f.seek(self._offs_a(idx, base_main) if is_aux else self._offs_d(idx))
            return EntrySF.unpack(f.read(self.RECORD_SIZE))

    def _write_rec(self, is_aux: bool, idx: int, rec: EntrySF, base_main: Optional[int] = None):
        """ Escribe un registro en el archivo (en D o A). """
        with open(self.filename, "r+b") as f:
            f.seek(self._offs_a(idx, base_main) if is_aux else self._offs_d(idx))
            f.write(rec.pack())

    # Búsqueda binaria en la región D (principal)
    def _lower_bound_d(self, key) -> int:
        """ Encuentra la primera posición en D donde el valor es mayor o igual a la clave. """
        main_count, _, _ = self._get_header()
        l, r, ans = 1, main_count, main_count + 1
        while l <= r:
            m = (l + r) // 2
            rec = self._read_rec(False, m, main_count)
            if rec.value >= key:
                ans = m
                r = m - 1
            else:
                l = m + 1
        return ans

    def range_search(self, lo, hi) -> List[int]:
        if lo > hi:
            lo, hi = hi, lo
        main_count, _, head_ptr = self._get_header()
        res: List[int] = []
        if head_ptr == 0:
            return res

        # 1) binaria en D con 'lo' para ubicar predecesor
        lb = self._lower_bound_d(lo)
        j = min(lb - 1, main_count)
        while j >= 1:
            cand = self._read_rec(False, j, main_count)
            if not cand.is_deleted():
                start_ptr = cand.next_ptr
                break
            j -= 1
        else:
            start_ptr = head_ptr

        # 2) caminar hasta superar hi
        cur = start_ptr
        while not is_end(cur):
            is_aux, idx = ptr_to_loc(cur)
            node = self._read_rec(is_aux, idx, main_count)
            if node.is_deleted():
                cur = node.next_ptr
                continue
            if node.value > hi:
                break
            if node.value >= lo:
                res.append(node.offset)
            cur = node.next_ptr
        return res

    def search(self, key) -> Optional[int]:
        """ Busca un registro por clave en la lista lógica. """
        main_count, _, head_ptr = self._get_header()
        if head_ptr == 0:
            return None

        lb = self._lower_bound_d(key)
        cur = head_ptr
        while cur != 0:
            is_aux, idx = ptr_to_loc(cur)
            node = self._read_rec(is_aux, idx, main_count)
            if node.is_deleted():
                cur = node.next_ptr
                continue
            if node.value == key:
                return node.offset
            if node.value > key:
                return None
            cur = node.next_ptr
        return None

    def insert(self, col_value, off_set):
        """
        Inserta SIEMPRE en AUX y lo encadena en la posición ordenada:
        - binaria en D para obtener el más cercano a la izquierda
        - caminar por la cadena lógica mientras cur.codigo < emp.codigo
        - enlazar prev -> new -> cur
        """
        main_count, aux_count, head_ptr = self._get_header()
        emp= EntrySF(off_set,col_value)
        # 0) guardar en AUX (1-based)
        new_idx = aux_count + 1
        emp.next_ptr = 0
        self._write_rec(True, new_idx, emp, main_count)
        new_ptr = aptr(new_idx)
        aux_count += 1

        # lista vacía
        if head_ptr == 0:
            head_ptr = new_ptr
            self._set_header(main_count, aux_count, head_ptr)
            self._maybe_reorganize()
            return

        # 1) binaria en D por emp.codigo
        lb = self._lower_bound_d(emp.value)
        j = min(lb - 1, main_count)
        # retroceder si d(j) está borrado
        while j >= 1:
            cand = self._read_rec(False, j, main_count)
            if not cand.is_deleted():
                break
            j -= 1

        # 2) decidir prev_ptr y cur_ptr
        if j >= 1:
            prev_ptr = dptr(j)
            cur_ptr = self._read_rec(False, j, main_count).next_ptr
        else:
            # podría ir al inicio si <= head
            h_is_aux, h_idx = ptr_to_loc(head_ptr)
            head = self._read_rec(h_is_aux, h_idx, main_count)
            if emp.value <= head.value:
                emp.next_ptr = head_ptr
                self._write_rec(True, new_idx, emp, main_count)
                head_ptr = new_ptr
                self._set_header(main_count, aux_count, head_ptr)
                self._maybe_reorganize()
                return
            prev_ptr = 0
            cur_ptr = head_ptr

        # 3) avanzar por punteros mientras cur.codigo < emp.codigo
        while not is_end(cur_ptr):
            is_aux, idx = ptr_to_loc(cur_ptr)
            node = self._read_rec(is_aux, idx, main_count)
            if node.is_deleted():  # defensivo
                cur_ptr = node.next_ptr
                continue
            if node.value < emp.value:
                prev_ptr = cur_ptr
                cur_ptr = node.next_ptr
            else:
                break

        # 4) enlazar prev -> new -> cur
        emp.next_ptr = cur_ptr
        self._write_rec(True, new_idx, emp, main_count)

        if prev_ptr == 0:
            head_ptr = new_ptr
        else:
            p_is_aux, p_idx = ptr_to_loc(prev_ptr)
            prev_node = self._read_rec(p_is_aux, p_idx, main_count)
            prev_node.next_ptr = new_ptr
            self._write_rec(p_is_aux, p_idx, prev_node, main_count)

        self._set_header(main_count, aux_count, head_ptr)
        self._maybe_reorganize()

    def delete(self, key) -> int:
        """ Elimina un registro lógico marcándolo como tombstone. """
        main_count, aux_count, head_ptr = self._get_header()
        if head_ptr == 0:
            return False

        lb = self._lower_bound_d(key)
        cur_ptr = head_ptr
        while cur_ptr != 0:
            is_aux, idx = ptr_to_loc(cur_ptr)
            node = self._read_rec(is_aux, idx, main_count)

            if node.value == key:
                node.next_ptr = DELETED_PTR
                self._write_rec(is_aux, idx, node, main_count)
                return node.offset

            cur_ptr = node.next_ptr
        return 0

    def _maybe_reorganize(self):
        main_count, aux_count, _ = self._get_header()
        # Política simple: cuando AUX supera floor(log2(main_count+1))
        k = int(math.log2(max(1, main_count + 1)))
        if aux_count > k:
            self.reorganize()

    def reorganize(self):
        """Reconstruye D leyendo desde head y siguiendo punteros en orden lógico."""
        main_count, aux_count, head_ptr = self._get_header()
        if head_ptr == 0:
            self._set_header(0, 0, 0)
            return

        base_main = main_count  # fija la base para leer A correctamente
        ordered: List[EntrySF] = []
        cur = head_ptr
        seen = 0
        cap = base_main + aux_count + 10
        while not is_end(cur) and seen < cap:
            is_aux, idx = ptr_to_loc(cur)
            node = self._read_rec(is_aux, idx, base_main)
            if not node.is_deleted():
                ordered.append(node)
            cur = node.next_ptr
            seen += 1

        # escribir compactado en D como d(1..N) y encadenar d(i)->d(i+1)
        new_main = len(ordered)
        with open(self.filename, "r+b") as f:
            for i, rec in enumerate(ordered, start=1):
                rec.next_ptr = dptr(i + 1) if i < new_main else 0
                f.seek(self._offs_d(i))
                f.write(rec.pack())

        self._set_header(new_main, 0, dptr(1) if new_main >= 1 else 0)
