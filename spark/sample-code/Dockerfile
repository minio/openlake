FROM openlake/spark-py:3.3.2

USER root

WORKDIR /app

RUN pip3 install pyspark==3.3.2

# Add avro dependency
ADD https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar $SPARK_HOME/jars
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.12/3.3.2/spark-avro_2.12-3.3.2.jar $SPARK_HOME/jars

COPY src/*.py .
