FROM resin/raspberrypi3-python:3

RUN [ "cross-build-start" ]

ENV INITSYSTEM on

WORKDIR /usr/src/app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt && pip install -e .

ENTRYPOINT ["fotc-bot"]

RUN [ "cross-build-end" ]
