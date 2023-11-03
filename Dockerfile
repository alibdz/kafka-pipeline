FROM python:3.8

ENV DEBIAN_FRONTEND=noninteractive

COPY ./requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

WORKDIR /app
COPY . .

CMD [ python , main.py]
