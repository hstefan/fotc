FROM resin/raspberrypi3-alpine-python:3-slim as build-base
RUN [ "cross-build-start" ]

ENV INITSYSTEM on

WORKDIR /usr/src/app/build

COPY . .

RUN apk update && \
    apk add --virtual build-deps gcc python-dev musl-dev && \
    apk add postgresql-dev

RUN pip install --no-cache-dir pipenv

RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy
RUN [ "cross-build-end" ]

FROM resin/raspberrypi3-alpine-python:3-slim
RUN [ "cross-build-start" ]
WORKDIR /usr/src/app

RUN apk update && apk add postgresql-dev
COPY --from=build-base /usr/src/app/build/.venv .venv
COPY --from=build-base /usr/src/app/build/fotc fotc
ENTRYPOINT [".venv/bin/python3", "-m", "fotc.main"]

RUN [ "cross-build-end" ]

