"""B+ tree index implementation.

This module provides an on-disk B+ tree index (classes `BPlusNode` and
`BPlusTree`). The file previously contained a demo `Record` type and
simple `DataFile`/`IndexedFile` helpers for CSV demos; those have been
removed so this module is index-only. Indexes in this project are
expected to store keys -> pointers (offsets) into table data files.
"""

import struct
import os
import bisect
import re

ORDER = 500
MIN_KEYS = ORDER // 2

class BPlusNode:
    HEADER_FORMAT = 'BBiii'  # node_type 1 , is_root 1 , num_keys 4, parent_ptr 4, next_leaf 4 
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    KEY_PTR_FORMAT = 'ii'  # (key, pointer)
    KEY_PTR_SIZE = struct.calcsize(KEY_PTR_FORMAT)
    SIZE_OF_NODE = HEADER_SIZE + ORDER *4 + (ORDER + 1) * 4  # ORDER claves + ORDER+1 punteros

    def __init__(self, node_type=1, is_root=0, num_keys=0, parent_ptr=-1, next_leaf=-1):
        self.node_type = node_type      # 0 = interno, 1 = hoja
        self.is_root = is_root          # 1 = raíz, 0 = no raíz
        self.num_keys = num_keys        # cantidad de claves almacenadas
        self.parent_ptr = parent_ptr    # offset del padre
        self.next_leaf = next_leaf

        self.keys = []                  # lista de claves (enteros)
        self.pointers = []

    def pack_header(self):
        return struct.pack(
            self.HEADER_FORMAT,
            self.node_type,
            self.is_root,
            self.num_keys,
            self.parent_ptr,
            self.next_leaf
        )
    
    @staticmethod
    def unpack_header(data):
        node_type, is_root, num_keys, parent_ptr, next_leaf = struct.unpack(
            BPlusNode.HEADER_FORMAT, data)
        return BPlusNode(node_type, is_root, num_keys, parent_ptr, next_leaf)
    

    def pack(self):
        header_data = self.pack_header()
        body_data = b''
        
        # Tamaño máximo del cuerpo (basado en el nodo interno)
        MAX_BODY_SIZE = ORDER * 4 + (ORDER + 1) * 4

        if self.node_type == 0:  # nodo interno
            # Guardar claves
            for i in range(self.num_keys):
                body_data += struct.pack('i', self.keys[i])
            for i in range(self.num_keys, ORDER):
                body_data += b'\x00' * 4
            # Guardar punteros (son num_keys + 1)
            for i in range(self.num_keys + 1):
                body_data += struct.pack('i', self.pointers[i])
            for i in range(self.num_keys + 1, ORDER + 1):
                body_data += b'\x00' * 4
        else:  # nodo hoja
            # En hojas, claves y punteros son paralelos
            for i in range(self.num_keys):
                body_data += struct.pack(self.KEY_PTR_FORMAT, self.keys[i], self.pointers[i])
            
            # Relleno para los pares (key, ptr) no utilizados
            current_body_size = self.num_keys * self.KEY_PTR_SIZE
            padding_size = MAX_BODY_SIZE - current_body_size
            
            # Asegurarse de que el padding nunca sea negativo si el nodo está sobrecargado temporalmente
            if padding_size > 0:
                body_data += b'\x00' * padding_size

        # Truncar por si acaso durante un split el nodo se desborda temporalmente
        return header_data + body_data[:MAX_BODY_SIZE]

    @staticmethod
    def unpack(data):
        header = data[:BPlusNode.HEADER_SIZE]
        node = BPlusNode.unpack_header(header)
        body = data[BPlusNode.HEADER_SIZE:]
        
        node.keys = []
        node.pointers = []
        offset = 0
        
        if node.node_type == 0:  # nodo interno
            # Leer claves
            for _ in range(node.num_keys):
                key, = struct.unpack('i', body[offset:offset + 4])
                node.keys.append(key)
                offset += 4
            # Leer punteros (num_keys + 1)
            offset += (ORDER - node.num_keys) * 4
            for _ in range(node.num_keys + 1):
                ptr, = struct.unpack('i', body[offset:offset + 4])
                node.pointers.append(ptr)
                offset += 4
        else:  # nodo hoja
            offset = 0
            for _ in range(node.num_keys):
                key, ptr = struct.unpack("ii",body[offset:offset + 8])
                node.keys.append(key)
                node.pointers.append(ptr)
                offset += 8
        
        return node

