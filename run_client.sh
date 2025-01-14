#check client container existence

docker container inspect $1 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    docker container stop $1
    docker container rm $1
    echo "Container $1 removed."    
fi

docker run --rm -i --privileged --name $1 --network clients client
