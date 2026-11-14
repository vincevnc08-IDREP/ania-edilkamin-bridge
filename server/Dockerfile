FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 ANIA_TX_GAIN=10 ANIA_FIRMWARE_VERSION=13 ANIA_CAPTURE_DIR=/data/state_tests ANIA_LINK_TOKEN_FILE=/private/link.token
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY server/app/bridge.py /app/bridge.py
COPY radio/*.py /app/radio/
USER 1000:1000
CMD ["python", "bridge.py", "--host", "0.0.0.0", "--token-file", "/private/bridge.token", "--database", "/private/commands.sqlite", "--radio-path", "/app/radio"]
