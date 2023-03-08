# Run spark jobs with MinIO as object storage

In this Notebook we will use MinIO as object storage for Spark jobs. If you haven't already setup `spark-operator` in your Kubernetes environment follow [this](setup-spark-operator.ipynb) guide.

Reading and writing Data from and to Minio using Spark is very simple once we have the right dependencies and configurations in place.
In this post we will not be discussing the dependencies, to keep things simple we use the `openlake/spark-py:3.3.2` image that contains all the dependencies required to read and write data from Minio using Spark.

### Getting Demo Data into MinIO
We will be using the NYC Taxi dataset that is available on MinIO. You can download the dataset from [here](https://data.cityofnewyork.us/api/views/t29m-gskq/rows.csv?accessType=DOWNLOAD) which has ~112M rows and ~10GB in size. You can use any other dataset of your choice.and upload it to MinIO using the following command:


```python
!mc mb play/openlake
!mc mb play/openlake/spark
!mc mb play/openlake/spark/sample-data
!mc cp nyc-taxi-data.csv play/openlake/spark/sample-data/nyc-taxi-data.csv
```

### Sample Python Application
Let's now read and write data from MinIO using Spark. We will use the following sample python application to do that.


```python
%%writefile sample-code/src/main.py
import logging
import os

from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, LongType, DoubleType, StringType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MinIOSparkJob")

spark = SparkSession.builder.getOrCreate()


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
# Filter dataframe based on passenger_count greater than 6
large_passengers_df = df.filter(df.passenger_count > 6)

total_rows_count = df.count()
filtered_rows_count = large_passengers_df.count()
# File Output Committer is used to write the output to the destination (Not recommended for Production)
large_passengers_df.write.format("csv").option("header", "true").save(
    os.getenv("OUTPUT_PATH", "s3a://openlake-tmp/spark/nyc/taxis_small"))

logger.info(f"Total Rows for NYC Taxi Data: {total_rows_count}")
logger.info(f"Total Rows for Passenger Count > 6: {filtered_rows_count}")
```

The above application reads the NYC Taxi dataset from MinIO and filters the rows where the passenger count is greater than 6. The filtered data is then written to MinIO.

### Building the Docker Image
We will now build the docker image that contains the above python application. You can use the following Dockerfile to build the image:


```python
%%writefile sample-code/Dockerfile
FROM openlake/spark-py:3.3.2

USER root

WORKDIR /app

RUN pip3 install pyspark==3.3.2

COPY src/*.py .
```

You can build your own docker image or use the pre-build image `openlake/sparkjob-demo:3.3.2` that is available on Docker Hub.

### Deploying the MinIO Spark Application
To read and write data from MinIO using Spark, you need to create a secret that contains the MinIO access key and secret key. You can create the secret using the following command:


```python
!kubectl create secret generic minio-secret \
    --from-literal=AWS_ACCESS_KEY_ID=openlakeuser \
    --from-literal=AWS_SECRET_ACCESS_KEY=openlakeuser \
    --from-literal=ENDPOINT=minio.openlake.io \
    --from-literal=AWS_REGION=us-east-1 \
    --namespace spark-operator
```

Now that we have the secret created, we can deploy the spark application that reads and writes data from MinIO.


```python
%%writefile sample-code/spark-job/sparkjob-minio.yml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
    name: spark-minio
    namespace: spark-operator
spec:
    type: Python
    pythonVersion: "3"
    mode: cluster
    image: "openlake/sparkjob-demo:3.3.2"
    imagePullPolicy: Always
    mainApplicationFile: local:///app/main.py
    sparkVersion: "3.3.2"
    restartPolicy:
        type: OnFailure
        onFailureRetries: 3
        onFailureRetryInterval: 10
        onSubmissionFailureRetries: 5
        onSubmissionFailureRetryInterval: 20
    driver:
        cores: 1
        memory: "1024m"
        labels:
            version: 3.3.2
        serviceAccount: my-release-spark
        env:
            -   name: AWS_REGION
                value: us-east-1
            -   name: AWS_ACCESS_KEY_ID
                value: openlakeuser
            -   name: AWS_SECRET_ACCESS_KEY
                value: openlakeuser
    executor:
        cores: 1
        instances: 3
        memory: "1024m"
        labels:
            version: 3.3.2
        env:
            -   name: INPUT_PATH
                value: "s3a://openlake/spark/sample-data/taxi-data.csv"
            -   name: OUTPUT_PATH
                value: "s3a://openlake/spark/output/taxi-data-output"
            -   name: AWS_REGION
                valueFrom:
                    secretKeyRef:
                        name: minio-secret
                        key: AWS_REGION
            -   name: AWS_ACCESS_KEY_ID
                valueFrom:
                    secretKeyRef:
                        name: minio-secret
                        key: AWS_ACCESS_KEY_ID
            -   name: AWS_SECRET_ACCESS_KEY
                valueFrom:
                    secretKeyRef:
                        name: minio-secret
                        key: AWS_SECRET_ACCESS_KEY
            -   name: ENDPOINT
                valueFrom:
                    secretKeyRef:
                        name: minio-secret
                        key: ENDPOINT
```

Above Python Spark Application YAML file contains the following configurations:

* `spec.type`: The type of the application. In this case, it is a Python application.
* `spec.pythonVersion`: The version of Python used in the application.
* `spec.mode`: The mode of the application. In this case, it is a cluster mode application.
* `spec.image`: The docker image that contains the application.
* `spec.imagePullPolicy`: The image pull policy for the docker image.
* `spec.mainApplicationFile`: The path to the main application file.
* `spec.sparkVersion`: The version of Spark used in the application.
* `spec.restartPolicy`: The restart policy for the application. In this case, the application will be restarted if it fails. The application will be restarted 3 times with a 10 seconds interval between each restart. If the application fails to submit, it will be restarted 5 times with a 20 seconds interval between each restart.
* `spec.driver`: The driver configuration for the application. In this case, we are using the `my-release-spark` service account. The driver environment variables are set to read and write data from MinIO.
* `spec.executor`: The executor configuration for the application. In this case, we are using 3 executors with 1 core and 1GB of memory each. The executor environment variables are set to read and write data from MinIO.


You can deploy the application using the following command:


```python
!kubectl apply -f sample-code/spark-job/sparkjob-minio.yml
```

After the application is deployed, you can check the status of the application using the following command:


```python
!kubectl get sparkapplications -n spark-operator
```

Once the application is completed, you can check the output data in MinIO. You can use the following command to list the files in the output directory:


```python
!mc ls play/openlake/spark/output/taxi-data-output
```

You can also check the logs of the application using the following command:


```python
!kubectl logs -f spark-minio-driver -n spark-operator # stop this shell once you are done
```

There is also option for you to use the Spark UI to monitor the application. You can use the following command to port forward the Spark UI:


```python
!kubectl port-forward svc/spark-minio-ui-svc 4040:4040 -n spark-operator # stop this shell once you are done browsing
```

In your browser, you can access the Spark UI using the following URL: `http://localhost:4040`

You will see the following Spark UI:

![Spark UI](./img/spark-ui.png)

Once the application is completed, you can delete the application using the following command:


```python
!kubectl delete sparkapplications spark-minio -n spark-operator
```

Deploying a Scheduled Spark Application is almost the same as deploying a normal Spark Application. The only difference is that you need to add the `spec.schedule` field to the Spark Application YAML file and the kind is `ScheduledSparkApplication`. You can save the following application as sparkjob-minio-scheduled.yaml:


```python
%%writefile sample-code/spark-job/sparkjob-scheduled-minio.yml
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: ScheduledSparkApplication
metadata:
    name: spark-scheduled-minio
    namespace: spark-operator
spec:
    schedule: "@every 1h" # Run the application every hour
    concurrencyPolicy: Allow
    template:
        type: Python
        pythonVersion: "3"
        mode: cluster
        image: "openlake/sparkjob-demo:3.3.2"
        imagePullPolicy: Always
        mainApplicationFile: local:///app/main.py
        sparkVersion: "3.3.2"
        restartPolicy:
            type: OnFailure
            onFailureRetries: 3
            onFailureRetryInterval: 10
            onSubmissionFailureRetries: 5
            onSubmissionFailureRetryInterval: 20
        driver:
            cores: 1
            memory: "1024m"
            labels:
                version: 3.3.2
            serviceAccount: my-release-spark
            env:
                -   name: AWS_REGION
                    value: us-east-1
                -   name: AWS_ACCESS_KEY_ID
                    value: openlakeuser
                -   name: AWS_SECRET_ACCESS_KEY
                    value: openlakeuser
        executor:
            cores: 1
            instances: 3
            memory: "1024m"
            labels:
                version: 3.3.2
            env:
                -   name: INPUT_PATH
                    value: "s3a://openlake/spark/sample-data/taxi-data.csv"
                -   name: OUTPUT_PATH
                    value: "s3a://openlake/spark/output/taxi-data-output"
                -   name: AWS_REGION
                    valueFrom:
                        secretKeyRef:
                            name: minio-secret
                            key: AWS_REGION
                -   name: AWS_ACCESS_KEY_ID
                    valueFrom:
                        secretKeyRef:
                            name: minio-secret
                            key: AWS_ACCESS_KEY_ID
                -   name: AWS_SECRET_ACCESS_KEY
                    valueFrom:
                        secretKeyRef:
                            name: minio-secret
                            key: AWS_SECRET_ACCESS_KEY
                -   name: ENDPOINT
                    valueFrom:
                        secretKeyRef:
                            name: minio-secret
                            key: ENDPOINT
```

You can deploy and see the results of the application in the same way as the normal Spark Application. Above Spark Application will run every hour and will write the output to the same directory in MinIO.

All the source code for this tutorial is available in the following GitHub repository: [openlake/spark](https://github.com/minio/openlake/tree/main/spark)
