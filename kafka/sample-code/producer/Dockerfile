FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY src/avro-producer.py .
CMD ["python3", "-u", "./avro-producer.py"]
