FROM python:3.11-slim

WORKDIR /app

# Ensure we have required OpenCV dependencies (GLib etc.)


COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py .

CMD ["python", "-u", "worker.py"]
