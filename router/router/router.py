import socket
import struct
import ipaddress
from subprocess import check_output
from multiprocessing import Process

DIRECCIONES_LOCALES = [x for x in check_output(['hostname', '-i']).decode().strip().split(' ')]
OPT_NAME = 20
DIRECCIONES_RESERVADAS = ['127.0.0.1', '10.0.10.254', '10.0.11.254', '10.0.10.253', '10.0.11.253']
PUERTO = 10000
NUMERO_DE_PROCESOS = 5

def proxy(port, read_buffer = 4196):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = ('', port)
    sock.bind(server_address)

    
    sock.setsockopt(socket.IPPROTO_IP, OPT_NAME, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)

    while True:
        data, ancdata, _, address = sock.recvmsg(read_buffer, socket.MSG_CMSG_CLOEXEC)

        client_net = address[0].split('.')[2]
        primary_net = DIRECCIONES_LOCALES[1].split('.')[2]
        
        if address[0] in DIRECCIONES_RESERVADAS or address[0] in DIRECCIONES_LOCALES or client_net != primary_net:
            continue

        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.IPPROTO_IP and cmsg_type == OPT_NAME:
                family, port = struct.unpack('=HH', cmsg_data[0:4])
                port = socket.htons(port)

                if family != socket.AF_INET:
                    raise TypeError(f"Tipo de socket no soportado '{family}'")

                ip = socket.inet_ntop(family, cmsg_data[4:8])
                ip_object = ipaddress.ip_address(ip)

                if ip_object.is_multicast:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
                        s.sendto(data, (ip, port))

processes = []

for i in range(NUMERO_DE_PROCESOS):
    p = Process(target=proxy, args=(PUERTO + i,))
    p.start()
    processes.append(p)

for p in processes:
    p.join()