# Dockerfile para el cliente
FROM base


# Crear directorio de trabajo
WORKDIR /app

# Copiar los archivos necesarios
COPY client/cliente.py ./cliente.py
COPY client/cliente.sh /usr/local/bin/cliente.sh

# Asegúrate de que el script sea ejecutable
RUN chmod +x /usr/local/bin/cliente.sh


# Configurar entorno para Tkinter (si se usa X11 forwarding)
ENV DISPLAY=:0

# Ejecutar el script de configuración y luego el cliente
ENTRYPOINT ["/bin/sh", "-c", "/usr/local/bin/cliente.sh && python /app/cliente.py"]
