FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY run.sh /app/
RUN chmod +x /app/run.sh

COPY solaredge_optimizers.py /app/

EXPOSE 8126

CMD ["/app/run.sh"]
