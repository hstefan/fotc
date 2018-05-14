FROM python:3-alpine

WORKDIR /usr/src/app

COPY . .

RUN apk update                                                  \
    && apk add --virtual build-deps gcc postgresql-dev musl-dev \
    && pip install --no-cache-dir -r requirements.txt           \
    && apk del build-deps

RUN apk add postgresql-dev

ENTRYPOINT ["python3", "-m", "fotc.main"]