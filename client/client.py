import hashlib
import pickle
import socket
from datetime import datetime, timedelta

M = 8
PORT = 5000

def hash_key(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**M)

class ChordClient:
    def __init__(self, bootstrap_node):
        """
        Initializes a ChordClient instance with a bootstrap node.

        Args:
            bootstrap_node (tuple): The IP address and port of the bootstrap node.

        Returns:
            None
        """
        self.bootstrap_node = bootstrap_node
        self.local_files = {}
        
    def remote_call(self, node_addr, command, *args):
        """
        Makes a remote procedure call to a node in the Chord network.

        Args:
            node_addr (tuple): The IP address and port of the node to call.
            command (str): The command to execute on the remote node.
            *args: Variable number of arguments to pass to the remote command.

        Returns:
            The response from the remote node, or None if the call fails.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect(node_addr)
                message = (command, args)
                s.sendall(pickle.dumps(message))
                response = pickle.loads(s.recv(1024))
                return response
        except:
            return None
    
    def upload_file(self, file_name):
        """
        Uploads a file to the Chord network.

        Args:
            file_name (str): The path to the file to be uploaded.

        Returns:
            None
        """
        try:
            with open(file_name, 'rb') as f:
                content = f.read()
                key = hash_key(file_name)
                target_node = self.remote_call(self.bootstrap_node, 'find_successor', key)
                
                metadata = {
                    'name': file_name.split('/')[-1],
                    'format': file_name.split('.')[-1],
                    'content': content,
                    'timestamp': datetime.now()
                }
                
                if self.remote_call(target_node, 'store_data', key, metadata):
                    print(f"Archivo {file_name} subido correctamente (clave: {key})")
                    self.local_files[key] = metadata
                else:
                    print("Error al subir el archivo")
        except Exception as e:
            print(f"Error: {e}")
    
    def search_files(self, query, file_format='Any'):
        """
        Searches for files in the Chord network based on a query and optional file format.

        Args:
            query (str): The search query to use when searching for files.
            file_format (str, optional): The file format to filter results by. Defaults to 'Any'.

        Returns:
            list: A list of tuples containing the names of matching files and their corresponding nodes.
        """
        results = []
        query_hash = hash_key(query)
        target_node = self.remote_call(self.bootstrap_node, 'find_successor', query_hash)
        metadata = self.remote_call(target_node, 'get_data', query_hash)
        
        if metadata and (file_format == 'Any' or metadata['format'].lower() == file_format.lower()):
            results.append((metadata['name'], target_node))
        
        print("\nResultados de búsqueda:")
        for name, node in results:
            print(f"Nombre: {name}, Nodo: {node[1]}")
        return results
    
    def download_file(self, file_name, node_addr):
        """
        Downloads a file from the Chord network.

        Args:
            file_name (str): The name of the file to be downloaded.
            node_addr: The address of the node containing the file.

        Returns:
            None
        """
        key = hash_key(file_name)
        metadata = self.remote_call(node_addr, 'get_data', key)
        if metadata:
            with open(f"downloads/{metadata['name']}", 'wb') as f:
                f.write(metadata['content'])
            print(f"Archivo {metadata['name']} descargado correctamente")
        else:
            print("Archivo no encontrado")

def main():
    bootstrap_node = ("127.0.0.1", 5000)
    client = ChordClient(bootstrap_node)
    
    while True:
        print("\n1. Buscar archivos")
        print("2. Subir archivo")
        print("3. Descargar archivo")
        print("4. Salir")
        opcion = input("Seleccione una opción: ")
        
        if opcion == '1':
            query = input("Término de búsqueda: ")
            formato = input("Formato (deje vacío para cualquier): ")
            results = client.search_files(query, formato if formato else 'Any')
            
            if results:
                file_name = input("Nombre exacto para descargar: ")
                client.download_file(file_name, results[0][1])
        
        elif opcion == '2':
            file_path = input("Ruta del archivo a subir: ")
            client.upload_file(file_path)
        
        elif opcion == '3':
            file_name = input("Nombre exacto del archivo: ")
            key = hash_key(file_name)
            target_node = client.remote_call(bootstrap_node, 'find_successor', key)
            client.download_file(file_name, target_node)
        
        elif opcion == '4':
            break

if __name__ == "__main__":
    main()