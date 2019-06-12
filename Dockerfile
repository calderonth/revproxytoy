FROM python:3.7-alpine

WORKDIR /code

RUN addgroup proxy && adduser -D -G proxy proxy

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

USER proxy
COPY reverse_proxy.py reverse_proxy.py
COPY config.ini config.ini
CMD ["python3", "/code/reverse_proxy.py"]
