# End to End Spark Structured Streaming for Kafka Topcis

In the previous [notebook](spark-streaming.ipynb) we saw how to consume kafka events in Spark's structured streaming, in this Notebook we will look at how to create Kafka topic events and consume them into MinIO end to end with Spark's structured streaming without using the Kafka produceres or connectors

### Prerequisites

Before we get started we need the following ready

1. [Kafka](../kafka/setup-kafka.ipynb)
2. [Kafka Schema Registry](../kafka/kafka-schema-registry-minio.ipynb)
3. [Spark Operator](setup-spark-operator.ipynb)
4. MinIO cluster

After we have the above prerequisites ready we will do the following

* Modify Kafka Topic Partion
* Spark Structured Streaming Consumer
* Spark Structured Streaming Producer



### Modify Kafka Topic Partition

In order for us to gain full parallelization capabilities from Spark we will need to modify the `nyc-avro-topic` kafka topic partitions to `10` so that Spark Structured streaming 10 workers can pull data from Kafka simultaneously as show below.


```python
%%writefile sample-code/spark-job/kafka-nyc-avro-topic.yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: nyc-avro-topic
  namespace: kafka
  labels:
    strimzi.io/cluster: my-kafka-cluster
spec:
  partitions: 10
  replicas: 3
```

    Overwriting sample-code/spark-job/kafka-nyc-avro-topic.yaml



```python
!kubectl apply -f sample-code/spark-job/kafka-nyc-avro-topic.yaml
```

**Note**: Before you apply the above change it is highly recommended to delete the `nyc-avro-topic` if it already exists based on the run from previous notebooks

### Spark Structured Streaming Consumer


```python
%%writefile sample-code/src/main-streaming-spark-consumer.py
import os
from pyspark import SparkConf
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.types import StructType, StructField, LongType, DoubleType, StringType
import json

conf = (
    SparkConf()
    .set("spark.sql.streaming.checkpointFileManagerClass", "io.minio.spark.checkpoint.S3BasedCheckpointFileManager")
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()


def load_config(spark_context: SparkContext):
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.access.key", "openlakeuser")
    spark_context._jsc.hadoopConfiguration().set("fs.defaultFS", "s3://warehouse-v")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.secret.key", "openlakeuser")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.endpoint", "opl.ic.min.dev")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "true")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.attempts.maximum", "1")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.establish.timeout", "5000")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "10000")


load_config(spark.sparkContext)

schema = StructType([
    StructField('VendorID', LongType(), True),
    StructField('tpep_pickup_datetime', StringType(), True),
    StructField('tpep_dropoff_datetime', StringType(), True),
    StructField('passenger_count', DoubleType(), True),
    StructField('trip_distance', DoubleType(), True),
    StructField('RatecodeID', DoubleType(), True),
    StructField('store_and_fwd_flag', StringType(), True),
    StructField('PULocationID', LongType(), True),
    StructField('DOLocationID', LongType(), True),
    StructField('payment_type', LongType(), True),
    StructField('fare_amount', DoubleType(), True),
    StructField('extra', DoubleType(), True),
    StructField('mta_tax', DoubleType(), True),
    StructField('tip_amount', DoubleType(), True),
    StructField('tolls_amount', DoubleType(), True),
    StructField('improvement_surcharge', DoubleType(), True),
    StructField('total_amount', DoubleType(), True)])

value_schema_dict = {
    "type": "record",
    "name": "nyc_avro_test",
    "fields": [
        {
            "name": "VendorID",
            "type": "long"
        },
        {
            "name": "tpep_pickup_datetime",
            "type": "string"
        },
        {
            "name": "tpep_dropoff_datetime",
            "type": "string"
        },
        {
            "name": "passenger_count",
            "type": "double"
        },
        {
            "name": "trip_distance",
            "type": "double"
        },
        {
            "name": "RatecodeID",
            "type": "double"
        },
        {
            "name": "store_and_fwd_flag",
            "type": "string"
        },
        {
            "name": "PULocationID",
            "type": "long"
        },
        {
            "name": "DOLocationID",
            "type": "long"
        },
        {
            "name": "payment_type",
            "type": "long"
        },
        {
            "name": "fare_amount",
            "type": "double"
        },
        {
            "name": "extra",
            "type": "double"
        },
        {
            "name": "mta_tax",
            "type": "double"
        },
        {
            "name": "tip_amount",
            "type": "double"
        },
        {
            "name": "tolls_amount",
            "type": "double"
        },
        {
            "name": "improvement_surcharge",
            "type": "double"
        },
        {
            "name": "total_amount",
            "type": "double"
        },
    ]
}

stream_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", 
            os.getenv("KAFKA_BOOTSTRAM_SERVER","my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")) \
    .option("subscribe", "nyc-avro-topic") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("minPartitions", "10") \
    .option("mode", "PERMISSIVE") \
    .option("truncate", False) \
    .option("newRows", 100000) \
    .load()

stream_df.printSchema()

taxi_df = stream_df.select(from_avro("value", json.dumps(value_schema_dict)).alias("data")).select("data.*")

taxi_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .trigger(processingTime='1 second') \
    .option("path", "s3a://warehouse-v/k8/spark-stream/") \
    .option("checkpointLocation", "s3a://warehouse-v/k8/checkpoint") \
    .start() \
    .awaitTermination()

```

    Overwriting sample-code/src/main-streaming-spark-consumer.py


