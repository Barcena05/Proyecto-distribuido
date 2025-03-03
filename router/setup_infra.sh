set +o verbose


docker network inspect clients >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Network clients exists."
else
    docker network create clients --subnet 10.0.10.0/24
    echo "Network clients created."
fi


docker network inspect servers >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Network servers exists."
else
    docker network create servers --subnet 10.0.11.0/24
    echo "Network servers created."
fi


docker image inspect router >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Image router:base exists."
else
    docker build -t router:base -f router/router_base.Dockerfile router/
    echo "Image router:base created."
fi


docker image inspect router >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Image router exists."
else
    docker build -t router -f router/router.Dockerfile router/
    echo "Image router created."
fi

docker container inspect router >/dev/null 2>&1
if [ $? -eq 0 ]; then
    docker container stop router
    docker container rm router
    echo "Container router removed."    
fi

docker run -d --rm --name router --cap-add NET_ADMIN -e PYTHONUNBUFFERED=1 router
echo "Container router executed."



docker network connect --ip 10.0.10.254 clients router
docker network connect --ip 10.0.11.254 servers router

docker run -d --rm --name multicast --cap-add NET_ADMIN -e PYTHONUNBUFFERED=1 router
echo "Container multicast executed."

docker network connect --ip 10.0.11.253 servers multicast
docker network connect --ip 10.0.10.253 clients multicast

echo "Container router connected to client and server networks."