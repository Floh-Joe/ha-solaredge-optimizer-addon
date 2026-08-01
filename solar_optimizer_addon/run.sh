#!/bin/sh

export SE_USERNAME="${SE_USERNAME}"
export SE_PASSWORD="${SE_PASSWORD}"

while true; do
    printf "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" > /tmp/response.txt
    python3 /app/solaredge_optimizers.py >> /tmp/response.txt
    nc -l -p 8126 < /tmp/response.txt
done
