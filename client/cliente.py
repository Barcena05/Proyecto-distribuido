import os
import socket
import struct
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import hashlib

GRUPO_MULTICAST = '224.0.0.1'
PUERTO_MULTICAST = 10000
PUERTO_TCP = 8001

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(),16)
class FileShareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente del buscador de archivos")
        self.root.geometry("800x600")
        
        # Área de logs
        self.log_area = scrolledtext.ScrolledText(root, state='disabled', height=20)
        self.log_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Frame para subir archivos
        self.upload_frame = tk.Frame(root)
        self.upload_frame.pack(padx=10, pady=5, fill=tk.X)
        self.upload_btn = tk.Button(self.upload_frame, text="Seleccionar archivo", command=self.select_file)
        self.upload_btn.pack(side=tk.LEFT)
        self.upload_path = tk.StringVar()
        self.upload_entry = tk.Entry(self.upload_frame, textvariable=self.upload_path, width=50)
        self.upload_entry.pack(side=tk.LEFT, padx=5)
        self.upload_start_btn = tk.Button(self.upload_frame, text="Subir", command=self.start_upload)
        self.upload_start_btn.pack(side=tk.LEFT)
        
        # Frame para descargar archivos
        self.download_frame = tk.Frame(root)
        self.download_frame.pack(padx=10, pady=5, fill=tk.X)
        tk.Label(self.download_frame, text="Nombre:").pack(side=tk.LEFT)
        self.download_name = tk.Entry(self.download_frame, width=30)
        self.download_name.pack(side=tk.LEFT, padx=5)
        tk.Label(self.download_frame, text="Tipo:").pack(side=tk.LEFT)
        self.download_type = tk.Entry(self.download_frame, width=10)
        self.download_type.pack(side=tk.LEFT, padx=5)
        self.search_btn = tk.Button(self.download_frame, text="Buscar", command=self.start_search)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # Lista de resultados
        self.results_list = tk.Listbox(root, height=10)
        self.results_list.pack(padx=10, pady=5, fill=tk.BOTH)
        self.download_selected_btn = tk.Button(root, text="Descargar seleccionado", command=self.start_download)
        self.download_selected_btn.pack(pady=5)
        
        # Variables
        self.selected_file = None
        self.search_results = []

    def log(self, message):
        """Agrega mensajes al área de logs"""
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

    def select_file(self):
        """Abre un diálogo para seleccionar archivo"""
        file_path = filedialog.askopenfilename()
        if file_path:
            self.upload_path.set(file_path)

    def start_upload(self):
        """Inicia la subida en un hilo separado"""
        file_path = self.upload_path.get()
        if not file_path:
            messagebox.showerror("Error", "Seleccione un archivo primero")
            return
        threading.Thread(target=self.upload_file, args=(file_path,)).start()

    def upload_file(self, file_path):
        """Proceso de subida de archivo"""
        try:
            self.log(f"Iniciando subida de {file_path}")
            
            # Crear socket multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.bind(("", PUERTO_MULTICAST))

            # Unirse al grupo multicast
            group = socket.inet_aton(GRUPO_MULTICAST)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Enviar solicitud de descubrimiento
            sock.sendto(b"DISCOVER_NODE", (GRUPO_MULTICAST, PUERTO_MULTICAST))

            # Esperar respuesta
            node_ip = None
            while True:
                data, addr = sock.recvfrom(1024)
                if data != b"DISCOVER_NODE":
                    node_ip = data.decode()
                    self.log(f"Nodo descubierto: {node_ip}")
                    break

            # Conectar al nodo
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((node_ip, PUERTO_TCP))
            
            # Enviar archivo
            file_name = os.path.basename(file_path)
            file_type = file_name.split(".")[-1]
            file_size = os.path.getsize(file_path)
            with open(file_path,'rb') as file:
                file_hash = getShaRepr(str(file.read()))
            client_socket.send(f"10,{file_name},{file_type},{file_size},{file_hash}".encode())
            if client_socket.recv(1024).decode() == 'READY':
                with open(file_path, "rb") as f:
                    while chunk := f.read(1024000):
                        client_socket.send(chunk)
                response = client_socket.recv(1024).decode()
                self.log(f"Respuesta del servidor: {response}")
            client_socket.close()
            
        except socket.timeout:
            self.log("[ERROR] No se encontraron nodos disponibles")
        except Exception as e:
            self.log(f"[ERROR] Error al subir archivo: {str(e)}")
        finally:
            sock.close()

    def start_search(self):
        """Inicia la búsqueda en un hilo separado"""
        name = self.download_name.get()
        file_type = self.download_type.get() if self.download_type.get() else '*'
        if not name:
            messagebox.showerror("Error", "Ingrese un nombre de archivo")
            return
        threading.Thread(target=self.search_files, args=(name, file_type)).start()

    def search_files(self, name, file_type):
        """Proceso de búsqueda de archivos"""
        try:
            self.log(f"Buscando {name} con extension {file_type}")
            
            # Crear socket multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.bind(("", PUERTO_MULTICAST))

            # Unirse al grupo multicast
            group = socket.inet_aton(GRUPO_MULTICAST)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Enviar solicitud de descubrimiento
            sock.sendto(b"DISCOVER_NODE", (GRUPO_MULTICAST, PUERTO_MULTICAST))

            # Esperar respuesta
            node_ip = None
            while True:
                data, addr = sock.recvfrom(1024)
                if data != b"DISCOVER_NODE":
                    node_ip = data.decode()
                    self.log(f"Nodo descubierto: {node_ip}")
                    break

            # Conectar al nodo
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((node_ip, PUERTO_TCP))
            
            # Buscar archivos
            client_socket.sendall(f"11,{name},{file_type}".encode())
            results = eval(client_socket.recv(1024).decode())
            if not results:
                self.log("No se encontraron resultados.")       
                return
            
            # Procesar resultados
            self.search_results = []
            for result in results:
                self.search_results.append({
                    'name': result['name'],
                    'type': result['type'],
                    'hash': result['hash'],
                    'nodes': [result['ip']]
                })
            
            # Agrupar por hash
            for res in results[1:]:
                existing = next((x for x in self.search_results if x['hash'] == res['hash']), None)
                if existing:
                    existing['nodes'].append(res['ip'])
                else:
                    self.search_results.append({
                        'name': res['name'],
                        'type': res['type'],
                        'hash': res['hash'],
                        'nodes': [res['ip']]
                    })
            
            # Actualizar GUI
            self.root.after(0, self.update_results_list)
            
        except socket.timeout:
            self.log("[ERROR] No se encontraron nodos disponibles")
        except Exception as e:
            self.log(f"[ERROR] Error en la búsqueda: {str(e)}")
        finally:
            sock.close()
            if 'client_socket' in locals():
                client_socket.close()
    
    def format_size(self, size):
        """Formatea el tamaño del archivo para mostrar"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def download_file(self, file_info):
        """Proceso de descarga de archivo"""
        try:
            self.log(f"Descargando {file_info['name']}...")
            file_name = file_info['name']
            
            # Intentar descargar desde cada nodo disponible
            for node_ip in file_info['nodes']:
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    client_socket.connect((node_ip, PUERTO_TCP))
                    self.log(f"Conectado al nodo {node_ip}")
                    client_socket.send(f"{12},{file_name}".encode())
                    
                    # Recibir información del archivo
                    size = int(client_socket.recv(1024).decode())
                    client_socket.send('ACK'.encode())
                    received_hash = client_socket.recv(1024).decode()
                    client_socket.send('ACK'.encode())
                    # Guardar archivo
                    with open(file_name, 'wb') as f:
                        remaining = size
                        file_content = b""
                        while remaining > 0:
                            chunk = client_socket.recv(min(remaining, 1024000))
                            file_content += chunk
                            remaining -= len(chunk)
                        # if received_hash != getShaRepr(str(file_content)):
                        #     self.log("[ERROR] El archivo no coincide con el hash")
                        #     client_socket.close()
                        #     continue
                        f.write(file_content)
                    self.log(f"[INFO] Archivo guardado como {file_name}")
                    client_socket.close()
                    return
                except:
                    client_socket.close()
                    continue
            
            self.log("[ERROR] No se pudo descargar el archivo de ningún nodo")
        except Exception as e:
            self.log(f"[ERROR] Error al descargar: {str(e)}")

    def update_results_list(self):
        """Actualiza la lista de resultados en la GUI"""
        self.results_list.delete(0, tk.END)
        for result in self.search_results:
            self.results_list.insert(tk.END, f"{result['name']} ({result['type']}) hash:{result['hash']}")

    def start_download(self):
        """Inicia la descarga del archivo seleccionado"""
        selection = self.results_list.curselection()
        if not selection:
            messagebox.showerror("Error", "Seleccione un archivo de la lista")
            return
        selected = self.search_results[selection[0]]
        threading.Thread(target=self.download_file, args=(selected,)).start()
    

if __name__ == "__main__":
    root = tk.Tk()
    app = FileShareApp(root)
    root.mainloop()