



import struct
import os
import os
BLOCK_FACTOR = 2


class Record:
    FORMAT = 'i20sif20s'
    SIZE_OF_RECORD = struct.calcsize(FORMAT)

    def __init__(self, id: int, producto: str, cantidad: int, precio: float, fecha: str):
        self.id = id
        self.producto = producto
        self.cantidad = cantidad
        self.precio = precio
        self.fecha = fecha

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.id,
            self.producto.encode('latin-1').ljust(20, b'\x00'),
            self.cantidad,
            self.precio,
            self.fecha.encode('latin-1').ljust(20, b'\x00')
        )

    @staticmethod
    def unpack(data: bytes):
        id, producto, cantidad, precio, fecha = struct.unpack(Record.FORMAT, data)
        return Record(
            id,
            producto.decode('latin-1').strip('\x00'),
            cantidad,
            precio,
            fecha.decode('latin-1').strip('\x00')
        )

    def __str__(self):
        return f"ID: {self.id}, Producto: {self.producto}, Cantidad: {self.cantidad}, Precio: {self.precio}, Fecha: {self.fecha}"


class BPTreeLeaf:
    def __init__(self, max_keys, next_leaf=None):
        self.max_keys = max_keys
        self.keys = []  # Claves del nodo
        self.values = []  # Punteros a los registros
        self.next_leaf = next_leaf  # Puntero al siguiente nodo hoja (encadenamiento de hojas)

    def is_full(self):
        return len(self.keys) >= self.max_keys

    def insert(self, key, value):
        # Inserta el par clave-valor en el nodo hoja (usando inserción ordenada)
        idx = 0
        while idx < len(self.keys) and self.keys[idx] < key:
            idx += 1
        self.keys.insert(idx, key)
        self.values.insert(idx, value)

    def split(self):
        # Divide el nodo cuando está lleno
        mid = len(self.keys) // 2
        new_leaf = BPTreeLeaf(self.max_keys, self.next_leaf)
        new_leaf.keys = self.keys[mid:]
        new_leaf.values = self.values[mid:]
        self.keys = self.keys[:mid]
        self.values = self.values[:mid]
        self.next_leaf = new_leaf
        return self.keys[-1], new_leaf  # Devuelve la clave promovida y el nuevo nodo hoja

    def __str__(self):
        return f"Leaf(keys: {self.keys}, next: {self.next_leaf})"

class BPTreeIntern:
    def __init__(self, max_keys):
        self.max_keys = max_keys
        self.keys = []  # Claves del nodo
        self.children = []  # Punteros a los nodos hijos

    def is_full(self):
        return len(self.keys) >= self.max_keys

    def insert(self, key, child):
        # Inserta la clave y el puntero al hijo en el nodo interno (usando inserción ordenada)
        idx = 0
        while idx < len(self.keys) and self.keys[idx] < key:
            idx += 1
        self.keys.insert(idx, key)
        self.children.insert(idx + 1, child)

    def split(self):
        # Divide el nodo cuando está lleno
        mid = len(self.keys) // 2
        new_node = BPTreeIntern(self.max_keys)
        new_node.keys = self.keys[mid + 1:]
        new_node.children = self.children[mid + 1:]
        self.keys = self.keys[:mid]
        self.children = self.children[:mid + 1]
        return self.keys[-1], new_node  # Devuelve la clave promovida y el nuevo nodo interno

    def __str__(self):
        return f"Intern(keys: {self.keys}, children: {self.children})"
class BPTreeIndexFile:
    def __init__(self, filename, max_keys):
        self.filename = filename
        self.max_keys = max_keys
        self.root = None  # Raíz del árbol B+
        self.load_index()

    def load_index(self):
        # Aquí cargaríamos el índice desde el archivo, o inicializaríamos el árbol
        pass

    def save_index(self):
        # Guardar el índice en el archivo
        pass

    def search(self, key):
        # Búsqueda en el árbol B+ (recorre desde la raíz hasta la hoja)
        node = self.root
        while isinstance(node, BPTreeIntern):
            idx = 0
            while idx < len(node.keys) and node.keys[idx] < key:
                idx += 1
            node = node.children[idx]
        # Aquí recorremos la hoja y devolvemos el resultado
        idx = 0
        while idx < len(node.keys) and node.keys[idx] < key:
            idx += 1
        return node.values[idx] if idx < len(node.keys) and node.keys[idx] == key else None


