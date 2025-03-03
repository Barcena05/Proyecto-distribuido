set +o verbose

cd router

chmod +x setup_infra.sh
sudo ./setup_infra.sh

cd ..

docker build -t base -f base/Dockerfile .
docker build -t client -f client/cliente.Dockerfile .
docker build -t server -f server/server.Dockerfile .
