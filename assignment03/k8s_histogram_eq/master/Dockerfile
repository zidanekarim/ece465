FROM python:3.11-slim

WORKDIR /app



COPY master/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY master/main.py .
COPY frontend ./frontend

# HTTP API
EXPOSE 8000
# K8s internal TCP port for custom protocol
EXPOSE 6000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
