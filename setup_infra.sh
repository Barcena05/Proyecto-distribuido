set +o verbose

# check clients docker networks existence

docker network inspect clients >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Network clients exists."
else
    docker network create clients --subnet 10.0.10.0/24
    echo "Network clients created."
fi

# check servers docker network existence 

docker network inspect servers >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Network servers exists."
else
    docker network create servers --subnet 10.0.11.0/24
    echo "Network servers created."
fi

# check router docker image existence 

docker image inspect router >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Image router exists."
else
    docker build -t router -f router/router.Dockerfile .
    echo "Image router created."
fi

# check router container existence

docker container inspect router >/dev/null 2>&1
if [ $? -eq 0 ]; then
    docker container stop router
    docker container rm router
    echo "Container router removed."    
fi

docker run -d --rm --name router router
echo "Container router executed."

# attach router to client and server networks

docker network connect --ip 10.0.10.254 clients router
docker network connect --ip 10.0.11.254 servers router

echo "Container router connected to client and server networks."

# check server docker image existence 

docker image inspect server >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Image server exists."
else
    docker build -t server -f server/Dockerfile server/
    echo "Image server created."
fi

# check client docker image existence 

docker image inspect client >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Image client exists."
else
    docker build -t client -f client/Dockerfile client/
    echo "Image client created."
fi

# check server container existence

docker container inspect server >/dev/null 2>&1
if [ $? -eq 0 ]; then
    docker container stop server
    docker container rm server
    echo "Container server removed."    
fi

docker run --rm -d --privileged -p 5000:5000 --name server --cap-add NET_ADMIN --network servers server
echo "Container server executed."