As you can see from the above code there is a slight change in the code

```python
taxi_df = stream_df.select(from_avro("value", json.dumps(value_schema_dict)).alias("data")).select("data.*")

taxi_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .trigger(processingTime='1 second') \
    .option("path", "s3a://warehouse-v/k8/spark-stream/") \
    .option("checkpointLocation", "s3a://warehouse-v/k8/checkpoint") \
    .start() \
    .awaitTermination()
```

The Avro is based on the Spark implementation so no need for Confluence dependency and skip the first 6 bits like we did earlier. We also added a `1 second` delay before polling for kafka events each time 


```python
%%writefile sample-code/Dockerfile
FROM openlake/spark-py:3.3.2

USER root

WORKDIR /app

RUN pip3 install pyspark==3.3.2

# Add avro dependency
ADD https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar $SPARK_HOME/jars
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.12/3.3.2/spark-avro_2.12-3.3.2.jar $SPARK_HOME/jars

COPY src/*.py .
```

    Overwriting sample-code/Dockerfile


Build the Docker image with the above code or use `openlake/sparkjob-demo:3.3.2`


```python
%%writefile sample-code/spark-job/sparkjob-streaming-consumer.yaml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: spark-stream-optimized
  namespace: spark-operator
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: "openlake/sparkjob-demo:3.3.2"
  imagePullPolicy: Always
  mainApplicationFile: local:///app/main-streaming-spark-consumer.py
  sparkVersion: "3.3.2"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 1
    onFailureRetryInterval: 10
    onSubmissionFailureRetries: 5
    onSubmissionFailureRetryInterval: 20
  driver:
    cores: 3
    memory: "2048m"
    labels:
      version: 3.3.2
    serviceAccount: my-release-spark
    env:
      - name: AWS_REGION
        value: us-east-1
      - name: AWS_ACCESS_KEY_ID
        value: openlakeuser
      - name: AWS_SECRET_ACCESS_KEY
        value: openlakeuser
  executor:
    cores: 1
    instances: 10
    memory: "1024m"
    labels:
      version: 3.3.2
    env:
      - name: AWS_REGION
        value: us-east-1
      - name: AWS_ACCESS_KEY_ID
        value: openlakeuser
      - name: AWS_SECRET_ACCESS_KEY
        value: openlakeuser

```

    Writing sample-code/spark-job/sparkjob-streaming-consumer.yaml


### Spark Structured Streaming Producer

Now that we have the kafka topic configured correctly, let create a Kafka Producer using Spark Structured Streaming as shown below


