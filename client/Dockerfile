
FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt && apt-get update && apt-get install -y iproute2

RUN chmod +x /app/client.sh

CMD [ "/app/client.sh" ]