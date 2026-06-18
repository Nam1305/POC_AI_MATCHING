#!/bin/bash

PORT=8000

start() {
    echo "Đang khởi động server tại port $PORT..."
    # Tắt process cũ nếu có
    fuser -k $PORT/tcp > /dev/null 2>&1
    # Chạy uvicorn
    .venv/bin/uvicorn app.main:app --reload --port $PORT
}

stop() {
    echo "Đang tắt server tại port $PORT..."
    fuser -k $PORT/tcp > /dev/null 2>&1
    echo "Đã tắt."
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Sử dụng: ./run.sh {start|stop}"
        exit 1
esac
