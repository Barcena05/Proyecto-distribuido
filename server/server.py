import socket
import threading
import time
import hashlib
import os
from base64 import b64encode, b64decode
import struct 
import json

# Constantes
PUERTO_DE_BROADCAST = 50000 
IP_DEL_SERVIDOR = socket.gethostbyname(socket.gethostname())
DIRECCION_DE_BROADCAST = '<broadcast>' 

GRUPO_DE_MULTICAST = '224.0.0.1'
PUERTO_DE_MULTICAST = 10000

ENCONTRAR_SUCESOR = 1
ENCONTRAR_PREDECESOR = 2
OBTENER_SUCESOR = 3
OBTENER_PREDECESOR = 4
NOTIFICAR = 5
DEDO_MAS_CERCANO = 6
IS_ALIVE = 7
NOTIFICAR1 = 8
ALMACENAR_LLAVE = 9
SUBIR_ARCHIVO = 10
BUSCAR_ARCHIVO = 11
DESCARGAR_ARCHIVO = 12
ALMACENAR_REPLICA = 13


def calcular_hash(file_content):
    return hashlib.sha256(file_content).hexdigest()

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(),16)

class Referencia:
    def __init__(self, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    def _enviar_datos(self, op: int, data: str = None) -> bytes:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))
                s.sendall(f'{op},{data}'.encode('utf-8'))
                return s.recv(1024)
        except Exception as e:
            print(f"Se ha producido el siguiente error: {e} durante la operacion: {op} ")
            return b''
        
    def encontrar_sucesor(self, id: int) -> 'Referencia':
        response = self._enviar_datos(ENCONTRAR_SUCESOR, str(id)).decode().split(',')
        return Referencia(response[1], self.port)

    def encontrar_predecesor(self, id: int) -> 'Referencia':
        response = self._enviar_datos(ENCONTRAR_PREDECESOR, str(id)).decode().split(',')
        return Referencia(response[1], self.port)

    @property
    def succ(self) -> 'Referencia':
        response = self._enviar_datos(OBTENER_SUCESOR).decode().split(',')
        return Referencia(response[1], self.port)

    @property
    def pred(self) -> 'Referencia':
        response = self._enviar_datos(OBTENER_PREDECESOR).decode().split(',')
        return Referencia(response[1], self.port)

    def notificar(self, node: 'Referencia'):
        self._enviar_datos(NOTIFICAR, f'{node.id},{node.ip}')

    def notificar1(self, node: 'Referencia'):
        self._enviar_datos(NOTIFICAR1, f'{node.id},{node.ip}')

    def dedo_mas_cercano(self, id: int) -> 'Referencia':
        response = self._enviar_datos(DEDO_MAS_CERCANO, str(id)).decode().split(',')
        return Referencia(response[1], self.port)

    def verificar(self):
        response = self._enviar_datos(IS_ALIVE).decode().split(',')
        return response
    
    def almacenar_llave(self, key: str, value: str):
        self._enviar_datos(ALMACENAR_LLAVE, f'{key},{value}')

    def almacenar_en_replicas(self,obj):
        try:
            s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((self.ip, self.port))
            s.send(f"{13},{obj['name']},{obj['type']},{len(obj['content'])},{','.join(obj['nodes'])}".encode())
            ready = s.recv(1024).decode()
            if ready == 'READY':
                print("ENVIANDO")
                for i in range(0, len(obj["content"]), 1024000):
                    chunk = obj["content"][i:i+1024000]
                    s.send(chunk)
            s.close()
            return  "ok"
        except:
            return "error"

    
    def almacenar_archivo(self, file_name, file_type, file_content, file_size):
        try:
            s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((self.ip, self.port))
            s.send(f"{10},{file_name},{file_type},{file_size}".encode())
            ready = s.recv(1024).decode()
            if ready == 'READY':
                for i in range(0, len(file_content), 1024000):
                    chunk = file_content[i:i+1024000]
                    s.send(chunk)
            response = s.recv(1024)
            s.close()
        except:
            response = "ERROR".encode()
        return response

    def __str__(self) -> str:
        return f'{self.id},{self.ip},{self.port}'

    def __repr__(self) -> str:
        return self.__str__()


