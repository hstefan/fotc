FROM resin/raspberrypi3-alpine-python:3-slim

RUN [ "cross-build-start" ]

ENV INITSYSTEM on

WORKDIR /usr/src/app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt && pip install -e .

ENTRYPOINT ["fotc-bot"]

RUN [ "cross-build-end" ]
