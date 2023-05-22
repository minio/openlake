# Spark Structured Streaming With Kafka and MinIO

## Spark Streaming:
Apache Spark Streaming is a powerful and scalable stream processing framework that is part of the larger Apache Spark ecosystem. It allows developers to process real-time data streams in near real-time with low-latency processing. Spark Streaming provides a high-level and expressive API for processing data streams from various sources such as Kafka, Flume, Kinesis, or custom sources, and enables a wide range of use cases including real-time analytics, machine learning, fraud detection, and more. Spark Streaming follows a micro-batch processing model, where incoming data is divided into small time-based batches, processed in parallel, and the results are aggregated to generate the final output. Spark Streaming provides strong guarantees of fault-tolerance, reliability, and exactly-once processing semantics, making it a popular choice for building scalable and robust stream processing applications.

## Spark Structured Streaming:
Spark Structured Streaming is a newer addition to the Apache Spark ecosystem that provides a more advanced and unified stream processing API based on the concept of "continuous processing". Spark Structured Streaming extends the familiar DataFrame and Dataset API, which is used for batch processing in Spark, to seamlessly support processing of streaming data as well. It provides a higher-level abstraction for processing data streams, allowing developers to write stream processing code that is similar to batch processing code, making it more intuitive and user-friendly. Spark Structured Streaming offers advanced features such as built-in support for fault-tolerance, event time processing, and state management, making it a powerful and convenient choice for building scalable, reliable, and complex stream processing applications. Spark Structured Streaming also provides tight integration with the larger Apache Spark ecosystem, enabling seamless integration with other Spark modules for end-to-end data processing pipelines that span batch and streaming data.

Structured Streaming is the way to go for modern stream processing needs because:

* It's a true streaming model with continuous processing, as opposed to the micro-batch model of Spark Streaming.
* It has a much richer API and set of stream processing features by leveraging Spark SQL.
* It has stronger fault tolerance and consistency guarantees. Data loss is prevented through checkpointing and recovery.
* It supports event-time based processing and reasoning about data across time.
* The API is higher-level and easier to work with versus the lower-level DStreams API.

Structured Streaming is the future of stream processing with Spark and where continued investment and improvements are being made. So for any new streaming application, it is highly recommend to start with Structured Streaming.


