FROM ghcr.io/home-assistant/base:latest
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY run.sh /app/
COPY solaredge_optimizers.py /app/

EXPOSE 8126

CMD ["/app/run.sh"]
