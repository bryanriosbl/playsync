FROM python:3.10-alpine

ENV PYTHONUNBUFFERED 1

RUN apk update \
  && apk add --virtual build-deps curl curl-dev gcc libc-dev g++ libffi-dev libxml2 python3-dev musl-dev \
  # Pillow dependencies
  && apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev \
  # Translations dependencies
  && apk add gettext \
  && apk add libpq-dev libssl3 libcrypto3 \
  && apk add openssl \
  && rm -rf /var/cache/apk/*

WORKDIR /app
COPY . .

RUN pip install --upgrade pip setuptools && \
    pip install -r requirements.txt

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]