```python
%%writefile sample-code/src/spark-streaming-kafka-producer.py
import json
from io import BytesIO
import os
import avro.schema
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import to_avro
from pyspark.sql.functions import struct
from pyspark.sql.types import StructType, StructField, LongType, DoubleType, StringType

spark = SparkSession.builder.getOrCreate()


def serialize_avro(data, schema):
    writer = avro.io.DatumWriter(schema)
    bytes_writer = BytesIO()
    encoder = avro.io.BinaryEncoder(bytes_writer)
    writer.write(data, encoder)
    return bytes_writer.getvalue()


def load_config(spark_context: SparkContext):
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.access.key", "openlakeuser")
    spark_context._jsc.hadoopConfiguration().set("fs.defaultFS", "s3://warehouse-v")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.secret.key", "openlakeuser")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.endpoint", "opl.ic.min.dev")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "true")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.attempts.maximum", "1")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.establish.timeout", "5000")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "10000")


load_config(spark.sparkContext)

schema = StructType([
    StructField('VendorID', LongType(), True),
    StructField('tpep_pickup_datetime', StringType(), True),
    StructField('tpep_dropoff_datetime', StringType(), True),
    StructField('passenger_count', DoubleType(), True),
    StructField('trip_distance', DoubleType(), True),
    StructField('RatecodeID', DoubleType(), True),
    StructField('store_and_fwd_flag', StringType(), True),
    StructField('PULocationID', LongType(), True),
    StructField('DOLocationID', LongType(), True),
    StructField('payment_type', LongType(), True),
    StructField('fare_amount', DoubleType(), True),
    StructField('extra', DoubleType(), True),
    StructField('mta_tax', DoubleType(), True),
    StructField('tip_amount', DoubleType(), True),
    StructField('tolls_amount', DoubleType(), True),
    StructField('improvement_surcharge', DoubleType(), True),
    StructField('total_amount', DoubleType(), True)])

value_schema_dict = {
    "type": "record",
    "name": "nyc_avro_test",
    "fields": [
        {
            "name": "VendorID",
            "type": "long"
        },
        {
            "name": "tpep_pickup_datetime",
            "type": "string"
        },
        {
            "name": "tpep_dropoff_datetime",
            "type": "string"
        },
        {
            "name": "passenger_count",
            "type": "double"
        },
        {
            "name": "trip_distance",
            "type": "double"
        },
        {
            "name": "RatecodeID",
            "type": "double"
        },
        {
            "name": "store_and_fwd_flag",
            "type": "string"
        },
        {
            "name": "PULocationID",
            "type": "long"
        },
        {
            "name": "DOLocationID",
            "type": "long"
        },
        {
            "name": "payment_type",
            "type": "long"
        },
        {
            "name": "fare_amount",
            "type": "double"
        },
        {
            "name": "extra",
            "type": "double"
        },
        {
            "name": "mta_tax",
            "type": "double"
        },
        {
            "name": "tip_amount",
            "type": "double"
        },
        {
            "name": "tolls_amount",
            "type": "double"
        },
        {
            "name": "improvement_surcharge",
            "type": "double"
        },
        {
            "name": "total_amount",
            "type": "double"
        },
    ]
}

value_schema_str = json.dumps(value_schema_dict)

df = spark.read.option("header", "true").schema(schema).csv(
    os.getenv("INPUT_PATH", "s3a://openlake/spark/sample-data/taxi-data.csv"))
df = df.select(to_avro(struct([df[x] for x in df.columns]), value_schema_str).alias("value"))

df.write \
    .format("kafka") \
    .option("kafka.bootstrap.servers", 
            os.getenv("KAFKA_BOOTSTRAM_SERVER", "my-kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")) \
    .option("flushInterval", "100ms") \
    .option("key.serializer", "org.apache.kafka.common.serialization.StringSerializer") \
    .option("value.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer") \
    .option("schema.registry.url",
            os.getenv("KAFKA_SCHEMA_REGISTRY", "http://kafka-schema-registry-cp-schema-registry.kafka.svc.cluster.local:8081")) \
    .option("topic", "nyc-avro-topic") \
    .save()

```

    Writing sample-code/src/spark-streaming-kafka-producer.py


In the above code we read the `taxi-data.csv` data from MinIO bucket in this block

```python
df = spark.read.option("header", "true").schema(schema).csv(
    os.getenv("INPUT_PATH", "s3a://openlake/spark/sample-data/taxi-data.csv"))
```

We transform the dataframe to avor in this code block

```python
df = df.select(to_avro(struct([df[x] for x in df.columns]), value_schema_str).alias("value"))
```

Finally we write the Kafka events for the topic `nyc-avro-topic` using the following block to `my-kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092` kafka server and this `http://kafka-schema-registry-cp-schema-registry.kafka.svc.cluster.local:8081` kafka schema registry URL


```python
df.write \
    .format("kafka") \
    .option("kafka.bootstrap.servers", 
            os.getenv("KAFKA_BOOTSTRAM_SERVER", "my-kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")) \
    .option("flushInterval", "100ms") \
    .option("key.serializer", "org.apache.kafka.common.serialization.StringSerializer") \
    .option("value.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer") \
    .option("schema.registry.url",
            os.getenv("KAFKA_SCHEMA_REGISTRY", "http://kafka-schema-registry-cp-schema-registry.kafka.svc.cluster.local:8081")) \
    .option("topic", "nyc-avro-topic") \
    .save()
```

Build the Docker image with the above code or use `openlake/sparkjob-demo:3.3.2`