class BPTree:
    def __init__(self, filename, max_keys):
        self.index_file = BPTreeIndexFile(filename, max_keys)

    def insert(self, key, value):
        node = self.index_file.root
        # Si la raíz está llena, dividirla
        if node is None or node.is_full():
            new_root = BPTreeIntern(self.index_file.max_keys)
            new_root.insert(node.keys[0], node)  # Insertion logic
            self.index_file.root = new_root

        # Recorrer el árbol hasta encontrar la hoja correcta
        while isinstance(node, BPTreeIntern):
            idx = 0
            while idx < len(node.keys) and node.keys[idx] < key:
                idx += 1
            node = node.children[idx]

        # Insertar en la hoja
        node.insert(key, value)
        if node.is_full():
            # Si el nodo hoja está lleno, se divide
            mid_key, new_leaf = node.split()
            parent = node.parent
            parent.insert(mid_key, new_leaf)

    def remove(self, key):
        # Buscar el nodo hoja
        node = self.index_file.root
        while isinstance(node, BPTreeIntern):
            idx = 0
            while idx < len(node.keys) and node.keys[idx] < key:
                idx += 1
            node = node.children[idx]

        # Eliminar el par clave-puntero de la hoja
        idx = 0
        while idx < len(node.keys) and node.keys[idx] < key:
            idx += 1
        if idx < len(node.keys) and node.keys[idx] == key:
            node.keys.pop(idx)
            node.values.pop(idx)
        else:
            return False
        # Aquí manejaríamos las actualizaciones hacia arriba y la fusión o redistribución de nodos
        return True

