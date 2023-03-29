import logging
import os
from pyspark import SparkConf
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, LongType, DoubleType, StringType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MinIOSparkJob")


# adding iceberg configs
conf = (
    SparkConf()
    .set("spark.sql.extensions", 
         "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") # Use Iceberg with Spark
    .set("spark.sql.catalog.demo", "org.apache.iceberg.spark.SparkCatalog")
    .set("spark.sql.catalog.demo.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .set("spark.sql.catalog.demo.warehouse", "s3a://warehouse/")
    .set("spark.sql.catalog.demo.s3.endpoint", "https://play.min.io:50000")
    .set("spark.sql.defaultCatalog", "demo") # Name of the Iceberg catalog
    .set("spark.sql.catalogImplementation", "in-memory")
    .set("spark.sql.catalog.demo.type", "hadoop") # Iceberg catalog type
    .set("spark.executor.heartbeatInterval", "300000")
    .set("spark.network.timeout", "400000")
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Disable below line to see INFO logs
spark.sparkContext.setLogLevel("ERROR")


def load_config(spark_context: SparkContext):
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.access.key", os.getenv("AWS_ACCESS_KEY_ID", "openlakeuser"))
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.secret.key",
                                                 os.getenv("AWS_SECRET_ACCESS_KEY", "openlakeuser"))
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.endpoint", os.getenv("ENDPOINT", "play.min.io:50000"))
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "true")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.attempts.maximum", "1")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.establish.timeout", "5000")
    spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "10000")


load_config(spark.sparkContext)

# Define schema for NYC Taxi Data
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

# Read CSV file from MinIO
df = spark.read.option("header", "true").schema(schema).csv(
    os.getenv("INPUT_PATH", "s3a://openlake/spark/sample-data/taxi-data.csv"))

# Create Iceberg table "nyc.taxis_large" from RDD
df.write.mode("overwrite").saveAsTable("nyc.taxis_large")

# Query table row count
count_df = spark.sql("SELECT COUNT(*) AS cnt FROM nyc.taxis_large")
total_rows_count = count_df.first().cnt
logger.info(f"Total Rows for NYC Taxi Data: {total_rows_count}")

# Rename column "fare_amount" in nyc.taxis_large to "fare"
spark.sql("ALTER TABLE nyc.taxis_large RENAME COLUMN fare_amount TO fare")

# Rename column "trip_distance" in nyc.taxis_large to "distance"
spark.sql("ALTER TABLE nyc.taxis_large RENAME COLUMN trip_distance TO distance")

# Add description to the new column "distance"
spark.sql(
    "ALTER TABLE nyc.taxis_large ALTER COLUMN distance COMMENT 'The elapsed trip distance in miles reported by the taximeter.'")

# Move "distance" next to "fare" column
spark.sql("ALTER TABLE nyc.taxis_large ALTER COLUMN distance AFTER fare")

# Add new column "fare_per_distance" of type float
spark.sql("ALTER TABLE nyc.taxis_large ADD COLUMN fare_per_distance FLOAT AFTER distance")

# Check the snapshots available
snap_df = spark.sql("SELECT * FROM nyc.taxis_large.snapshots")
snap_df.show()  # prints all the available snapshots (1 till now)

# Populate the new column "fare_per_distance"
logger.info("Populating fare_per_distance column...")
spark.sql("UPDATE nyc.taxis_large SET fare_per_distance = fare/distance")

# Check the snapshots available
logger.info("Checking snapshots...")
snap_df = spark.sql("SELECT * FROM nyc.taxis_large.snapshots")
snap_df.show()  # prints all the available snapshots (2 now) since previous operation will create a new snapshot

# Qurey the table to see the results
res_df = spark.sql("""SELECT VendorID
                            ,tpep_pickup_datetime
                            ,tpep_dropoff_datetime
                            ,fare
                            ,distance
                            ,fare_per_distance
                            FROM nyc.taxis_large LIMIT 15""")
res_df.show()

# Delete rows from "fare_per_distance" based on criteria
logger.info("Deleting rows from fare_per_distance column...")
spark.sql("DELETE FROM nyc.taxis_large WHERE fare_per_distance > 4.0 OR distance > 2.0")
spark.sql("DELETE FROM nyc.taxis_large WHERE fare_per_distance IS NULL")

# Check the snapshots available
logger.info("Checking snapshots...")
snap_df = spark.sql("SELECT * FROM nyc.taxis_large.snapshots")
snap_df.show()  # prints all the available snapshots (4 now) since previous operations will create 2 new snapshots

# Query table row count
count_df = spark.sql("SELECT COUNT(*) AS cnt FROM nyc.taxis_large")
total_rows_count = count_df.first().cnt
logger.info(f"Total Rows for NYC Taxi Data after delete operations: {total_rows_count}")

# Partition table based on "VendorID" column
logger.info("Partitioning table based on VendorID column...")
spark.sql("ALTER TABLE nyc.taxis_large ADD PARTITION FIELD VendorID")

# Query Metadata tables like snapshot, files, history
logger.info("Querying Snapshot table...")
snapshots_df = spark.sql("SELECT * FROM nyc.taxis_large.snapshots ORDER BY committed_at")
snapshots_df.show()  # shows all the snapshots in ascending order of committed_at column

logger.info("Querying Files table...")
files_count_df = spark.sql("SELECT COUNT(*) AS cnt FROM nyc.taxis_large.files")
total_files_count = files_count_df.first().cnt
logger.info(f"Total Data Files for NYC Taxi Data: {total_files_count}")

spark.sql("""SELECT file_path, 
                    file_format, 
                    record_count, 
                    null_value_counts, 
                    lower_bounds, 
                    upper_bounds 
                    FROM nyc.taxis_large.files LIMIT 1""").show()

# Query history table
logger.info("Querying History table...")
hist_df = spark.sql("SELECT * FROM nyc.taxis_large.history")
hist_df.show()

# Time travel to initial snapshot
logger.info("Time Travel to initial snapshot...")
snap_df = spark.sql("SELECT snapshot_id FROM nyc.taxis_large.history LIMIT 1")
spark.sql(f"CALL demo.system.rollback_to_snapshot('nyc.taxis_large', {snap_df.first().snapshot_id})")

# Qurey the table to see the results
res_df = spark.sql("""SELECT VendorID
                            ,tpep_pickup_datetime
                            ,tpep_dropoff_datetime
                            ,fare
                            ,distance
                            ,fare_per_distance
                            FROM nyc.taxis_large LIMIT 15""")
res_df.show()

# Query history table
logger.info("Querying History table...")
hist_df = spark.sql("SELECT * FROM nyc.taxis_large.history")
hist_df.show()  # 1 new row

# Query table row count
count_df = spark.sql("SELECT COUNT(*) AS cnt FROM nyc.taxis_large")
total_rows_count = count_df.first().cnt
logger.info(f"Total Rows for NYC Taxi Data after time travel: {total_rows_count}")