```python
%%writefile sample-code/spark-job/sparkjob-kafka-producer.yaml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: kafka-stream-producer
  namespace: spark-operator
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: "openlake/sparkjob-demo:3.3.2"
  imagePullPolicy: Always
  mainApplicationFile: local:///app/spark-streaming-kafka-producer.py
  sparkVersion: "3.3.2"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 3
    onFailureRetryInterval: 10
    onSubmissionFailureRetries: 5
    onSubmissionFailureRetryInterval: 20
  driver:
    cores: 3
    # coreLimit: "1200m"
    memory: "2048m"
    labels:
      version: 3.3.2
    serviceAccount: my-release-spark
    env:
      - name: INPUT_PATH
        value: "s3a://openlake/spark/sample-data/taxi-data.csv"
      - name: AWS_REGION
        value: us-east-1
      - name: AWS_ACCESS_KEY_ID
        value: openlakeuser
      - name: AWS_SECRET_ACCESS_KEY
        value: openlakeuser
  executor:
    cores: 1
    instances: 10
    memory: "1024m"
    labels:
      version: 3.3.2
    env:
      - name: INPUT_PATH
        value: "s3a://openlake/spark/sample-data/taxi-data.csv"
      - name: AWS_REGION
        value: us-east-1
      - name: AWS_ACCESS_KEY_ID
        value: openlakeuser
      - name: AWS_SECRET_ACCESS_KEY
        value: openlakeuser

```

    Overwriting sample-code/spark-job/sparkjob-kafka-producer.yaml



```python
!kubectl apply -f sample-code/spark-job/sparkjob-kafka-producer.yaml
```

Based on the configs we have setup with 10 partitions for `nyc-avro-topic` and 10 executors from spark Kafka prodcucer and consumer all the `~112M` rows is streamed and consumed in less than 10mins from the original ~3hrs from the previous kafka/spark streaming notebooks. This is a big performance gain and can be crucial based on the type of application that you want to build. 

**Note**: If we did not apply the `10 partitions` change in the `nyc-avro-topic` spark producer will still be able to complete in `<10 min` but the consumer will still take time to complete based on the number of partitions in the topic level.

### Performance Benchmarks

If we measured the number of S3 API calls made by Spark structured streaming consumer alone we will get the below numbers


```
API                             RX      TX      CALLS   ERRORS
s3.CompleteMultipartUpload      7.5 KiB 7.3 KiB 16      0       
s3.DeleteMultipleObjects        22 KiB  6.8 KiB 60      0       
s3.HeadObject                   51 KiB  0 B     200     0       
s3.ListObjectsV1                1.5 KiB 9.0 KiB 6       0       
s3.ListObjectsV2                15 KiB  20 KiB  60      0       
s3.NewMultipartUpload           4.1 KiB 6.1 KiB 16      0       
s3.PutObject                    1.1 GiB 0 B     63      0       
s3.PutObjectPart                1.2 GiB 0 B     32      0       

Summary:

Total: 453 CALLS, 2.4 GiB RX, 49 KiB TX - in 160.71s
```

The same if done without the MinIO's checkpoint mananger we will end up with the below numbers

```
API                             RX      TX      CALLS   ERRORS
s3.CompleteMultipartUpload      6.1 KiB 5.9 KiB 13      0       
s3.CopyObject                   6.1 KiB 4.1 KiB 18      0       
s3.DeleteMultipleObjects        30 KiB  8.8 KiB 78      0       
s3.DeleteObject                 4.6 KiB 0 B     18      0       
s3.HeadObject                   110 KiB 0 B     432     0       
s3.ListObjectsV2                63 KiB  124 KiB 248     0       
s3.NewMultipartUpload           3.3 KiB 4.9 KiB 13      0       
s3.PutObject                    1.3 GiB 0 B     66      0       
s3.PutObjectPart                1.1 GiB 0 B     26      0       

Summary:

Total: 912 CALLS, 2.3 GiB RX, 147 KiB TX - in 166.55s
```

We can clearly see the signigicant performance improvements with the end-to-end Spark structured streaming for kafka producer and consumer and with `MinIO's checkpoint manager` we further enhanced the performance by reducing the number of S3 API calls. 

Further if the above sample code was run on a `versioned bucket` and if we did a `mc ls --versions --recursive opl/warehouse-v/k8 --summarize` we will end up with `84 objects` vs `140 objects` between MinIO's checkpoint manager vs the default checkpoint manager respectively which again doesn't cleanup the delete markers.


