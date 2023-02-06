FROM python:3.11

WORKDIR /app
COPY . /app
COPY requirements.txt  /

ENV TZ="UTC"
ENV HS_SERVER="http://localhost/"
ENV KEY=""

RUN pip install -r /app/requirements.txt

USER 1000:1000

VOLUME /headscale 
VOLUME /data

EXPOSE 5000/tcp
CMD ["python","/app/server.py"]