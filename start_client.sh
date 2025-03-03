#!/bin/bash

# Verificar si se ha pasado un parámetro
if [ -z "$1" ]; then
    echo "No se ha proporcionado ningún nombre para el cliente."
    echo "Uso: ./start_client.sh <nombre>"
    exit 1
fi

xhost +local:docker


docker run -it --name $1 -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /usr/share/fonts:/usr/share/fonts:ro --cap-add NET_ADMIN --network clients client