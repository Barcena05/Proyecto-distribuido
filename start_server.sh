#!/bin/bash

# Verificar si se ha pasado un parámetro
if [ -z "$1" ]; then
    echo "No se ha proporcionado ningún nombre para el servidor."
    echo "Uso: ./start_server.sh <nombre>"
    exit 1
fi

docker run -it --name $1 --cap-add NET_ADMIN --network servers server