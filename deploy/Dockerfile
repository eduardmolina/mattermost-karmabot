FROM alpine:3.8

RUN apk add --no-cache python3

COPY requirements.txt /

RUN apk add --no-cache --virtual build-dependencies \
	gcc \
	linux-headers \
	musl-dev \
	python3-dev \
	tzdata \
	&& cp /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime \
	&& echo "America/Sao_Paulo" > /etc/timezone \
	&& pip3 install -r /requirements.txt \
	&& apk del build-dependencies

COPY src /src
COPY config /config
COPY run.py /run.py

CMD python3 /run.py
