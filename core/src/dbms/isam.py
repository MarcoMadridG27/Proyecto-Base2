import struct
import os
import time

BLOCK_FACTOR = 30# se puede aumetar apra disminuir tiempos
INDEX_FACTOR = 20# se puede aumentar


class Record:
    """
    Generic ISAM record containing only the indexed key (id) and the file offset
    where the full table record lives. This makes ISAM independent from the table
    schema: the index stores (id, offset) and queries can read the real record
    from the table file using the offset.
    FORMAT: 'ii' -> id:int, offset:int
    """
    FORMAT = 'ii'
    SIZE_OF_RECORD = struct.calcsize(FORMAT)

    def __init__(self, id: int, offset: int):
        self.id = int(id)
        self.offset = int(offset)

    def pack(self) -> bytes:
        return struct.pack(self.FORMAT, self.id, self.offset)

    @staticmethod
    def unpack(data: bytes):
        id, offset = struct.unpack(Record.FORMAT, data)
        return Record(id, offset)

    def __str__(self):
        return f"ID: {self.id}, Offset: {self.offset}"


class Page:
    HEADER_FORMAT = 'ii'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    SIZE_OF_PAGE = HEADER_SIZE + BLOCK_FACTOR * Record.SIZE_OF_RECORD

    def __init__(self, records=None, next_page=-1):
        self.records = records if records else []
        self.next_page = next_page

    def pack(self):
        header_data = struct.pack(self.HEADER_FORMAT, len(self.records), self.next_page)
        records_data = b''
        for record in self.records:
            records_data += record.pack()
        i = len(self.records)
        while i < BLOCK_FACTOR:
            records_data += b'\x00' * Record.SIZE_OF_RECORD
            i += 1
        return header_data + records_data

    @staticmethod
    def unpack(data: bytes):
        size, next_page = struct.unpack(Page.HEADER_FORMAT, data[:Page.HEADER_SIZE])
        records = []
        offset = Page.HEADER_SIZE
        for i in range(size):
            record_data = data[offset: offset + Record.SIZE_OF_RECORD]
            records.append(Record.unpack(record_data))
            offset += Record.SIZE_OF_RECORD
        return Page(records, next_page)


class IndexPage:
    m = INDEX_FACTOR

    def __init__(self):
        self.keys = [0] * self.m
        self.pages = [0] * (self.m + 1)
        self.size = 0

    def pack(self):
        keys_data = b''.join(struct.pack('i', key) for key in self.keys)
        pages_data = b''.join(struct.pack('i', page) for page in self.pages)
        return struct.pack('i', self.size) + keys_data + pages_data

    @staticmethod
    def unpack(data: bytes):
        if len(data) < 4:
            raise ValueError("Datos insuficientes para desempaquetar IndexPage")

        size = struct.unpack('i', data[:4])[0]
        keys = []
        offset = 4

        for i in range(INDEX_FACTOR):
            if offset + 4 > len(data):
                raise ValueError(f"Datos insuficientes en offset {offset}")
            key = struct.unpack('i', data[offset: offset + 4])[0]
            keys.append(key)
            offset += 4

        pages = []
        for i in range(INDEX_FACTOR + 1):
            if offset + 4 > len(data):
                raise ValueError(f"Datos insuficientes en offset {offset}")
            page = struct.unpack('i', data[offset: offset + 4])[0]
            pages.append(page)
            offset += 4

        index_page = IndexPage()
        index_page.size = size
        index_page.keys = keys
        index_page.pages = pages
        return index_page

    def isFull(self):
        return self.size == self.m

    def insert(self, key: int, page: int):
        if self.isFull():
            return False
        i = self.size - 1
        while i >= 0 and self.keys[i] > key:
            self.keys[i + 1] = self.keys[i]
            self.pages[i + 2] = self.pages[i + 1]
            i -= 1
        self.keys[i + 1] = key
        self.pages[i + 2] = page
        self.size += 1
        return True


