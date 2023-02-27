FROM openlake/spark-py:3.3.1

USER root

WORKDIR /app

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY src/*.py .