class NodoChord:
    def __init__(self, ip: str, peerId = None, port: int = 8001, m: int = 160):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = Referencia(self.ip, self.port)
        self.pred = self.ref 
        self.m = m
        self.finger = [self.ref] * self.m 
        self.lock = threading.Lock()
        self.succ2 = self.ref
        self.succ3 = self.ref
        self.data = {}
        self.replics= []
        
        
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.files_file = os.path.join(self.data_dir, "files.json")
        self.file_names_file = os.path.join(self.data_dir, "file_names.json")
        
        
        if not os.path.exists(self.files_file):
            with open(self.files_file, 'w') as f:
                json.dump([], f)
                
        if not os.path.exists(self.file_names_file):
            with open(self.file_names_file, 'w') as f:
                json.dump([], f)

        


        threading.Thread(target=self.estabilizar_red, daemon=True).start()  
        threading.Thread(target=self.corregir_finger_table, daemon=True).start()  

        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        sock.bind(('', PUERTO_DE_BROADCAST))

        print(f"Servidor escuchando en el puerto {PUERTO_DE_BROADCAST}...")

        discovery_thread = threading.Thread(target=self.manejar_descubrimiento, args=(sock,))
        discovery_thread.daemon = True  
        discovery_thread.start()

        replic_thread = threading.Thread(target=self.replicar)
        replic_thread.daemon = True  
        replic_thread.start()


        
        sock_m = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_m.bind(('', PUERTO_DE_MULTICAST))

        
        group = socket.inet_aton(GRUPO_DE_MULTICAST)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock_m.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print(f"Escuchando en {GRUPO_DE_MULTICAST}:{PUERTO_DE_MULTICAST}...")
        multicast_thread = threading.Thread(target=self.manejar_descubrimiento_multicast,args=(sock_m,))
        multicast_thread.daemon=True
        multicast_thread.start()


        self.new_ip = self.descubrir_servidor()
        print("discovery_ip: ", self.new_ip)
        if self.new_ip is not None:
            threading.Thread(target=self.join, args=(Referencia(self.new_ip, self.port),), daemon=True).start()
        self.iniciar_servidor()


    
    @property
    def succ(self):
        return self.finger[0]
    
    @succ.setter
    def succ(self, node: 'Referencia'):
        with self.lock:
            self.finger[0] = node

    
    def almacenar_archivo(self, file_name, file_type, file_content, r):
        with self.lock:
            file_hash = calcular_hash(file_content)
            content_b64 = b64encode(file_content).decode('utf-8')
            
            # Leer datos existentes
            with open(self.files_file, 'r') as f:
                files = json.load(f)
            with open(self.file_names_file, 'r') as f:
                file_names = json.load(f)
            
            # Verificar si el hash ya existe
            existing_file = next((f for f in files if f['hash'] == file_hash), None)
            if existing_file:
                # Verificar si el nombre ya está asociado
                existing_name = next((n for n in file_names 
                                     if n['file_id'] == existing_file['id'] 
                                     and n['name'] == file_name), None)
                if not existing_name:
                    file_names.append({
                        'file_id': existing_file['id'],
                        'name': file_name
                    })
                    with open(self.file_names_file, 'w') as f:
                        json.dump(file_names, f)
                    if r == 0: 
                        self.replics.append({
                            'name': file_name,
                            'type': file_type,
                            'content': file_content,
                            'nodes': [self.ip]
                        })
                    return "Nombre agregado al archivo existente"
                return "El archivo ya existe con ese nombre"
            else:
                # Crear nuevo registro
                new_id = len(files) + 1
                new_file = {
                    'id': new_id,
                    'hash': file_hash,
                    'content': content_b64,
                    'type': file_type
                }
                files.append(new_file)
                
                file_names.append({
                    'file_id': new_id,
                    'name': file_name
                })
                
                with open(self.files_file, 'w') as f:
                    json.dump(files, f)
                with open(self.file_names_file, 'w') as f:
                    json.dump(file_names, f)
                    
                if r == 0: 
                    self.replics.append({
                        'name': file_name,
                        'type': file_type,
                        'content': file_content,
                        'nodes': [self.ip]
                    })
                return "Archivo subido correctamente"

    def busqueda_broadcast(self, file_name, file_type):
        """Realiza una búsqueda por broadcast en la red CHORD."""
        results = []
        print("CONFIGURANDO SOCKET PARA BUSQUEDA BROADCAST")
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.settimeout(3)  # Tiempo de espera para respuestas

        print("ENVIANDO MENSAJE")
        message = f"{BUSCAR_ARCHIVO},{file_name},{file_type}"
        broadcast_socket.sendto(message.encode(), (DIRECCION_DE_BROADCAST, PUERTO_DE_BROADCAST))

        def manejar_respuesta(m):
            if m.startswith("SEARCH_RESULT~"):
                    print("TENGO RESPUESTA DE LA BUSQUEDA")
                    Elements=eval(m.split("~")[1])
                    with self.lock:
                        for e in Elements:
                            if e not in results: results.append(e)

        
        while True:
            try:
                data, addr = broadcast_socket.recvfrom(1024)
                response = data.decode()
                threading.Thread(
                    target=manejar_respuesta,
                    args=(response,),
                    daemon=True
                ).start()
            except socket.timeout:
                print("SE ACABO EL TIEMPO DE BUSQUEDA")
                break 
        print("BUSQUEDA TERMINADA")
        broadcast_socket.close()
        print("DEVOLVIENDO LOS RESULTADOS")
        print(results)
        return results


    def buscar_archivo(self, file_name, file_type):
        with self.lock:
            with open(self.files_file, 'r') as f:
                files = json.load(f)
            with open(self.file_names_file, 'r') as f:
                file_names = json.load(f)
            
            results = []
            for name_entry in file_names:
                if file_name in name_entry['name']:
                    file_id = name_entry['file_id']
                    file_data = next((f for f in files if f['id'] == file_id), None)
                    if file_data and (file_type == "*" or file_data['type'] == file_type):
                        results.append({
                            'name': name_entry['name'],
                            'type': file_data['type'],
                            'hash': file_data['hash'],
                            'ip': self.ip
                        })
            return results

    def descargar_archivo(self, file_name):
        with self.lock:
            with open(self.files_file, 'r') as f:
                files = json.load(f)
            with open(self.file_names_file, 'r') as f:
                file_names = json.load(f)
            
            # Buscar por nombre
            name_entry = next((n for n in file_names if n['name'] == file_name), None)
            if not name_entry:
                return None
                
            file_data = next((f for f in files if f['id'] == name_entry['file_id']), None)
            if file_data:
                return b64decode(file_data['content'].encode('utf-8'))
            return None


    def _estaEntre(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval [start, end)."""
        k = k % 2 ** self.m
        start = start % 2 ** self.m
        end = end % 2 ** self.m
        if start < end:
            return start <= k < end
        return start <= k or k < end
    
    def _estaEnRango(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval (start, end)."""
        _start = (start + 1) % 2 ** self.m
        return self._estaEntre(k, _start, end)
    
    def _estaEntreComplemento(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval (start, end]."""
        _end = (end - 1) % 2 ** self.m 
        return self._estaEntre(k, start, _end)

    def encontrar_succ(self, id: int) -> 'Referencia':
        node = self.encontrar_predec(id)
        return node.succ 

    def encontrar_predec(self, id: int) -> 'Referencia':
        node = self
        try:
            if node.id == self.succ.id:
                return node
        except:
            print("ERROR AL ENCONTRAR PREDECESOR")
        while not self._estaEntreComplemento(id, node.id, node.succ.id):
            node = node.dedo_mas_cercano(id)
            if node.id == self.id:
                break
        return node

    def dedo_mas_cercano(self, id: int) -> 'Referencia':
        node = None
        for i in range(self.m - 1, -1, -1):
            try:
                if node == self.finger[i]:
                    continue
                self.finger[i].succ
                if self._estaEnRango(self.finger[i].id, self.id, id):
                    return self.finger[i] if self.finger[i].id != self.id else self
            except:
                node = self.finger[i]
                continue    
        return self

    def join(self, node: 'Referencia'):
        time.sleep(5)
        """Unirse a la red usando un nodo como punto de entrada"""
        self.pred = self.ref
        self.succ = node.encontrar_sucesor(self.id)
        self.succ2 = self.succ.succ
        self.succ3 = self.succ2.succ

    def estabilizar_red(self):
        time.sleep(5)
        """Verificar la red para corregir su estructura"""
        while True:
            try:
                if self.succ:
                    x = self.succ.pred
                    
                    if x.id != self.id:
                        if self.succ.id == self.id or self._estaEnRango(x.id, self.id, self.succ.id):
                            self.succ = x
                    self.succ2 = self.succ.succ
                    self.succ.notificar(self.ref)
            except Exception as e:
                try:
                    x = self.succ2
                    self.succ = x
                    self.succ2 = self.succ.succ
                    self.succ.notificar1(Referencia(self.ip, self.port))
                except:
                    try:
                        x = self.succ3
                        self.succ = x
                        self.succ2 = self.succ.succ
                        self.succ3.notificar1(self.ref)
                    except Exception as h:
                        print(f"Error al estabilizar la red: {h}")
            try:
                self.succ3 = self.succ.succ.succ
            except:
                try:
                    self.succ3 = self.succ3.succ
                except:
                    time.sleep(1)
                    continue

            print(f"Sucesor : {self.succ}  Segundo sucesor {self.succ2} Tercer sucesor {self.succ3} Predecesor {self.pred}")
            time.sleep(5)

    def notificar(self, node: 'Referencia'):
        print(f"Notificar desde: {self.ip} a: {node.ip}")
        if node.id == self.id:
            return
        if (self.pred.id == self.id) or self._estaEnRango(node.id, self.pred.id, self.id):
            self.pred = node
    
    def notificar1(self, node: 'Referencia'):
        self.pred = node
    
    def corregir_finger_table(self):
        time.sleep(5)
        while True:
            for i in range(self.m - 1, -1, -1):
                self.next = i
                with self.lock:
                    self.finger[self.next] = self.encontrar_succ((self.id + 2 ** self.next) % (2 ** self.m))
            time.sleep(10)

    def manejar_descubrimiento(self, sock):
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8')
                print(f"Recibido mensaje de broadcast: {message} de {addr}")
                # Crear un hilo para manejar el mensaje
                threading.Thread(
                    target=self.manejar_mensaje_broadcast,
                    args=(sock, message, addr),
                    daemon=True
                ).start()
                
            except Exception as e:
                print(f"Error en el hilo de descubrimiento: {e}")
                break
    
    def manejar_mensaje_broadcast(self, sock, message, addr):
        try:
            if message == "DISCOVER_REQUEST":
                    response = f"ip:{IP_DEL_SERVIDOR}"
                    sock.sendto(response.encode('utf-8'), addr)
            elif message.startswith(f"{BUSCAR_ARCHIVO},"):
                parts = message.split(',')
                file_name, file_type = parts[1], parts[2]
                local_results = self.buscar_archivo(file_name, file_type)
                if local_results:
                    response = f"SEARCH_RESULT~{local_results}"
                    sock.sendto(response.encode(), addr)
        except Exception as e:
            print(f"Error al manejar mensaje de broadcast: {e}")



    def manejar_descubrimiento_multicast(self,sock):
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                if data == b"DISCOVER_NODE":
                    print("RECIBIDO MENSAJE DE MULTICAST")
                    node_ip = socket.gethostbyname(socket.gethostname())
                    sock.sendto(node_ip.encode(), (GRUPO_DE_MULTICAST,PUERTO_DE_MULTICAST))
                    print(f"Respondendo a {GRUPO_DE_MULTICAST} con mi direccion ip: {node_ip}")
        except Exception as e:
            print(f"ERROR EN EL hilo de multicast: {e}")
    
    def descubrir_servidor(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) #Permite broadcast

        sock.settimeout(5)  # Tiempo máximo para esperar una respuesta

        message = "DISCOVER_REQUEST"
        try:
            sock.sendto(message.encode('utf-8'), (DIRECCION_DE_BROADCAST, PUERTO_DE_BROADCAST))
            print("Enviando solicitud de descubrimiento por broadcast...")
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode('utf-8')
                    print(f"Recibido respuesta de {addr}: {response}")

                    if response.startswith("ip:"):
                        server_ip = response.split(":")[1]
                        if server_ip == self.ip:
                            continue
                        print(f"Servidor encontrado en la direccion: {server_ip}")
                        return server_ip

                except socket.timeout:
                    print("No se encontraron servidores en el tiempo especificado.")
                    return None

        except Exception as e:
            print(f"Error durante el descubrimiento: {e}")
            return None
        finally:
            sock.close()

    def replicar(self):
        time.sleep(5)
        while True:
            if self.replics:
                obj = self.replics.pop(0)
                if len(obj["nodes"])<3:
                    if self.ip not in obj["nodes"]:
                        print(f"REPLICANDO ARCHIVO EN NODO: {self.ip}")
                        self.almacenar_archivo(obj['name'],obj['type'],obj['content'],1)
                        obj['nodes'].append(self.ip)
                    
                    message = self.succ.almacenar_en_replicas(obj)
                    if message == "error":
                        self.replics.append(obj)
                    time.sleep(5)
            else:
                time.sleep(5)

    def almacenar_llave(self, key, value):
        key_hash = getShaRepr(key)
        if self._estaEnRango(key_hash, self.id, self.succ.id):
            self.data[key] = value
        else:
            node = self.dedo_mas_cercano(key_hash)
            node.almacenar_llave(key, value)

    def iniciar_servidor(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setblocking(True)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.atender_cliente, args=(conn,), daemon=True).start() 

    def atender_cliente(self, conn: socket.socket):
        
        data = conn.recv(1024).decode().split(',')
        data_resp = None
        option = int(data[0])
        if option == ENCONTRAR_SUCESOR:
            id = int(data[1])
            data_resp = self.encontrar_succ(id)
        elif option == ENCONTRAR_PREDECESOR:
            id = int(data[1])
            data_resp = self.encontrar_predec(id)
        elif option == OBTENER_SUCESOR:
            data_resp = self.succ
        elif option == OBTENER_PREDECESOR:
            data_resp = self.pred
        elif option == NOTIFICAR:
            id = int(data[1])
            ip = data[2]
            self.notificar(Referencia(ip, self.port))
        elif option == DEDO_MAS_CERCANO:
            id = int(data[1])
            data_resp = self.dedo_mas_cercano(id)
        elif option == NOTIFICAR1:
            id = int(data[1])
            ip = data[2]
            self.notificar1(Referencia(ip, self.port))
        elif option == IS_ALIVE:
            data_resp = 'verificar'
        elif option == ALMACENAR_LLAVE:
            print(data)
            key, value = data[1], data[2]
            self.almacenar_llave(key, value)
            print(self.data)
            conn.sendall(self.data)
        elif option == SUBIR_ARCHIVO:
            file_name, file_type, file_size = data[1], data[2], int(data[3])
            print("LISTO PARA RECIBIR")
            conn.send('READY'.encode())
            file_content = b""
            remaining = file_size
            while remaining > 0:
                chunk = conn.recv(min(1024000, remaining))
                if not chunk: 
                    break
                file_content += chunk
                remaining -= len(chunk)
            file_hash = getShaRepr(str(file_content))
            # if file_hash != file_hash_rcv:
            #     conn.send('ERROR, HASH NO COINCIDE'.encode())
            #     return
            # Encontrar al nodo responsable de almacenar el archivo
            responsible_node = self.encontrar_succ(file_hash)
            if responsible_node.id == self.id:
                response = self.almacenar_archivo(file_name, file_type, file_content,0)
            else:
                response = responsible_node.almacenar_archivo(file_name, file_type, file_content, file_size).decode()
                while response == "ERROR":
                    responsible_node = self.encontrar_succ(file_hash)
                    if responsible_node.id == self.id:
                        response = self.almacenar_archivo(file_name, file_type, file_content,0)
                    else:
                        response = responsible_node.almacenar_archivo(file_name, file_type, file_content, file_size).decode()
            
            conn.send(response.encode())
        elif option == BUSCAR_ARCHIVO:
            file_name,file_type= data[1],data[2]
            try:
                print("BUSCAR ARCHIVO POR BROADCAST")
                results= self.busqueda_broadcast(file_name,file_type)
                print("ENVIANDO RESPUESTA")
                conn.sendall(str(results).encode())
            except Exception as e:
                print(f"ERROR DURANTE LA BUSQUEDA POR BROADCAST: {e}")
                conn.sendall("ERROR DURANTE LA BUSQUEDA POR BROADCAST".encode())
        elif option == DESCARGAR_ARCHIVO:
            file_name = data[1]
            response = self.descargar_archivo(file_name)
            conn.send(f'{len(response)}'.encode())
            conn.recv(1024).decode()
            conn.send(f'{getShaRepr(str(response))}'.encode())
            conn.recv(1024).decode()
            for i in range(0, len(response), 1024000):
                chunk = response[i:i+1024000]
                conn.send(chunk)

        elif option == ALMACENAR_REPLICA:
            file_name,file_type,file_size= data[1],data[2],int(data[3])
            print(f'Replic size: {file_size}')
            nodes ="["
            for i in range(4,len(data)):
                nodes+= "\"" + data[i] + "\""
                if i!=len(data)-1:
                    nodes+=","
            nodes+="]"
            nodes= eval(nodes)
            conn.send('READY'.encode())
            file_content = b""
            remaining = file_size
            while remaining > 0:
                chunk = conn.recv(min(1024000, remaining))
                if not chunk: 
                    break
                file_content += chunk
                remaining -= len(chunk)
            self.replics.append({'name':file_name,'type':file_type,'content':file_content,'nodes':nodes})

        if option in [SUBIR_ARCHIVO,BUSCAR_ARCHIVO]:
            return
        if data_resp == 'verificar':
            response = data_resp.encode()
            conn.sendall(response)
        elif data_resp:
            response = f'{data_resp.id},{data_resp.ip}'.encode()
            conn.sendall(response)
        conn.close()


if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    node = NodoChord(ip)
