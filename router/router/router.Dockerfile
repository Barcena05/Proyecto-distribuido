FROM router:base

COPY route.sh /root/route.sh

COPY router.py /root/router.py

RUN chmod +x /root/route.sh

ENTRYPOINT /root/route.sh