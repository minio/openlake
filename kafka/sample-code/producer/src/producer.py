import logging
import os

import fsspec
import pandas as pd
import s3fs

from kafka import KafkaProducer

logging.basicConfig(level=logging.INFO)

producer = KafkaProducer(bootstrap_servers="my-kafka-cluster-kafka-bootstrap:9092")

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
for df in pd.read_csv('s3a://openlake/spark/sample-data/taxi-data.csv', chunksize=1000):
    count = 0
    for index, row in df.iterrows():
        producer.send("my-topic", bytes(row.to_json(), 'utf-8'))
        count += 1
    producer.flush()
    total_processed += count
    if total_processed % 10000 * i == 0:
        logging.info(f"total processed till now {total_processed}")
        i += 1
