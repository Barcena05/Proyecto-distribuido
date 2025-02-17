import hashlib
import socket
import threading
import time
import pickle
from datetime import datetime, timedelta

M = 8 
PORT = 5000
REPLICATION_FACTOR = 3
STABILIZE_INTERVAL = 5
CHECK_INTERVAL = 3

def hash_key(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**M)

class Node:
    def __init__(self, ip, port):
        self.id = hash_key(f"{ip}:{port}")
        self.ip = ip
        self.port = port
        self.finger_table = [(ip, port)] * M
        self.predecessor = None
        self.data = {}
        self.alive = True
        self.lock = threading.Lock()
        self.successor_list = []
        self.failed_nodes = set()
        self._data_expiration = timedelta(minutes=5)

    def resolve_node(self, node_addr):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((node_addr[0], node_addr[1]))
            return s
        except:
            return None

    def remote_call(self, node_addr, command, *args):
        try:
            s = self.resolve_node(node_addr)
            if s:
                message = (command, args)
                s.sendall(pickle.dumps(message))
                response = pickle.loads(s.recv(1024))
                s.close()
                return response
            else:
                self.mark_failed(node_addr)
                return None
        except Exception as e:
            self.mark_failed(node_addr)
            return None

    def mark_failed(self, node_addr):
        with self.lock:
            if node_addr not in self.failed_nodes:
                print(f"Marcando nodo {node_addr} como fallado")
                self.failed_nodes.add(node_addr)
                for i in range(M):
                    if self.finger_table[i] == node_addr:
                        self.finger_table[i] = self.find_successor((self.id + 2**i) % (2**M))
                if self.predecessor == node_addr:
                    self.predecessor = None
                self.successor_list = [s for s in self.successor_list if s != node_addr]
                self.build_successor_list()
                threading.Thread(target=self.stabilize).start()

    def ping_node(self, node_addr):
        try:
            return self.remote_call(node_addr, 'ping') is True
        except:
            return False

    def build_successor_list(self):
        self.successor_list = []
        seen = set()
        current = self.finger_table[0]
        if not current or not self.ping_node(current):
            current = self.find_successor((self.id + 1) % (2**M))
            self.finger_table[0] = current
        while len(self.successor_list) < REPLICATION_FACTOR:
            if current and current not in seen and self.ping_node(current):
                if current != (self.ip, self.port):
                    self.successor_list.append(current)
                seen.add(current)
            else:
                break
            next_node = self.remote_call(current, 'get_successor')
            if not next_node or next_node == current:
                break
            current = next_node
        i = 1
        while len(self.successor_list) < REPLICATION_FACTOR and i < 256:
            candidate = self.find_successor((self.id + i) % (2**M))
            if candidate and candidate not in self.successor_list and candidate != (self.ip, self.port):
                self.successor_list.append(candidate)
            i += 1

    def find_successor(self, key):
        try:
            if self.id == key:
                return (self.ip, self.port)
            node_addr = self.closest_preceding_node(key)
            if node_addr == (self.ip, self.port):
                if self.finger_table[0]:
                    return self.finger_table[0]
                else:
                    return (self.ip, self.port)
            return self.remote_call(node_addr, 'find_successor', key)
        except Exception as e:
            return self.finger_table[0] if self.finger_table[0] else (self.ip, self.port)

    def closest_preceding_node(self, key):
        for i in range(M-1, -1, -1):
            node_addr = self.finger_table[i]
            if node_addr not in self.failed_nodes and self.ping_node(node_addr):
                node_id = self.remote_call(node_addr, 'get_id')
                if node_id and self.is_key_between(node_id, self.id, key):
                    return node_addr
        return (self.ip, self.port)

    def is_key_between(self, key, start, end):
        if start < end:
            return start < key <= end
        else:
            return start < key or key <= end

    def find_predecessor(self, key):
        node_addr = (self.ip, self.port)
        while True:
            successor = self.remote_call(node_addr, 'get_successor')
            if not successor or node_addr in self.failed_nodes:
                break
            successor_id = self.remote_call(successor, 'get_id')
            node_id = self.remote_call(node_addr, 'get_id')
            if not successor_id or not node_id:
                break
            if self.is_key_between(key, node_id, successor_id):
                return node_addr
            next_node = self.remote_call(node_addr, 'closest_preceding_node', key)
            if not next_node or next_node == node_addr:
                break
            node_addr = next_node
        return (self.ip, self.port)

    def join(self, existing_node_addr=None):
        if existing_node_addr:
            self.init_finger_table(existing_node_addr)
            self.update_others()
            self.build_successor_list()
            threading.Thread(target=self.stabilize).start()
        else:
            self.predecessor = (self.ip, self.port)
            self.finger_table = [(self.ip, self.port)] * M
            self.successor_list = [(self.ip, self.port)]

    def init_finger_table(self, existing_node_addr):
        self.finger_table[0] = self.remote_call(existing_node_addr, 'find_successor', (self.id + 1) % (2**M))
        if self.finger_table[0]:
            predecessor_candidate = self.remote_call(self.finger_table[0], 'get_predecessor')
            if predecessor_candidate and self.ping_node(predecessor_candidate):
                self.predecessor = predecessor_candidate
            self.remote_call(self.finger_table[0], 'update_predecessor', (self.ip, self.port))
        for i in range(M):
            start = (self.id + 2**i) % (2**M)
            self.finger_table[i] = self.find_successor(start)

    def update_others(self):
        for i in range(M):
            target_id = (self.id - 2**i + (2**M)) % (2**M)
            p = self.find_predecessor(target_id)
            self.remote_call(p, 'update_finger_table', (self.ip, self.port), i)

    def update_finger_table(self, node_addr, i):
        start = (self.id + 2**i) % (2**M)
        node_hash = hash_key(f"{node_addr[0]}:{node_addr[1]}")
        if self.is_key_between(node_hash, self.id, start) or self.id == start:
            self.finger_table[i] = node_addr
            if self.predecessor and self.predecessor != (self.ip, self.port):
                self.remote_call(self.predecessor, 'update_finger_table', node_addr, i)

    def store_data(self, key, value, ttl=REPLICATION_FACTOR):
        with self.lock:
            if key not in self.data:
                self.data[key] = {
                    'value': value,
                    'expires': datetime.now() + self._data_expiration
                }
                print(f"Nodo {self.port} almacenó clave {key}")
                if ttl > 0:
                    self.replicate_data(key, value, ttl)

    def replicate_data(self, key, value, ttl):
        success_count = 0
        for successor in self.successor_list[:ttl]:
            if successor != (self.ip, self.port) and self.ping_node(successor):
                try:
                    if self.remote_call(successor, 'store_data', key, value, 0):
                        success_count += 1
                    else:
                        print(f"Fallo réplica en {successor[1]}")
                except Exception as e:
                    self.mark_failed(successor)

    def get_data(self, key):
        self.clean_expired_data()
        return self.data.get(key, {}).get('value', None)

    def clean_expired_data(self):
        now = datetime.now()
        expired = [k for k, v in self.data.items() if v['expires'] < now]
        for k in expired:
            del self.data[k]

    def stabilize(self):
        while self.alive:
            time.sleep(STABILIZE_INTERVAL)
            successor = self.finger_table[0]
            if not self.ping_node(successor):
                successor = self.find_successor((self.id + 1) % (2**M))
                self.finger_table[0] = successor
            x = self.remote_call(successor, 'get_predecessor')
            if x and self.ping_node(x):
                x_id = self.remote_call(x, 'get_id')
                succ_id = self.remote_call(successor, 'get_id')
                if x_id and succ_id and self.is_key_between(x_id, self.id, succ_id):
                    successor = x
                    self.finger_table[0] = successor
            if successor:
                self.remote_call(successor, 'notify', (self.ip, self.port))
            self.build_successor_list()

    def notify(self, node_addr):
        node_id = self.remote_call(node_addr, 'get_id')
        if node_id:
            predecessor_id = self.remote_call(self.predecessor, 'get_id') if self.predecessor else None
            if self.predecessor is None or (predecessor_id is not None and self.is_key_between(node_id, predecessor_id, self.id)):
                self.predecessor = node_addr

    def check_predecessor(self):
        while self.alive:
            time.sleep(CHECK_INTERVAL)
            if self.predecessor and not self.ping_node(self.predecessor):
                self.predecessor = None
            for successor in self.successor_list[:]:
                if not self.ping_node(successor):
                    self.mark_failed(successor)

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen()
            while self.alive:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn,)).start()

    def handle_client(self, conn):
        with conn:
            data = conn.recv(1024)
            if data:
                try:
                    message = pickle.loads(data)
                    command, args = message
                    handlers = {
                        'get_id': lambda: self.id,
                        'get_successor': lambda: self.finger_table[0],
                        'get_predecessor': lambda: self.predecessor,
                        'update_predecessor': lambda: setattr(self, 'predecessor', args[0]),
                        'find_successor': lambda: self.find_successor(args[0]),
                        'closest_preceding_node': lambda: self.closest_preceding_node(args[0]),
                        'store_data': lambda: self.store_data(args[0], args[1], args[2]),
                        'get_data': lambda: self.get_data(args[0]),
                        'update_finger_table': lambda: self.update_finger_table(args[0], args[1]),
                        'ping': lambda: True,
                        'get_successors': lambda: self.successor_list,
                        'notify': lambda: self.notify(args[0])
                    }
                    handler = handlers.get(command)
                    response = handler() if handler else None
                    conn.sendall(pickle.dumps(response))
                except Exception as e:
                    conn.sendall(pickle.dumps(None))


if __name__ == "__main__":
    Node(ip="0.0.0.0", port=PORT)