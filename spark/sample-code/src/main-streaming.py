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
