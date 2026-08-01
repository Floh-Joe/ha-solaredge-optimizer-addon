FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y netcat-openbsd

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY run.sh /app/
RUN chmod +x /app/run.sh

COPY solaredge_optimizers.py /app/
COPY server.py /app/

EXPOSE 8126

CMD ["/app/run.sh"]