class OverflowPage:
    HEADER_FORMAT = 'ii'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    SIZE_OF_PAGE = HEADER_SIZE + BLOCK_FACTOR * Record.SIZE_OF_RECORD

    def __init__(self, records=None, next_overflow=-1):
        self.records = records if records else []
        self.next_overflow = next_overflow

    def pack(self):
        header_data = struct.pack(self.HEADER_FORMAT, len(self.records), self.next_overflow)
        records_data = b''
        for record in self.records:
            records_data += record.pack()
        i = len(self.records)
        while i < BLOCK_FACTOR:
            records_data += b'\x00' * Record.SIZE_OF_RECORD
            i += 1
        return header_data + records_data

    @staticmethod
    def unpack(data: bytes):
        size, next_overflow = struct.unpack(OverflowPage.HEADER_FORMAT, data[:OverflowPage.HEADER_SIZE])
        records = []
        offset = OverflowPage.HEADER_SIZE
        for i in range(size):
            record_data = data[offset: offset + Record.SIZE_OF_RECORD]
            records.append(Record.unpack(record_data))
            offset += Record.SIZE_OF_RECORD
        return OverflowPage(records, next_overflow)

    def isFull(self):
        return len(self.records) >= BLOCK_FACTOR


class ISAMMultinivel:
    def __init__(self, nivel_1_index, nivel_2_index, nivel_3_data, overflow_file):
        self.nivel_1_index = nivel_1_index
        self.nivel_2_index = nivel_2_index
        self.nivel_3_data = nivel_3_data
        self.overflow_file = overflow_file
        self.records_buffer = []

        for filename in [nivel_1_index, nivel_2_index, nivel_3_data, overflow_file]:
            if not os.path.exists(filename):
                with open(filename, "wb") as f:
                    pass

    def load_index(self, filename):
        with open(filename, 'rb') as f:
            data = f.read()
            if len(data) == 0:
                return IndexPage()
            return IndexPage.unpack(data)

    def save_index(self, filename, index_page: IndexPage):
        with open(filename, 'wb') as f:
            f.write(index_page.pack())

    def read_page(self, filename, page_number: int):
        with open(filename, 'rb') as f:
            f.seek(page_number * Page.SIZE_OF_PAGE)
            data = f.read(Page.SIZE_OF_PAGE)
            if len(data) < Page.SIZE_OF_PAGE:
                return Page()
            return Page.unpack(data)

    def read_index_page_from_file(self, filename, page_number: int):
        index_size = struct.calcsize('i') + (INDEX_FACTOR * struct.calcsize('i')) + (
                    (INDEX_FACTOR + 1) * struct.calcsize('i'))
        with open(filename, 'rb') as f:
            f.seek(page_number * index_size)
            data = f.read(index_size)
            if len(data) < index_size:
                return IndexPage()
            return IndexPage.unpack(data)

    def write_page(self, filename, page_number: int, page: Page):
        with open(filename, 'r+b') as f:
            f.seek(page_number * Page.SIZE_OF_PAGE)
            f.write(page.pack())

    def append_page(self, filename, page: Page):
        with open(filename, 'ab') as f:
            f.write(page.pack())
        with open(filename, 'rb') as f:
            f.seek(0, 2)
            return (f.tell() // Page.SIZE_OF_PAGE) - 1

    def read_overflow_page(self, overflow_number: int):
        with open(self.overflow_file, 'rb') as f:
            f.seek(overflow_number * OverflowPage.SIZE_OF_PAGE)
            data = f.read(OverflowPage.SIZE_OF_PAGE)
            return OverflowPage.unpack(data)

    def write_overflow_page(self, overflow_number: int, overflow_page: OverflowPage):
        with open(self.overflow_file, 'r+b') as f:
            f.seek(overflow_number * OverflowPage.SIZE_OF_PAGE)
            f.write(overflow_page.pack())

    def append_overflow_page(self, overflow_page: OverflowPage):
        with open(self.overflow_file, 'ab') as f:
            f.write(overflow_page.pack())
        with open(self.overflow_file, 'rb') as f:
            f.seek(0, 2)
            return (f.tell() // OverflowPage.SIZE_OF_PAGE) - 1

    def binary_search_index(self, index_page: IndexPage, key: int):
        tam_index = index_page.size
        if tam_index == 0:
            return 0

        lista = index_page.keys
        low = 0
        high = tam_index - 1
        floor_index = -1

        while low <= high:
            mid = (low + high) // 2
            if lista[mid] == key:
                floor_index = mid
                break
            elif lista[mid] < key:
                floor_index = mid
                low = mid + 1
            else:
                high = mid - 1

        if floor_index == -1:
            return index_page.pages[0]
        return index_page.pages[floor_index + 1]

    def search(self, key: int):
        nivel_1 = self.load_index(self.nivel_1_index)
        nivel_2_page = self.binary_search_index(nivel_1, key)

        nivel_2_index_page = self.read_index_page_from_file(self.nivel_2_index, nivel_2_page)
        nivel_3_page = self.binary_search_index(nivel_2_index_page, key)

        page = self.read_page(self.nivel_3_data, nivel_3_page)
        for record in page.records:
            if record.id == key:
                return record

        if page.next_page != -1:
            current_overflow = page.next_page
            while current_overflow != -1:
                overflow_data = self.read_overflow_page(current_overflow)
                for record in overflow_data.records:
                    if record.id == key:
                        return record
                current_overflow = overflow_data.next_overflow

        return None

    # Compatibility: return offsets lists like other index classes
    def find(self, key: int):
        """Return a list of offsets for records with id == key."""
        res = []
        rec = self.search(key)
        if rec is None:
            return res
        # rec is a Record(id, offset)
        try:
            res.append(rec.offset)
        except Exception:
            pass
        return res

    def insert(self, record: Record):
        self.records_buffer.append(record)

    def insert_after_build(self, record: Record):
        nivel_1 = self.load_index(self.nivel_1_index)
        nivel_2_page = self.binary_search_index(nivel_1, record.id)
        nivel_2_index_page = self.read_index_page_from_file(self.nivel_2_index, nivel_2_page)
        nivel_3_page = self.binary_search_index(nivel_2_index_page, record.id)
        page = self.read_page(self.nivel_3_data, nivel_3_page)

        if len(page.records) < BLOCK_FACTOR:
            page.records.append(record)
            page.records.sort(key=lambda r: r.id)
            self.write_page(self.nivel_3_data, nivel_3_page, page)
            return True

        if page.next_page == -1:
            overflow_new = OverflowPage([record])
            overflow_num = self.append_overflow_page(overflow_new)
            page.next_page = overflow_num
            self.write_page(self.nivel_3_data, nivel_3_page, page)
            return True

        current_overflow_num = page.next_page
        prev_overflow_num = -1

        while current_overflow_num != -1:
            overflow_page = self.read_overflow_page(current_overflow_num)
            if not overflow_page.isFull():
                overflow_page.records.append(record)
                overflow_page.records.sort(key=lambda r: r.id)
                self.write_overflow_page(current_overflow_num, overflow_page)
                return True
            prev_overflow_num = current_overflow_num
            current_overflow_num = overflow_page.next_overflow

        overflow_new = OverflowPage([record])
        overflow_num = self.append_overflow_page(overflow_new)
        last_overflow = self.read_overflow_page(prev_overflow_num)
        last_overflow.next_overflow = overflow_num
        self.write_overflow_page(prev_overflow_num, last_overflow)
        return True

    def insert_batch_overflow(self, records: list):
        if not records:
            return True

        print(f"\nInsertando {len(records)} registros en overflow...")
        start = time.perf_counter()

        records_by_page = {}
        nivel_1 = self.load_index(self.nivel_1_index)

        for record in records:
            nivel_2_page = self.binary_search_index(nivel_1, record.id)
            nivel_2_index_page = self.read_index_page_from_file(self.nivel_2_index, nivel_2_page)
            nivel_3_page = self.binary_search_index(nivel_2_index_page, record.id)

            if nivel_3_page not in records_by_page:
                records_by_page[nivel_3_page] = []
            records_by_page[nivel_3_page].append(record)

        for page_num, page_records in records_by_page.items():
            # ordenar e intentar llenar espacio en la página principal
            page_records.sort(key=lambda r: r.id)
            page = self.read_page(self.nivel_3_data, page_num)

            space_in_main = BLOCK_FACTOR - len(page.records)
            if space_in_main > 0:
                to_insert = min(space_in_main, len(page_records))
                page.records.extend(page_records[:to_insert])
                page.records.sort(key=lambda r: r.id)
                self.write_page(self.nivel_3_data, page_num, page)
                page_records = page_records[to_insert:]

            # si quedaron registros, colocarlos en la cadena de overflow
            if page_records:
                self._insert_into_overflow_chain(page_num, page, page_records)

        end = time.perf_counter()
        print(f"Lote insertado en {end - start:.6f} segundos")
        return True

    def _insert_into_overflow_chain(self, page_num, page, records):
        records_to_insert = records.copy()

        # Si no existe cadena de overflow, crearla nueva con batches
        if page.next_page == -1:
            first_overflow_num = None
            prev_num = -1
            while records_to_insert:
                batch = records_to_insert[:BLOCK_FACTOR]
                records_to_insert = records_to_insert[BLOCK_FACTOR:]
                overflow_page = OverflowPage(batch)
                overflow_num = self.append_overflow_page(overflow_page)

                if first_overflow_num is None:
                    first_overflow_num = overflow_num
                if prev_num != -1:
                    prev_overflow = self.read_overflow_page(prev_num)
                    prev_overflow.next_overflow = overflow_num
                    self.write_overflow_page(prev_num, prev_overflow)
                prev_num = overflow_num

            page.next_page = first_overflow_num if first_overflow_num is not None else -1
            self.write_page(self.nivel_3_data, page_num, page)
            return

        # Si ya existe cadena de overflow, intentar llenar páginas existentes
        current_num = page.next_page
        prev_num = -1

        while current_num != -1 and records_to_insert:
            overflow_page = self.read_overflow_page(current_num)
            space_available = BLOCK_FACTOR - len(overflow_page.records)
            if space_available > 0:
                to_insert = min(space_available, len(records_to_insert))
                overflow_page.records.extend(records_to_insert[:to_insert])
                overflow_page.records.sort(key=lambda r: r.id)
                self.write_overflow_page(current_num, overflow_page)
                records_to_insert = records_to_insert[to_insert:]
            prev_num = current_num
            current_num = overflow_page.next_overflow

        # Si aún quedan registros, anexar nuevas páginas de overflow
        while records_to_insert:
            batch = records_to_insert[:BLOCK_FACTOR]
            records_to_insert = records_to_insert[BLOCK_FACTOR:]
            new_overflow = OverflowPage(batch)
            new_num = self.append_overflow_page(new_overflow)
            if prev_num != -1:
                prev_page = self.read_overflow_page(prev_num)
                prev_page.next_overflow = new_num
                self.write_overflow_page(prev_num, prev_page)
            prev_num = new_num

    def remove(self, key: int):
        nivel_1 = self.load_index(self.nivel_1_index)
        nivel_2_page = self.binary_search_index(nivel_1, key)
        nivel_2_index_page = self.read_index_page_from_file(self.nivel_2_index, nivel_2_page)
        nivel_3_page = self.binary_search_index(nivel_2_index_page, key)

        page = self.read_page(self.nivel_3_data, nivel_3_page)
        new_records = [r for r in page.records if r.id != key]
        if len(new_records) < len(page.records):
            page.records = new_records
            self.write_page(self.nivel_3_data, nivel_3_page, page)
            return True

        if page.next_page != -1:
            current_overflow = page.next_page
            while current_overflow != -1:
                overflow_page = self.read_overflow_page(current_overflow)
                new_records = [r for r in overflow_page.records if r.id != key]
                if len(new_records) < len(overflow_page.records):
                    overflow_page.records = new_records
                    self.write_overflow_page(current_overflow, overflow_page)
                    return True
                current_overflow = overflow_page.next_overflow
        return False

    def build_indices(self):
        if not self.records_buffer:
            return

        print(f"\nConstruyendo índices ({len(self.records_buffer)} registros)...")
        records = sorted(self.records_buffer, key=lambda r: r.id)

        nivel_3_pages = []
        for i in range(0, len(records), BLOCK_FACTOR):
            chunk = records[i:i + BLOCK_FACTOR]
            page = Page(chunk)
            nivel_3_pages.append(page)

        with open(self.nivel_3_data, 'wb') as f:
            for page in nivel_3_pages:
                f.write(page.pack())

        nivel_2_index_pages = []
        for j in range(0, len(nivel_3_pages), INDEX_FACTOR):
            index_page = IndexPage()
            chunk_end = min(j + INDEX_FACTOR, len(nivel_3_pages))
            index_page.pages[0] = j
            for idx in range(j + 1, chunk_end):
                if nivel_3_pages[idx].records:
                    first_key = nivel_3_pages[idx].records[0].id
                    index_page.insert(first_key, idx)
            nivel_2_index_pages.append(index_page)

        with open(self.nivel_2_index, 'wb') as f:
            for index_page in nivel_2_index_pages:
                f.write(index_page.pack())

        nivel_1_index = IndexPage()
        if len(nivel_2_index_pages) == 1:
            nivel_1_index.size = nivel_2_index_pages[0].size
            nivel_1_index.keys = nivel_2_index_pages[0].keys.copy()
            nivel_1_index.pages = nivel_2_index_pages[0].pages.copy()
        else:
            nivel_1_index.pages[0] = 0
            for i in range(1, len(nivel_2_index_pages)):
                nivel_2_page = nivel_2_index_pages[i]
                first_valid_key = None
                if nivel_2_page.size > 0:
                    if nivel_2_page.keys[0] != 0:
                        first_valid_key = nivel_2_page.keys[0]
                    else:
                        for k in range(nivel_2_page.size):
                            if nivel_2_page.keys[k] != 0:
                                first_valid_key = nivel_2_page.keys[k]
                                break
                if first_valid_key is None:
                    first_data_page_num = nivel_2_page.pages[0]
                    first_data_page = nivel_3_pages[first_data_page_num]
                    if first_data_page.records:
                        first_valid_key = first_data_page.records[0].id
                if first_valid_key is not None and first_valid_key != 0:
                    nivel_1_index.insert(first_valid_key, i)

        self.save_index(self.nivel_1_index, nivel_1_index)
        print(f"Índices construidos correctamente\n")

    def load_from_csv(self, csv_path, limit=None):
        print("\n" + "=" * 70)
        print("CARGA DESDE CSV")
        print("=" * 70)

        all_records = []
        try:
            with open(csv_path, "r", encoding="utf-8") as file:
                next(file)
                for i, linea in enumerate(file):
                    if limit and i >= limit:
                        break
                    linea = linea.rstrip("\n")
                    list_linea = linea.split(";")
                    id = int(list_linea[0])
                    # for CSV loader we only need id and offset placeholder (0)
                    record = Record(id, 0)
                    all_records.append(record)
            print(f"Total registros leídos: {len(all_records)}")
        except FileNotFoundError:
            print(f"Error: Archivo no encontrado - {csv_path}")
            return
        except Exception as e:
            print(f"Error leyendo CSV: {e}")
            return

        if not all_records:
            return

        max_capacity = (INDEX_FACTOR + 1) * (INDEX_FACTOR + 1) * BLOCK_FACTOR
        print(f"Capacidad máxima sin overflow: {max_capacity} registros")

        if len(all_records) <= max_capacity:
            initial_records = all_records
            overflow_records = []
        else:
            initial_records = all_records[:max_capacity]
            overflow_records = all_records[max_capacity:]
            print(f"Registros en estructura principal: {len(initial_records)}")
            print(f"Registros en overflow: {len(overflow_records)}")

        start = time.perf_counter()
        for record in initial_records:
            self.records_buffer.append(record)
        self.build_indices()
        end = time.perf_counter()
        print(f"Estructura construida en {end - start:.6f} segundos")

        if overflow_records:
            self.insert_batch_overflow(overflow_records)

        print("=" * 70 + "\n")

    def scanAll(self):
        nivel_1 = self.load_index(self.nivel_1_index)
        visited = set()
        count = 0
        overflow_pages_count = 0
        overflow_records_count = 0

        for i in range(nivel_1.size + 1):
            nivel_2_page_num = nivel_1.pages[i]
            nivel_2 = self.read_index_page_from_file(self.nivel_2_index, nivel_2_page_num)

            for j in range(nivel_2.size + 1):
                nivel_3_page_num = nivel_2.pages[j]
                if nivel_3_page_num in visited:
                    continue
                visited.add(nivel_3_page_num)

                page = self.read_page(self.nivel_3_data, nivel_3_page_num)
                if len(page.records) == 0:
                    continue

                print(f"#Página {nivel_3_page_num} ({len(page.records)} registros)")
                for record in page.records:
                    print(f"  {record}")
                    count += 1

                if page.next_page != -1:
                    current = page.next_page
                    while current != -1:
                        overflow_pages_count += 1
                        overflow = self.read_overflow_page(current)
                        print(f"#Overflow {current} ({len(overflow.records)} registros)")
                        for record in overflow.records:
                            print(f"  {record}")
                            count += 1
                            overflow_records_count += 1
                        current = overflow.next_overflow

        print(f"\n{'=' * 70}")
        print(f"Total registros: {count}")
        print(f"Páginas de overflow: {overflow_pages_count}")
        print(f"Registros en overflow: {overflow_records_count}")
        if overflow_pages_count > 0:
            print(f"Promedio registros/página overflow: {overflow_records_count / overflow_pages_count:.2f}")
        print(f"{'=' * 70}")

    def search_range(self, begin_key: int, end_key: int):

        results = []

        if begin_key > end_key:
            begin_key, end_key = end_key, begin_key

        nivel_1 = self.load_index(self.nivel_1_index)

        nivel_2_start = self.binary_search_index(nivel_1, begin_key)
        nivel_2_end = self.binary_search_index(nivel_1, end_key)

        nivel_2_pages_to_explore = []

        if nivel_2_start == nivel_2_end:
            # Caso simple: todo el rango está en una sola página de nivel 2
            nivel_2_pages_to_explore.append(nivel_2_start)
        else:
            # Caso complejo: el rango abarca múltiples páginas de nivel 2
            # Necesitamos encontrar todas las páginas entre start y end
            found_start = False
            for i in range(nivel_1.size + 1):
                page_num = nivel_1.pages[i]
                if page_num == nivel_2_start:
                    found_start = True
                if found_start:
                    nivel_2_pages_to_explore.append(page_num)
                if page_num == nivel_2_end:
                    break

        # NIVEL 2 y 3: Explorar solo las páginas relevantes
        visited_data_pages = set()

        for nivel_2_page_num in nivel_2_pages_to_explore:
            nivel_2_index = self.read_index_page_from_file(self.nivel_2_index, nivel_2_page_num)

            # Encontrar qué páginas de nivel 3 pueden contener el rango
            nivel_3_start = self.binary_search_index(nivel_2_index, begin_key)
            nivel_3_end = self.binary_search_index(nivel_2_index, end_key)

            # Determinar páginas de nivel 3 a explorar
            if nivel_3_start == nivel_3_end:
                # Todo en una página
                pages_to_check = [nivel_3_start]
            else:
                # Múltiples páginas - explorar desde start hasta end
                pages_to_check = []
                found_start = False
                for j in range(nivel_2_index.size + 1):
                    page_num = nivel_2_index.pages[j]
                    if page_num == nivel_3_start:
                        found_start = True
                    if found_start:
                        pages_to_check.append(page_num)
                    if page_num == nivel_3_end:
                        break
            for nivel_3_page_num in pages_to_check:
                if nivel_3_page_num in visited_data_pages:
                    continue
                visited_data_pages.add(nivel_3_page_num)
                page = self.read_page(self.nivel_3_data, nivel_3_page_num)

                for record in page.records:
                    if begin_key <= record.id <= end_key:
                        results.append(record)

                # Recolectar de overflow
                if page.next_page != -1:
                    current_overflow = page.next_page
                    while current_overflow != -1:
                        overflow_data = self.read_overflow_page(current_overflow)
                        for record in overflow_data.records:
                            if begin_key <= record.id <= end_key:
                                results.append(record)
                        current_overflow = overflow_data.next_overflow

        # los ordene para que se vea bonito en el moento de imprimir, esto no es primordial se peude comentar tranqui :p
        results.sort(key=lambda r: r.id)
        return results

    def range_search(self, begin_key: int, end_key: int):
        """Compatibility wrapper returning offsets for records in [begin_key, end_key]."""
        recs = self.search_range(begin_key, end_key)
        offsets = []
        for r in recs:
            try:
                offsets.append(r.offset)
            except Exception:
                continue
        return offsets


if __name__ == "__main__":
        # Limpiar archivos anteriores
        for f in ["nivel_1.dat", "nivel_2.dat", "nivel_3.dat", "overflow.dat"]:
            if os.path.exists(f):
                os.remove(f)

        db = ISAMMultinivel("nivel_1.dat", "nivel_2.dat", "nivel_3.dat", "overflow.dat")

        print("=" * 70)
        print("ISAM MULTINIVEL - DEMOSTRACIÓN DE OPERACIONES")
        print("=" * 70)
        print(f"Block Factor: {BLOCK_FACTOR}")
        print(f"Index Factor: {INDEX_FACTOR}")
        print(f"Capacidad máxima: {(INDEX_FACTOR + 1) * (INDEX_FACTOR + 1) * BLOCK_FACTOR} registros")
        print("=" * 70)

        # 1. CARGA DESDE CSV
        print("\n" + "=" * 70)
        print("1. CARGANDO DATOS DESDE CSV")
        print("=" * 70)
        db.load_from_csv("ventas_desordenadas2.csv", limit=None)

        # 2. BÚSQUEDA ESPECÍFICA (puede retornar múltiples elementos)
        print("\n" + "=" * 70)
        print("2. BÚSQUEDA ESPECÍFICA - search(key)")
        print("=" * 70)

        # Primero verificar que 10009 existe
        search_key = 10009
        print(f"Buscando registros con ID = {search_key}")
        start = time.perf_counter()
        results = db.search(search_key)
        end = time.perf_counter()

        # print(f"Resultados encontrados: {len(results)}")
        # print(f"Tiempo: {end - start:.6f} segundos")
        # if results:
        #     for record in results:
        #         print(f"  → {record}")
        # else:
        #     print("  No encontrado")

        # 3. BÚSQUEDA POR RANGO
        print("\n" + "=" * 70)
        print("3. BÚSQUEDA POR RANGO - rangeSearch(begin_key, end_key)")
        print("=" * 70)
        begin_key = 10000
        end_key = 10010
        print(f"Buscando registros en rango [{begin_key}, {end_key}]")
        start = time.perf_counter()
        results = db.search_range(begin_key, end_key)
        end = time.perf_counter()

        print(f"Resultados encontrados: {len(results)}")
        print(f"Tiempo: {end - start:.6f} segundos")

        # Verificar específicamente si 10009 está en los resultados
        ids_found = [r.id for r in results]
        print(f"IDs encontrados: {sorted(ids_found)}")

        if 10009 in ids_found:
            print("✓ ID 10009 SÍ está en el rango")
        else:
            print("✗ ID 10009 NO está en el rango (pero debería estar)")
            # Buscar específicamente 10009 para debug
            result_10009 = db.search(10009)
            if result_10009:
                print(f"  DEBUG: 10009 existe individualmente: {result_10009[0]}")

        if results:
            print("\nRegistros completos:")
            for record in results:
                print(f"  → {record}")
        else:
            print("  No se encontraron registros en el rango")

        # 4. AGREGAR REGISTROS
        print("\n" + "=" * 70)
        print("4. AGREGAR REGISTROS - add(registro)")
        print("=" * 70)
        nuevos_registros = [
            Record(99001, 0),
            Record(99002, 0),
            Record(99003, 0),
        ]

        for record in nuevos_registros:
            print(f"Agregando: {record}")
            start = time.perf_counter()
            success = db.insert_after_build(record)
            end = time.perf_counter()
            print(f"  {'✓ Agregado' if success else '✗ Error'} - Tiempo: {end - start:.6f} seg")

        # Verificar que se agregaron
        print("\nVerificando registros agregados:")
        for record in nuevos_registros:
            results = db.search(record.id)
            print(f"  ID {record.id}: {'✓ Encontrado' if results else '✗ No encontrado'}")

        # 5. ELIMINAR REGISTROS
        print("\n" + "=" * 70)
        print("5. ELIMINAR REGISTROS - remove(key)")
        print("=" * 70)
        keys_to_remove = [25995, 99002]

        for key in keys_to_remove:
            print(f"Eliminando registro con ID = {key}")
            start = time.perf_counter()
            success = db.remove(key)
            end = time.perf_counter()
            print(f"  {'✓ Eliminado' if success else '✗ No encontrado'} - Tiempo: {end - start:.6f} seg")

            # Verificar eliminación
            result = db.search(key)
            print(f"  Verificación: {'✗ Aún existe' if result else '✓ No existe'}")

        # 6. ESTADÍSTICAS FINALES
        print("\n" + "=" * 70)
        print("6. ESTADÍSTICAS FINALES")
        print("=" * 70)

        nivel_1 = db.load_index(db.nivel_1_index)
        visited = set()
        total_records = 0
        overflow_records = 0
        overflow_pages = 0
        main_pages = 0

        for i in range(nivel_1.size + 1):
            nivel_2_page_num = nivel_1.pages[i]
            nivel_2 = db.read_index_page_from_file(db.nivel_2_index, nivel_2_page_num)
            for j in range(nivel_2.size + 1):
                nivel_3_page_num = nivel_2.pages[j]
                if nivel_3_page_num in visited:
                    continue
                visited.add(nivel_3_page_num)
                page = db.read_page(db.nivel_3_data, nivel_3_page_num)
                if len(page.records) > 0:
                    main_pages += 1
                    total_records += len(page.records)

                if page.next_page != -1:
                    current = page.next_page
                    while current != -1:
                        overflow_pages += 1
                        overflow_page = db.read_overflow_page(current)
                        overflow_records += len(overflow_page.records)
                        total_records += len(overflow_page.records)
                        current = overflow_page.next_overflow

        print(f"Total de registros: {total_records}")
        print(f"Páginas principales: {main_pages}")
        print(f"Registros en overflow: {overflow_records}")
        print(f"Páginas de overflow: {overflow_pages}")
        if overflow_pages > 0:
            print(f"Promedio registros/página overflow: {overflow_records / overflow_pages:.2f}/{BLOCK_FACTOR}")
            efficiency = (overflow_records / overflow_pages) / BLOCK_FACTOR * 100
            print(f"Eficiencia: {efficiency:.2f}%")

        # 7. BÚSQUEDA POR RANGO ADICIONAL
        print("\n" + "=" * 70)
        print("7. BÚSQUEDA POR RANGO AMPLIO")
        print("=" * 70)
        begin_key = 99000
        end_key = 99005
        print(f"Buscando registros agregados en rango [{begin_key}, {end_key}]")
        results = db.search_range(begin_key, end_key)
        print(f"Resultados: {len(results)}")
        for record in results:
            print(f"  → {record}")

        print("\n" + "=" * 70)
        print("DEMOSTRACIÓN COMPLETADA")
        print("=" * 70)