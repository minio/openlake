import logging
import os

import fsspec
import pandas as pd
import s3fs
from avro.schema import make_avsc_object
from confluent_kafka.avro import AvroProducer

logging.basicConfig(level=logging.INFO)

# Avro schema
value_schema_dict = {
    "type": "record",
    "name": "nyc_avro",
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

value_schema = make_avsc_object(value_schema_dict)

producer_config = {
    "bootstrap.servers": "my-kafka-cluster-kafka-bootstrap:9092",
    "schema.registry.url": "http://kafka-schema-registry-cp-schema-registry:8081"
}

producer = AvroProducer(producer_config, default_value_schema=value_schema)

fsspec.config.conf = {
    "s3":
        {
            "key": os.getenv("AWS_ACCESS_KEY_ID", "openlakeuser"),
            "secret": os.getenv("AWS_SECRET_ACCESS_KEY", "openlakeuser"),
            "client_kwargs": {
                "endpoint_url": "https://play.min.io:50000"
            }
        }
}
s3 = s3fs.S3FileSystem()
total_processed = 0
i = 1
for df in pd.read_csv('s3a://openlake/spark/sample-data/taxi-data.csv', chunksize=10000):
    count = 0
    for index, row in df.iterrows():
        producer.produce(topic="nyc-avro-topic", value=row.to_dict())
        count += 1

    total_processed += count
    if total_processed % 10000 * i == 0:
        producer.flush()
        logging.info(f"total processed till now {total_processed} for topic 'nyc-avro-topic'")
        i += 1
