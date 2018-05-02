FROM resin/raspberrypi3-alpine-python:3-slim

RUN [ "cross-build-start" ]

ENV INITSYSTEM on

WORKDIR /usr/src/app

COPY . .

RUN apk update && \
    apk add --virtual build-deps gcc python-dev musl-dev && \
    apk add postgresql-dev

RUN pip install --no-cache-dir pipenv && pipenv install --system --deploy

ENTRYPOINT ["python", "-m", "fotc.main"]

RUN [ "cross-build-end" ]