class BPlusTree:
    FORMAT = 'ii'  # root_ptr, total_nodes
    SIZE = struct.calcsize(FORMAT)
    NODE_SIZE = BPlusNode.SIZE_OF_NODE
    

    def __init__(self, filename:str):
        self.filename = filename
        # Crear archivo si no existe
        # Crear archivo si no existe
        if not os.path.exists(filename):
            with open(filename, 'wb') as f:
                 #Header inicial
                root_ptr = self.SIZE  # La raíz empieza justo después del header
                total_nodes = 1
                header_data = struct.pack(self.FORMAT, root_ptr, total_nodes)
                f.write(header_data)

                # 2 Nodo raíz vacío
                root = BPlusNode(node_type=1, is_root=1)
                root.keys = []
                root.pointers = []
                root.num_keys = 0
                f.write(root.pack())

    
    def read_header(self):
        with open(self.filename, 'r+b') as f:
            f.seek(0)
            data = f.read(self.SIZE)
            root_ptr, total_nodes = struct.unpack(self.FORMAT, data)
            return root_ptr, total_nodes
    
    def write_header(self, root_ptr:int=None, total_nodes:int=None):
        curr_root, curr_total = self.read_header()
        if root_ptr is None:
            root_ptr = curr_root
        else:
            root_ptr = root_ptr

        if total_nodes is None:
            total_nodes = curr_total
        else:
            total_nodes = total_nodes
        with open(self.filename, 'r+b') as f:
            f.seek(0)
            f.write(struct.pack(self.FORMAT, root_ptr, total_nodes))
    

        # --- Leer nodo desde archivo ---
    def read_node(self, offset:int):
        with open(self.filename, 'r+b') as f:
            f.seek(offset)

            data = f.read(self.NODE_SIZE)
            return BPlusNode.unpack(data)
            
    # --- Escribir nodo al archivo ---
    def write_node(self, node, offset:int):
        with open(self.filename, 'r+b') as f:
            # Extender el archivo si el offset está más allá del tamaño actual
            f.seek(0, 2)  # Ir al final
            current_size = f.tell()
            if offset + self.NODE_SIZE > current_size:
                # Rellenar con zeros hasta el nuevo tamaño
                f.write(b'\x00' * (offset + self.NODE_SIZE - current_size))
            
            f.seek(offset)
            f.write(node.pack())

    def binary_intern(self,node,key):
        # comparator-aware binary search (bisect_right equivalent)
        l, r = 0, node.num_keys - 1
        ans = node.num_keys
        while l <= r:
            m = (l + r) // 2
            if self._cmp(node.keys[m], key) <= 0:
                l = m + 1
            else:
                ans = m
                r = m - 1
        return min(ans, len(node.pointers) - 1)
    def binary_leaf(self,node, key):
        left, right = 0, node.num_keys - 1
        while left <= right:
            mid = (left + right) // 2
            cmpv = self._cmp(node.keys[mid], key)
            if cmpv == 0:
                return mid
            elif cmpv > 0:
                right = mid - 1
            else:
                left = mid + 1
        return -1

    def _looks_numeric(self, x):
        return isinstance(x, (int, float)) or (isinstance(x, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", x.strip()))

    def _cmp(self, a, b):
        # None ordering
        if a is None and b is None:
            return 0
        if a is None:
            return -1
        if b is None:
            return 1

        # numeric native
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return (a > b) - (a < b)

        # numeric-looking strings
        try:
            if self._looks_numeric(a) and self._looks_numeric(b):
                fa = float(str(a))
                fb = float(str(b))
                return (fa > fb) - (fa < fb)
        except Exception:
            pass

        sa = str(a)
        sb = str(b)
        if sa == sb:
            return 0
        return 1 if sa > sb else -1
    
    def search(self, key):

        root_ptr, _ = self.read_header()
        node = self.read_node(root_ptr)

        while node.node_type == 0:  # nodo interno

            i = self.binary_intern(node, key)
            child_ptr = node.pointers[i]
            node = self.read_node(child_ptr)

        # Nodo hoja                   
        idx = self.binary_leaf(node,key)
        if idx != -1:
            return node.pointers[idx]
        return None
    def find(self, key):
        """Return a list of pointers (offsets) for all entries matching key (support duplicates)."""
        root_ptr, _ = self.read_header()
        node = self.read_node(root_ptr)

        while node.node_type == 0:
            i = self.binary_intern(node, key)
            child_ptr = node.pointers[i]
            node = self.read_node(child_ptr)

        # node is leaf
        # find any index with the key
        i = self.binary_leaf(node, key)
        if i == -1:
            return []

        # collect equals to the left and right
        results = []
        # scan left
        j = i
        while j >= 0 and self._cmp(node.keys[j], key) == 0:
            results.append(node.pointers[j])
            j -= 1
        # scan right
        j = i + 1
        while j < node.num_keys and self._cmp(node.keys[j], key) == 0:
            results.append(node.pointers[j])
            j += 1

        # it's possible duplicates continue in next leaf(s)
        next_leaf_ptr = node.next_leaf
        while next_leaf_ptr != -1:
            next_node = self.read_node(next_leaf_ptr)
            stop = False
            for k, pk in zip(next_node.keys, next_node.pointers):
                if self._cmp(k, key) == 0:
                    results.append(pk)
                else:
                    # keys are sorted; if greater, we can stop scanning further leaves
                    if self._cmp(k, key) > 0:
                        stop = True
                        break
            if stop:
                break
            next_leaf_ptr = next_node.next_leaf

        return results

    def range_search(self, begin_key, end_key):
        """Return list of pointers whose keys are between begin_key and end_key inclusive."""
        if begin_key is None or end_key is None:
            return []
        if begin_key > end_key:
            begin_key, end_key = end_key, begin_key

        # find starting leaf and index: traverse to leaf using binary_intern but choosing lower_bound
        root_ptr, _ = self.read_header()
        node = self.read_node(root_ptr)
        while node.node_type == 0:
            # use comparator-aware binary search to find child pointer for begin_key
            try:
                i = self.binary_intern(node, begin_key)
            except Exception:
                # fallback to safe bounds
                i = 0 if not node.pointers else min(len(node.pointers) - 1, 0)
            child_ptr = node.pointers[i]
            node = self.read_node(child_ptr)

        # now at leaf, scan keys across leaf chain
        results = []
        cur = node
        while True:
            for k, p in zip(cur.keys, cur.pointers):
                if self._cmp(k, begin_key) < 0:
                    continue
                if self._cmp(k, end_key) > 0:
                    return results
                results.append(p)
            if cur.next_leaf == -1:
                break
            cur = self.read_node(cur.next_leaf)

        return results

    def add(self, key, pointer):
        """Compatibility alias used by SchemaManager.insert (index.add)."""
        try:
            # try convert numeric-like strings to int for stable ordering
            if isinstance(key, str) and key.isdigit():
                key = int(key)
        except Exception:
            pass
        return self.insert(key, pointer)
    def insert(self, key, pointer):
        root_ptr, _ = self.read_header()

        # Llamada recursiva al método interno
        # normalize key if numeric-like string
        try:
            if isinstance(key, str) and re.fullmatch(r"\d+", key):
                key = int(key)
        except Exception:
            pass
        result = self.insert_recursive(key, pointer, root_ptr)

        # Si hubo split que llegó hasta la raíz
        if result is not None:
            promoted_key, new_child_ptr = result

            # Crear nueva raíz
            old_root_ptr = root_ptr
            new_root = BPlusNode(node_type=0, is_root=1)
            new_root.keys = [promoted_key]
            new_root.pointers = [old_root_ptr, new_child_ptr]
            new_root.num_keys = 1

            # CAMBIO: Calcular offset manualmente y escribir directamente
            _, total_nodes = self.read_header()
            new_root_ptr = self.SIZE + total_nodes * BPlusNode.SIZE_OF_NODE
            with open(self.filename, 'r+b') as f:
                f.seek(new_root_ptr)
                f.write(new_root.pack())
            # Actualizar header
            self.write_header(root_ptr=new_root_ptr, total_nodes=total_nodes + 1)

    # VERIFICAR KEY TIPO INT
    def insert_in_leaf(self, node: BPlusNode, key: int, pointer: int):
        # find leftmost index where node.keys[i] >= key using comparator
        left, right = 0, node.num_keys
        while left < right:
            mid = (left + right) // 2
            if self._cmp(node.keys[mid], key) < 0:
                left = mid + 1
            else:
                right = mid
        i = left
        node.keys.insert(i, key)
        node.pointers.insert(i, pointer)
        node.num_keys += 1
    def insert_in_internal(self, node: BPlusNode, key: int, pointer: int):
        # find leftmost index where node.keys[i] >= key
        left, right = 0, node.num_keys
        while left < right:
            mid = (left + right) // 2
            if self._cmp(node.keys[mid], key) < 0:
                left = mid + 1
            else:
                right = mid
        i = left
        node.keys.insert(i, key)
        node.pointers.insert(i + 1, pointer)
        node.num_keys += 1
    def insert_recursive(self, key, pointer, node_ptr):
        node = self.read_node(node_ptr)

        if node.node_type == 1:  # hoja
            self.insert_in_leaf(node, key, pointer)
            self.write_node(node, node_ptr)
            if node.num_keys > ORDER:
                return self.split_leaf(node, node_ptr)
            return None
            
        else:  # nodo interno
            child_idx = self.binary_intern(node, key)
            child_ptr = node.pointers[child_idx]
            result = self.insert_recursive(key, pointer, child_ptr)

            if result is not None:
                promoted_key, new_child_ptr = result
                self.insert_in_internal(node, promoted_key, new_child_ptr)
                
                if node.num_keys > ORDER:  # ← Esto DEBE dispararse cuando num_keys = 4
                    self.write_node(node, node_ptr)
                    return self.split_internal(node, node_ptr)
                else:
                    self.write_node(node, node_ptr)
            
            return None
    def split_leaf(self, node: BPlusNode, node_ptr: int):
        """
        Divide un nodo hoja en dos. 
        Devuelve (promoted_key, new_node_ptr) para el nodo padre.
        """
        mid = node.num_keys // 2  # índice de división
        
        # Reservar espacio para el nuevo nodo PRIMERO
        new_node_ptr = self.allocate_node(node_type=1)
        
        # Crear nuevo nodo hoja
        new_node = BPlusNode(node_type=1, is_root=0)
        new_node.keys = node.keys[mid:]
        new_node.pointers = node.pointers[mid:]
        new_node.num_keys = len(new_node.keys)
        new_node.next_leaf = node.next_leaf

        # Actualizar nodo original
        node.keys = node.keys[:mid]
        node.pointers = node.pointers[:mid]
        node.num_keys = len(node.keys)
        node.next_leaf = new_node_ptr  # offset del nuevo nodo

        # Escribir nodos en archivo
        self.write_node(node, node_ptr)
        self.write_node(new_node, new_node_ptr)
        
        # Promover la primera clave del nuevo nodo
        promoted_key = new_node.keys[0]
        return promoted_key, new_node_ptr
    
    def split_internal(self, node: BPlusNode, node_ptr: int):
        """
        Divide un nodo interno en dos. 
        Devuelve (promoted_key, new_node_ptr) para el nodo padre.
        """
        mid = node.num_keys // 2  # índice de clave a promover
        promoted_key = node.keys[mid]

        # Reservar espacio para el nuevo nodo PRIMERO
        new_node_ptr = self.allocate_node(node_type=0)

        # Crear nuevo nodo interno
        new_node = BPlusNode(node_type=0, is_root=0)
        new_node.keys = node.keys[mid+1:]  # claves a la derecha de la promovida
        new_node.pointers = node.pointers[mid+1:]
        new_node.num_keys = len(new_node.keys)

        # Actualizar nodo original
        node.keys = node.keys[:mid]
        node.pointers = node.pointers[:mid+1]
        node.num_keys = len(node.keys)

        # Escribir nodos en archivo
        self.write_node(node, node_ptr)
        self.write_node(new_node, new_node_ptr)

        return promoted_key, new_node_ptr
    def allocate_node(self, node_type=1):
        """
        Reserva espacio para un nuevo nodo y lo inicializa vacío en disco
        """
        _, total_nodes = self.read_header()
        new_offset = self.SIZE + total_nodes * BPlusNode.SIZE_OF_NODE
        
        # Crear un nodo vacío y escribirlo (esto asegura que el espacio existe)
        empty_node = BPlusNode(node_type=node_type, is_root=0)
        empty_node.keys = []
        empty_node.pointers = []
        empty_node.num_keys = 0
        if node_type == 0:  # interno
            empty_node.pointers = [-1]  # Al menos un puntero dummy
        else:  # hoja
            empty_node.pointers = []
        # IMPORTANTE: Escribir el nodo vacío en el nuevo offset
        with open(self.filename, 'r+b') as f:
        # Extender el archivo si es necesario
            f.seek(0, 2)  # Ir al final
            current_size = f.tell()
            if new_offset + self.NODE_SIZE > current_size:
                # Rellenar con zeros hasta el offset deseado
                f.write(b'\x00' * (new_offset - current_size))
            
            # Ahora escribir el nodo vacío
            f.seek(new_offset)
            f.write(empty_node.pack())
        # Actualizamos el header con un nodo más
        self.write_header(total_nodes=total_nodes + 1)
        return new_offset
   
    
    def delete(self, key):
        root_ptr, _ = self.read_header()
        self.delete_recursive(key, root_ptr)

        # Actualizar raíz si quedó vacía
        root = self.read_node(root_ptr)
        if root.num_keys == 0 and root.node_type == 0:
            new_root_ptr = root.pointers[0]
            self.write_header(root_ptr=new_root_ptr)
    def remove_from_leaf(self, node: BPlusNode, key: int):
        """
        Elimina una clave y su puntero de un nodo hoja.
        """
        i = self.binary_leaf(node, key)
        if i == -1:
            return False  # no existe la clave
        del node.keys[i]
        del node.pointers[i]
        node.num_keys -= 1
        return True
    def delete_recursive(self, key, node_ptr, parent_ptr=None, index_in_parent=None):
        node = self.read_node(node_ptr)

        if node.node_type == 1:  # nodo hoja
            removed = self.remove_from_leaf(node, key)
            if not removed:
                return False  # clave no encontrada

            self.write_node(node, node_ptr)

            # Revisar underflow
            if node.num_keys < MIN_KEYS and parent_ptr is not None:
                self.handle_underflow_leaf(node_ptr, parent_ptr, index_in_parent)

            return True

        else:  # nodo interno
            # Encontrar el hijo correspondiente
            child_idx = self.binary_intern(node, key)
            child_ptr = node.pointers[child_idx]

            # Recursivamente eliminar en el hijo
            deleted = self.delete_recursive(key, child_ptr, node_ptr, child_idx)
            if not deleted:
                return False

            # Revisar underflow en nodo interno
            node = self.read_node(node_ptr)
            if node.num_keys < MIN_KEYS and parent_ptr is not None:
                self.handle_underflow_internal(node_ptr, parent_ptr, index_in_parent)

            return True
    def handle_underflow_leaf(self, node_ptr, parent_ptr, index_in_parent):
        node = self.read_node(node_ptr)
        parent = self.read_node(parent_ptr)

        # Intentar redistribuir con hermano izquierdo
        if index_in_parent > 0:
            left_sibling_ptr = parent.pointers[index_in_parent - 1]
            left_sibling = self.read_node(left_sibling_ptr)

            if left_sibling.num_keys > MIN_KEYS:
                # Mover la última clave del hermano izquierdo al principio del nodo
                key_to_move = left_sibling.keys.pop(-1)
                pointer_to_move = left_sibling.pointers.pop(-1)
                left_sibling.num_keys -= 1

                node.keys.insert(0, key_to_move)
                node.pointers.insert(0, pointer_to_move)
                node.num_keys += 1

                # Actualizar la clave correspondiente en el padre
                parent.keys[index_in_parent - 1] = node.keys[0]

                self.write_node(left_sibling, left_sibling_ptr)
                self.write_node(node, node_ptr)
                self.write_node(parent, parent_ptr)
                return

        # Intentar redistribuir con hermano derecho
        if index_in_parent < len(parent.pointers) - 1:
            right_sibling_ptr = parent.pointers[index_in_parent + 1]
            right_sibling = self.read_node(right_sibling_ptr)

            if right_sibling.num_keys > MIN_KEYS:
                # Mover la primera clave del hermano derecho al final del nodo
                key_to_move = right_sibling.keys.pop(0)
                pointer_to_move = right_sibling.pointers.pop(0)
                right_sibling.num_keys -= 1

                node.keys.append(key_to_move)
                node.pointers.append(pointer_to_move)
                node.num_keys += 1

                # Actualizar la clave correspondiente en el padre
                parent.keys[index_in_parent] = right_sibling.keys[0]

                self.write_node(right_sibling, right_sibling_ptr)
                self.write_node(node, node_ptr)
                self.write_node(parent, parent_ptr)
                return

        # Si no se puede redistribuir, hacer merge (fusión) con un hermano
        if index_in_parent > 0:
            # Fusionar con hermano izquierdo
            left_sibling_ptr = parent.pointers[index_in_parent - 1]
            left_sibling = self.read_node(left_sibling_ptr)

            left_sibling.keys.extend(node.keys)
            left_sibling.pointers.extend(node.pointers)
            left_sibling.num_keys = len(left_sibling.keys)
            left_sibling.next_leaf = node.next_leaf

            self.write_node(left_sibling, left_sibling_ptr)
            self.remove_from_internal(parent, index_in_parent)
            self.write_node(parent, parent_ptr)

        else:
            # Fusionar con hermano derecho
            right_sibling_ptr = parent.pointers[index_in_parent + 1]
            right_sibling = self.read_node(right_sibling_ptr)

            node.keys.extend(right_sibling.keys)
            node.pointers.extend(right_sibling.pointers)
            node.num_keys = len(node.keys)
            node.next_leaf = right_sibling.next_leaf

            self.write_node(node, node_ptr)
            self.remove_from_internal(parent, index_in_parent)
            self.write_node(parent, parent_ptr)

    def handle_underflow_internal(self, node_ptr, parent_ptr, index_in_parent):
        node = self.read_node(node_ptr)
        parent = self.read_node(parent_ptr)

        # Intentar redistribuir con hermano izquierdo
        if index_in_parent > 0:
            left_sibling_ptr = parent.pointers[index_in_parent - 1]
            left_sibling = self.read_node(left_sibling_ptr)

            if left_sibling.num_keys > MIN_KEYS:
                # Mover la última clave del hermano izquierdo y el puntero correspondiente
                borrowed_key = left_sibling.keys.pop(-1)
                borrowed_pointer = left_sibling.pointers.pop(-1)
                left_sibling.num_keys -= 1

                # La clave del padre entre los dos nodos baja al nodo actual
                node.keys.insert(0, parent.keys[index_in_parent - 1])
                node.pointers.insert(0, borrowed_pointer)
                node.num_keys += 1

                # Actualizar clave del padre con la que se movió del hermano
                parent.keys[index_in_parent - 1] = borrowed_key

                self.write_node(left_sibling, left_sibling_ptr)
                self.write_node(node, node_ptr)
                self.write_node(parent, parent_ptr)
                return

        # Intentar redistribuir con hermano derecho
        if index_in_parent < len(parent.pointers) - 1:
            right_sibling_ptr = parent.pointers[index_in_parent + 1]
            right_sibling = self.read_node(right_sibling_ptr)

            if right_sibling.num_keys > MIN_KEYS:
                # Mover la primera clave del hermano derecho y el puntero correspondiente
                borrowed_key = right_sibling.keys.pop(0)
                borrowed_pointer = right_sibling.pointers.pop(0)
                right_sibling.num_keys -= 1

                # La clave del padre baja al final del nodo actual
                node.keys.append(parent.keys[index_in_parent])
                node.pointers.append(borrowed_pointer)
                node.num_keys += 1

                # Actualizar clave del padre con la que se movió del hermano derecho
                parent.keys[index_in_parent] = borrowed_key

                self.write_node(right_sibling, right_sibling_ptr)
                self.write_node(node, node_ptr)
                self.write_node(parent, parent_ptr)
                return

        # Si no se puede redistribuir, hacer merge
        if index_in_parent > 0:
            # Fusionar con hermano izquierdo
            left_sibling_ptr = parent.pointers[index_in_parent - 1]
            left_sibling = self.read_node(left_sibling_ptr)

            # La clave del padre que separa los nodos baja al hermano izquierdo
            left_sibling.keys.append(parent.keys[index_in_parent - 1])
            left_sibling.keys.extend(node.keys)
            left_sibling.pointers.extend(node.pointers)
            left_sibling.num_keys = len(left_sibling.keys)

            self.write_node(left_sibling, left_sibling_ptr)
            self.remove_from_internal(parent, index_in_parent)
            self.write_node(parent, parent_ptr)

        else:
            # Fusionar con hermano derecho
            right_sibling_ptr = parent.pointers[index_in_parent + 1]
            right_sibling = self.read_node(right_sibling_ptr)

            # La clave del padre que separa los nodos baja al nodo actual
            node.keys.append(parent.keys[index_in_parent])
            node.keys.extend(right_sibling.keys)
            node.pointers.extend(right_sibling.pointers)
            node.num_keys = len(node.keys)

            self.write_node(node, node_ptr)
            self.remove_from_internal(parent, index_in_parent)
            self.write_node(parent, parent_ptr)
    def remove_from_internal(self, node: BPlusNode, index: int):
        """
        Elimina la clave y el puntero hijo de un nodo interno en la posición index.
        """
        del node.keys[index]
        del node.pointers[index + 1]
        node.num_keys -= 1

    def print_simple(self):
        """
        Imprime el árbol B+ en forma simplificada, mostrando claves por nivel.
        """
        root_ptr, total_nodes = self.read_header()
        print(f"\n[HEADER] root_ptr={root_ptr}, total_nodes={total_nodes}")
        
        if root_ptr == -1:
            print("Árbol vacío.")
            return

        queue = [(root_ptr, 0)]
        levels = {}

        while queue:
            node_ptr, level = queue.pop(0)
            node = self.read_node(node_ptr)
            
            print(f"[NODE] offset={node_ptr}, level={level}, type={'LEAF' if node.node_type else 'INTERNAL'}, keys={node.keys}, pointers={node.pointers}")

            # Guardar las claves del nodo
            if level not in levels:
                levels[level] = []
            levels[level].append(node.keys)

            # Si es interno, añadir hijos a la cola
            if node.node_type == 0:
                for ptr in node.pointers:
                    queue.append((ptr, level + 1))

        # Imprimir niveles
        print("\nEstructura simplificada del B+ Tree:\n")
        for lvl in sorted(levels.keys()):
            keys_str = " | ".join(str(k) for k in levels[lvl])
            print(f"Nivel {lvl}: {keys_str}")
    print()
