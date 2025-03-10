FROM base

WORKDIR /app

COPY server/routing.sh /app
COPY server/server.py /app
COPY server/ca.crt /app
COPY server/servidor.crt /app 
COPY server/servidor.key /app

RUN chmod +x /app/routing.sh

ENTRYPOINT [ "/app/routing.sh" ]