In this Notebook we will explore how to process events streamed from Kafka in Spark Structured Streaming. We will also explore why we highly recommend to use [MinIO checkpointer](https://github.com/minio/spark-streaming-checkpoint) and show the significant performance improvements it has to offer. We will also explore how to save event data from Kafka directly as Iceberg Table into MinIO. If you haven't setup Kafka yet take a look at this [Notebook](../kafka/setup-kafka.ipynb), if you haven't already setup the Kafka topic `nyc-avro-topic` and producing events using `avro-producer` follow the [Kafka Schema Registry Notebook](../kafka/kafka-schema-registry-minio.ipynb)

## PySpark Structured Streaming Application

Below we will write a simple pyspark application that will continuously stream events for the topic `nyc-avro-topic` from Kafka and process each record and saves it as `parquet` files into MinIO.

**Note**: Here we will assume that that the Kafka, schema registry, kafka topic `nyc-avro-topic` and the Avro producer is up and running. You can refer to this [Notebook](../kafka/kafka-schema-registry-minio.ipynb#Producer-with-Avro-Schema)


```python
%%writefile sample-code/src/main-streaming.py
from pyspark import SparkConf
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.types import StructType, StructField, LongType, DoubleType, StringType
import json

spark = SparkSession.builder.getOrCreate()

# Hadoop configs to connect with MinIO
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


# Avro Schema used to deserialize data from Kafka
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
    .option("kafka.bootstrap.servers", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092") \
    .option("subscribe", "nyc-avro-topic") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("mode", "PERMISSIVE") \
    .option("truncate", False) \
    .option("newRows", 100000) \
    .load()

stream_df.printSchema()

# special pre-processing to ignore first 6 bits for Confluent Avro data stream topics
taxi_df = stream_df.selectExpr("substring(value, 6) as avro_value").select(
    from_avro("avro_value", json.dumps(value_schema_dict)).alias("data")).select("data.*")


taxi_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .trigger(processingTime='1 minute') \
    .option("path", "s3a://warehouse-v/k8/spark-stream/") \
    .option("checkpointLocation", "s3a://warehouse-v/k8/checkpoint") \
    .start() \
    .awaitTermination()

```

    Overwriting sample-code/src/main-streaming.py


In the above code:
`load_config` has all the hadoop configs required for spark to connect with `MinIO` to read/write data. 

`value_schema_dict` has the Avro schema based on which Spark will deserialize data from kafka

#### Spark Stream setup

```python
stream_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092") \
    .option("subscribe", "nyc-avro-topic") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("mode", "PERMISSIVE") \
    .option("truncate", False) \
    .option("newRows", 100000) \
    .load()
```

In the above snipped we specify spark stream format to `kafka` and some of the key options we included are:

`kafka.bootstrap.servers` - Kafka server endpoint from which to consume the events from

`subscribe` - list of comma seperated strings pointing to the topics which the Spark stream will process, in our case it is `nyc-avro-topic`

`startingOffsets` -  specifies from when Spark Stream should start processing the events for the subscribed topics, in our case it will be `earliest` which is beginning of time for the subscribed for the given topics


#### Preprocessing Avro data stream

```python
# special pre-processing to ignore first 6 bits for Confluent Avro data stream topics
taxi_df = stream_df.selectExpr("substring(value, 6) as avro_value").select(
    from_avro("avro_value", json.dumps(value_schema_dict)).alias("data")).select("data.*")
```

In our case since we are using Confluent Avro data stream, before we start consuming the data in Spark we need to preprocess the bytestream. The first 6bits contains the avro schema metadata which is used by confluent API in kafka by consumers/connectors in our case we can skip these bits for Spark streaming


#### Write Parquet data to MinIO

```python
taxi_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .option("path", "s3a://warehouse/k8/spark-stream/") \
    .option("checkpointLocation", "s3a://warehouse/k8/checkpoint") \
    .start() \
    .awaitTermination()
```

We open a writestream in spark that writes the preprocessed dataframe `taxi_df` to `parquet` format into MinIO in the `path` specified in the options, we also give the `checkpointLocation` which is a MinIO bucket where Spark will continuously checkpoint in case of spark job failure it will continue from where it left based on the checkpoints.


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


Build your own image or use the `openlake/sparkjob-demo:3.3.2` from dockerhub which has the above code.


```python
%%writefile sample-code/spark-job/sparkjob-streaming.yaml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: spark-stream
  namespace: spark-operator
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: "openlake/sparkjob-demo:3.3.2"
  imagePullPolicy: Always
  mainApplicationFile: local:///app/main-streaming.py
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

    Overwriting sample-code/spark-job/sparkjob-streaming.yaml



```python
!kubectl apply -f sample-code/spark-job/sparkjob-streaming.yaml
```

    sparkapplication.sparkoperator.k8s.io/spark-stream created


**Note**: Since our Kafka Consumer approximately runs for 3hrs to stream all the `112M` rows, Spark structured streaming will also take close to same time when both the producer and consumer are started at the same time.

### Performance Benchmarks

If we measured the number of S3 API calls made by Spark structured streaming consumer alone we will get the below numbers

```
API                             RX      TX      CALLS   ERRORS
s3.CopyObject                   6.7 MiB 4.5 MiB 20220   0
s3.DeleteMultipleObjects        11 MiB  3.0 MiB 26938   0
s3.DeleteObject                 9.9 MiB 0 B     39922   0
s3.GetObject                    1.8 MiB 496 MiB 6736    0
s3.HeadObject                   84 MiB  0 B     336680  0
s3.ListObjectsV2                60 MiB  1.6 GiB 241903  0
s3.PutObject                    2.3 GiB 0 B     26975   0

Summary:

Total: 699374 CALLS, 2.5 GiB RX, 2.1 GiB TX - in 11999.80s
```

As you can see from the above table the we make approximately 700K call to the MinIO endpoint. There is a simple change that we can do to the consumer code to optimize this. If we added a `1 min` delay trigger to the consumer code instead of continuously polling for new events from Kafka we can significantly reduce the total API call. Here is the optimized code.

```python
taxi_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .trigger(processingTime='1 minute') \
    .option("path", "s3a://warehouse-v/k8/spark-stream/") \
    .option("checkpointLocation", "s3a://warehouse-v/k8/checkpoint") \
    .start() \
    .awaitTermination()
```

They Key thing to note here is `.trigger(processingTime='1 minute')` which will add a `1 min` before polling kafka events each time. Here is the number with the optimized code

```
API                             RX      TX      CALLS   ERRORS
s3.CopyObject                   207 KiB 139 KiB 614     0       
s3.DeleteMultipleObjects        335 KiB 92 KiB  812     0       
s3.DeleteObject                 235 KiB 0 B     921     0       
s3.GetObject                    54 KiB  469 KiB 199     0       
s3.HeadObject                   2.5 MiB 0 B     9867    0       
s3.ListObjectsV2                1.7 MiB 12 MiB  6910    0       
s3.PutObject                    2.0 GiB 0 B     814     0       

Summary:

Total: 20137 CALLS, 2.0 GiB RX, 13 MiB TX - in 12126.59s
```

As you can see from the above table we went from `~700K` API calls to `~20k` API calls. Just by adding a simple 1 line code change we are able to make a big changes to the number of S3 API calls.

## MinIO Checkpoint Manager

Above optimization is huge improvement, if we run the same set of code in a **versioned bucket** and after all the rows are stored into MinIO if we perform a `mc ls --versions --recursive opl/warehouse-v/k8 --summarize` you will still notice objects with `v1` and `v2` where the `v2` is delete markers for the objects that should have been deleted. This could be a huge problem as the consumer keeps ading more records over a period of time and these delete marker objects are sticky wasting storage space.

Enter [MinIO Checkpoint Manager](https://github.com/minio/spark-streaming-checkpoint) `io.minio.spark.checkpoint.S3BasedCheckpointFileManager` which take advantage of MinIO's strictly consistent atomic transactions. MinIO's Checkpoint Manager takes full advantage of the native object APIs and avoids the uncessary baggage from POSIX based implementation.

You can easily use the checkpoint manager in your code by adding this 1 line to your spark config

```python
SparkConf().set("spark.sql.streaming.checkpointFileManagerClass", "io.minio.spark.checkpoint.S3BasedCheckpointFileManager")
```

Below is the sample code that you can run to see the results


```python
%%writefile sample-code/src/main-streaming-optimized.py
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
    .option("kafka.bootstrap.servers", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092") \
    .option("subscribe", "nyc-avro-topic") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("minPartitions", "10") \
    .option("mode", "PERMISSIVE") \
    .option("truncate", False) \
    .option("newRows", 100000) \
    .load()

stream_df.printSchema()

taxi_df = stream_df.selectExpr("substring(value, 6) as avro_value").select(
    from_avro("avro_value", json.dumps(value_schema_dict)).alias("data")).select("data.*")

taxi_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .option("path", "s3a://warehouse-v/k8/spark-stream/") \
    .option("checkpointLocation", "s3a://warehouse-v/k8/checkpoint") \
    .start() \
    .awaitTermination()

```

    Overwriting sample-code/src/main-streaming-optimized.py



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


Build your own image or use the `openlake/sparkjob-demo:3.3.2` from dockerhub which has the above code.


```python
%%writefile sample-code/spark-job/sparkjob-streaming-optimized.yaml
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
  mainApplicationFile: local:///app/main-streaming-optimized.py
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

    Overwriting sample-code/spark-job/sparkjob-streaming-optimized.yaml


Deploy the optimized consumer with the new MinIO's checkpoint manager as shown below


```python
!kubectl apply -f sample-code/spark-job/sparkjob-streaming-optimized.yaml
```

### Performance Benchmarks


If we measured the number of S3 API calls made by Spark structured streaming consumer with the optimized checkpoint manager we will get the below numbers


```
API                             RX      TX      CALLS   ERRORS
s3.DeleteMultipleObjects        5.8 MiB 1.7 MiB 15801   0       
s3.DeleteObject                 12 MiB  0 B     46465   0       
s3.GetObject                    4.0 MiB 2.7 GiB 15802   0       
s3.HeadObject                   43 MiB  0 B     172825  0       
s3.ListObjectsV1                7.8 MiB 7.8 GiB 31402   0       
s3.ListObjectsV2                3.9 MiB 5.2 MiB 15782   0       
s3.PutObject                    4.7 GiB 0 B     63204   0       

Summary:

Total: 361281 CALLS, 4.8 GiB RX, 10 GiB TX - in 12160.25s
```

We can already see that we went from `~700K` API calls to `~361K` API calls, on top of this if we add the `1 min` deley before each polling we will see further improvements

```
API                             RX      TX      CALLS   ERRORS
s3.DeleteMultipleObjects        75 KiB  23 KiB  200     0       
s3.DeleteObject                 100 KiB 0 B     394     0       
s3.GetObject                    52 KiB  469 KiB 199     0       
s3.HeadObject                   508 KiB 0 B     1995    0       
s3.ListBuckets                  150 B   254 B   1       0       
s3.ListObjectsV1                75 KiB  2.8 MiB 293     0       
s3.ListObjectsV2                51 KiB  67 KiB  200     0       
s3.PutObject                    2.0 GiB 0 B     803     0       

Summary:

Total: 4085 CALLS, 2.0 GiB RX, 3.3 MiB TX - in 11945.35s
```

From `~20K` API calls earlier we are now down to `~4K` API calls. Another major improvement that we will notice on the `versioned bucket` is that no `v2 delete marker` objects are present and we only have `v1` objects. 

In this Notebook we saw in details about how to use Spark structured streaming to consume events from Kafka and some of the optimizations that can be done to reduce the S3 API calls. We also saw the benefits of using MinIO checkpoint manager and how the implementations avoids all the POSIX baggage and utilizes the native object storage strict consistency. In the next notebook we will see how to have the end-to-end Kafka producer and consumer implemented in Spark structured streaming and how that can speed up the entire flow on high events/throughput.


```python

```