class DataFile:


    def __init__(self, filename, index_filename):
        self.filename = filename
        self.index_filename = index_filename

        # inicializar archivos si no existen
        if not os.path.exists(self.filename):
            with open(self.filename, "wb") as f:
                f.write(Page().pack())
        if not os.path.exists(self.index_filename):
            index_page = IndexPage()
            index_page.insert(0, 0)
            with open(self.index_filename, "wb") as f:
                f.write(index_page.pack())

    # cargar archivo indice
    def load_index(self):
        with open(self.index_filename, 'rb') as f:
            data = f.read()
            return IndexPage.unpack(data)
    #guardar archivo indice con los nuevos datos
    def save_index(self, index_page: IndexPage):
        print("agregando indice a archivo index")
        with open(self.index_filename, 'wb') as f:
            f.write(index_page.pack())
    #busqueda binaria en el archivo indice  a traves de la key : ID


    def binary_search_index(self, index_page: IndexPage, key: int):
        print("///////////////BUSQUEDA BINARIA  : /////////////////")
        tam_index = index_page.size
        if tam_index == 0:
            print("/////////////// FIN BUSQUEDA BINARIA  : /////////////////")
            return -1

        lista = index_page.keys
        low = 0
        high = tam_index - 1
        floor_index = -1

        while low <= high:
            mid = (low + high) // 2
            if lista[mid] == key:
                floor_index = mid
                print("/////////////// FIN BUSQUEDA BINARIA  : /////////////////")
                break
            elif lista[mid] < key:
                floor_index = mid
                low = mid + 1
            else:
                high = mid - 1

        # Si no hay ningún key <= key, usamos pages[0] (puntero "antes" del primer key)
        if floor_index == -1:
            print("/////////////// FIN BUSQUEDA BINARIA  : /////////////////")
            return index_page.pages[0]
        # pages[ floor_index + 1 ] es el pointer correspondiente a keys[floor_index]
        print("/////////////// FIN BUSQUEDA BINARIA  : /////////////////")
        return index_page.pages[floor_index + 1]
    # no encontrado

    #leer cierta pagina segun el numero
    def read_page(self, page_number: int):
        with open(self.filename, 'rb') as f:
            f.seek(page_number * Page.SIZE_OF_PAGE)
            data = f.read(Page.SIZE_OF_PAGE)
            return Page.unpack(data)
    #escribir en la pagina
    def write_page(self, page_number: int, page: Page):
        with open(self.filename, 'r+b') as f:
            f.seek(page_number * Page.SIZE_OF_PAGE)
            f.write(page.pack())

    def append_page(self, page: Page):
        with open(self.filename, 'ab') as f:
            # Abrimos el archivo en modo append binario
            # Escribimos al final del archivo la nueva página
            f.write(page.pack())

        with open(self.filename, 'rb') as f:
            f.seek(0, 2)  # nos ubicamos al final del archivo
            # f.tell() devuelve la posición actual en bytes (al final del archivo)
            # Dividimos entre el tamaño de una página para saber cuántas páginas hay
            # Restamos 1 para obtener el índice de la última página añadida
            return (f.tell() // Page.SIZE_OF_PAGE) - 1

    def chain(self, page_number: int, next_page: int):
        print("INICIO CHAIN")
        # inicialmente

        page = self.read_page(page_number) # clase Page
        if page.next_page == -1:
            page.next_page = next_page
            self.write_page(page_number, page)
            print("page actual numero:", page_number)
            print("capacidad :  ", len(page.records))
            print("FIN CHAIN")
            return

        # recursivo
        # para insertar una pagina, tenemos que verificar que esa pagina no haya sido llenada antes
        # si la pagina que accedo ya tiene un next, tenemos que ir a ese next
        page_actual_number = page_number
        page_actual = page #clase Page
        while page_actual.next_page != -1 :

            page_next_number = self.read_page(page_actual_number).next_page
            page_actual_number = page_next_number

            page_actual = self.read_page(page_next_number)
        # ya se encontro a un page que tiene espacio.
        page_actual.next_page = next_page
        self.write_page(page_actual_number, page_actual)


        print("FIN CHAIN")





    def insert(self, record: Record):
        print("-------------INICIO INSERCION--------------")
        index_page = self.load_index() # abre archivo indice y traemos  O(1)
        page_number = self.binary_search_index(index_page, record.id) #RAM
        print("insercion deberia ser en el page numero", page_number)
        if page_number == -1:
            print("Insercion falla, numero de pagina = ", page_number)
            return False
        page = self.read_page(page_number) #Leemos pagina especifica de datos O(1)
        if len(page.records) < BLOCK_FACTOR:
            print("Insercion facil, insertamos en page encontrado ( hay espacio)")
            #agregamos en el page y guardamos
            page.records.append(record)
            page.records.sort(key=lambda record: record.id)
            self.write_page(page_number, page)
            print("insercion correcta en page numero, ", page_number)
            print("capacidad actual : ", len(page.records))
            print("-------------Fin INSERCION---------------")


        elif len(page.records)== BLOCK_FACTOR and index_page.size < IndexPage.m:
            print("Insercion intermedia, aun hay espacio en index, se divide el page en dos")
            # si el tamaño del page que se debe agregar ya esta lleno y aun hay espacio en en el indexpage
            record_ext = page.records
            record_ext.append(record)
            record_ext.sort(key=lambda record: record.id)
            list_left = record_ext[:len(record_ext)//2] #lista de records
            list_right = record_ext[len(record_ext)//2:] #lista de records
            page1 = Page(list_left)
            page_new = Page(list_right)

            size1 = len(page1.records)

            size2 = len(page_new.records)

            #abrimos pages e insertamos el page1 donde era originalmente
            self.write_page(page_number, page1) #escribimos pagina en datos O(1)
            #agregamos la pagina al final y recuperamos numero de pagina insertada
            new_page_numer  = self.append_page(page_new)
            #tenemos que introducir nuevo indice por ejemplo [6 89]
            #si nuevo indice = 13
            #binarysearch me da 1
            #=> leer y escribir , coloco y ordeno
            with open( self.index_filename, 'rb+') as indexf: #un solo buffer O(1)
                indexf.seek(0,0)
                indexPage = IndexPage.unpack(indexf.read())
                indexPage.insert(list_right[0].id, new_page_numer)
                self.save_index(indexPage)
                # insertamos una nueva key y un numero de pagina a la lista de keys y de pages
            print("se spliteo \n page_a", page_number, "capacidad: ", size1,"\n"
                "page b", new_page_numer, "capacidad: ", size2,"\n")
            print("-------------Fin INSERCION---------------")

        # ya no tenemos espacio en el index
        #encadenamos
        # verificar si hay espacio en el next, sino no es necesario crear otra pagina
        else:
            print("Insercion dificil, se alcanzo el limite de indices")
            if page.next_page == -1:

                #el bucle termino porque aun no hay creada una pagina y todos los next estan llens
                page_new_chain = Page([record])
                page_new_number = self.append_page(page_new_chain)
                print("encadenando page numero : ", page_number, " con page numero: ", page_new_number )
                # encadenamiento
                self.chain(page_number, page_new_number)
                print("se inserto correctamente en page :", page_new_number)
                print("capacidad actual del next: ", len(page_new_chain.records))
                print("-------------Fin INSERCION---------------")
                return True
            prev_number = page_number
            curr_number = page.next_page
            nextPage = self.read_page(page.next_page)
            currPage = nextPage #nos dirigimos al siguiente de page
            # avanzar mientras esté lleno y tenga otro next
            while len(currPage.records) == BLOCK_FACTOR and currPage.next_page != -1:
                prev_number = curr_number
                curr_number = currPage.next_page
                currPage = self.read_page(curr_number)

            # caso 1: encontramos página con espacio
            if len(currPage.records) < BLOCK_FACTOR:
                print("numero de next page encontrado : ", curr_number)
                print("capacidad del nextpage encontrado: ", len(currPage.records))
                currPage.records.append(record)
                currPage.records.sort(key=lambda record: record.id)
                self.write_page(curr_number, currPage)
                print("se inserto correctamente en page :", curr_number)
                print("capacidad actual del next: ", len(currPage.records))
                print("-------------Fin INSERCION---------------")
            else:
                # caso 2: última página llena y sin next → creamos nueva
                page_new_chain = Page([record])
                page_new_number = self.append_page(page_new_chain)
                self.chain(curr_number, page_new_number)
                print("se inserto correctamente en nueva page :", page_new_number)
                print("capacidad actual del next: ", len(page_new_chain.records))
                print("-------------Fin INSERCION---------------")

    def search(self, key: int):
        indexPage = self.load_index()
        # 1. Buscar en el índice qué página corresponde
        idx_page = self.binary_search_index(indexPage, key)
        page_number = idx_page

        # 2. Recorremos la página principal y, si no está, seguimos por el chain
        while page_number != -1:
            print(f"Buscando en página {page_number}")
            page = self.read_page(page_number)

            # 3. Búsqueda lineal dentro de la página
            for record in page.records:
                if record.id == key:
                    return record  # encontrado

            # 4. Pasar a la siguiente página encadenada
            page_number = page.next_page

        # 5. No se encontró
        return None

    def remove(self, key: int):
        print("\n------ INICIO REMOVE ------")

        index_page = self.load_index()
        page_number = self.binary_search_index(index_page, key)

        prev_number = None
        current_number = page_number

        while current_number != -1:
            page = self.read_page(current_number)
            new_records = [r for r in page.records if r.id != key]

            if len(new_records) < len(page.records):
                # si se Se eliminó
                page.records = new_records
                self.write_page(current_number, page)


                #DESENCADENAMIENTO
                # # Si la página quedó vacía y ya avanzamos a otro nivel de chain
                if len(page.records) == 0 and current_number != page_number:
                     # es overflow, desencadenar
                     if prev_number is not None:
                         prev_page = self.read_page(prev_number)
                         prev_page.next_page = page.next_page
                         self.write_page(prev_number, prev_page)
                         print(f"Se actualizó página {prev_number} para apuntar a {page.next_page}")
                print("------ FIN REMOVE ------")
                return True

            prev_number = current_number
            current_number = page.next_page
        print(f"Registro {key} no encontrado en ninguna página de la cadena")
        print("------ FIN REMOVE ------")
        return False

    def scanAll(self):
        with open(self.filename, 'rb') as file:
            file.seek(0, 2)
            num_pages = file.tell() // Page.SIZE_OF_PAGE
            file.seek(0)
            for i in range(num_pages):
                page_data = file.read(Page.SIZE_OF_PAGE)
                page = Page.unpack(page_data)
                print("#Page", i )
                print("#next_page ", page.next_page)
                for record in page.records:
                    print(record)

    def load(self, csv):
        with open(csv, 'r',encoding='utf-8') as file:
            next(file)
            count = 1

            for linea in file:
                linea = linea.rstrip('\n')
                list_linea = linea.split(';')# eliminar salto de línea al final
                  # convertir la línea en lista de caracteres
                id = int(list_linea[0])
                nombre = list_linea[1]
                cantidad = int(list_linea[2])
                precio = float(list_linea[3])
                fecha = list_linea[4]

                record = Record(id, nombre, cantidad, precio, fecha)
                self.insert(record)
                if (count < 10): count = count + 1
                else: break







db = DataFile("data.dat", "index.dat")
print("Tamaño de record:", Record.SIZE_OF_RECORD)
print("Block factor:", BLOCK_FACTOR)
print("Header size:", Page.HEADER_SIZE)
print("Tamaño de página:", Page.SIZE_OF_PAGE)
db.load("sales_dataset_unsorted (1).csv")
print("////////////////// ESCANEO ///////////////")
db.scanAll()
print("////////////////// FIN ESCANEO ///////////////")

print("////////////////// CHAIN  ///////////////")
result = db.read_page(3)
print(result.next_page)

#comprobacion de chain
print("//////////////////  FIN CHAIN  ///////////////")

print("////////////////// BUSQUEDA   ///////////////")
result = db.search(614)
if result:
    print(result.id, result.producto, result.cantidad, result.precio, result.fecha)
else:
    print("no encontrado")
print("////////////////// FIN BUSQUEDA   ///////////////")
print("///////////////// ELIMINACION   ///////////////")
isRemoved = db.remove(681)
print("confirmacion de eliminacion, " , isRemoved)
db.scanAll()
db.insert(Record(405, "Tablet", 5, 750.0, "10/08/2024"))
db.scanAll()
