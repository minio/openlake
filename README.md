# Openlake

Welcome to the Openlake repository! In this repository, we will guide you through the steps to build a Data Lake using open source tools like Spark, Kafka, Trino, Apache Iceberg, Airflow, and other tools deployed in Kubernetes with MinIO as the object store.

## What is a Data Lake?

A Data Lake is a centralized repository that allows you to store all your structured, semi-structured, and unstructured data at any scale. It enables you to break down data silos and create a single source of truth for all your data, which can then be used for various analytical purposes.

## Prerequisites

Before you get started, you will need the following:


* A Kubernetes cluster: You will need a Kubernetes cluster to deploy the various tools required for building a Data Lake. If you don't have a Kubernetes cluster, you can set one up using tools like [kubeadm](https://kubernetes.io/docs/reference/setup-tools/kubeadm/)/[kind](https://kind.sigs.k8s.io/)/[minikube](https://minikube.sigs.k8s.io/docs/) or a managed Kubernetes service like Google Kubernetes Engine (GKE) or Amazon Elastic Kubernetes Service (EKS)
* [kubectl](https://kubernetes.io/docs/reference/kubectl/): Command line tool for communicating with Kubernetes cluster
* [A MinIO instance](https://min.io/download#/kubernetes): You will need a MinIO instance to use as the object store for your Data Lake
* [MinIO Client(mc)](https://min.io/docs/minio/linux/reference/minio-mc.html): You will need mc to run commands to peform actions in MinIo
* A working knowledge of Kubernetes: You should have a basic understanding of Kubernetes concepts and how to interact with a Kubernetes cluster using kubectl
* Familiarity with the tools used in this repo: You should have a basic understanding of the tools used in this repo, including Spark, Kafka, Trino, Apache Iceberg etc.
* [JupyterHub/ Notebook](https://jupyter.org/install) (Optional): If you are palnning to walkthrough the instructions using Notebooks

## Table of Contents
- [Apache Spark](#apache-spark)
   - [Setup Spark on K8s](#setup-spark-on-k8s)
   - [Run Spark Jobs with MinIO as Object Storage](#run-spark-jobs-with-minio-as-object-storage)
   - [Maintain Iceberg Table using Spark](#maintain-iceberg-table-using-spark)
- [Dremio](#dremio)
   - [Setup Dremio on K8s](#setup-dremio-on-k8s)
   - [Access datasets/iceberg tables in MinIO using Dremio](#access-minio-using-dremio)
- [Apache Kafka](#apache-kafka)
   - [Setup Kafka on K8s](#setup-kafka-on-k8s)
   - [Store Kafka Topics in MinIO](#store-kafka-topics-in-minio)
   - [Kafka Schema Registry and Iceberg Table (experimental)](#kafka-schema-registry-and-iceberg-table-experimental)
- [Kafka Spark Structured Streaming](#kafka-spark-structured-streaming)
   - [Spark Structured Streaming](#spark-structured-streaming)
   - [End-to-End Spark Structured Streaming for Kafka Topics](#end-to-end-spark-structured-streaming-for-kafka)


## Apache Spark

In this section we will cover 
* Setup spark on Kubernetes using spark-operator
* Run spark jobs with MinIO as object storage
* Use different type of S3A Committers, checkpoints and why running spark jobs on object storage (MinIO) is a much better approach than HDFS.
* Peform CRUD operations on Apache Iceberg table using Spark
* Spark Streaming


### Setup Spark on k8s
To run spark jobs on kubernetes we will use [spark-operator](https://github.com/GoogleCloudPlatform/spark-on-k8s-operator). You can follow the complete walkthrough [here](spark/setup-spark-operator.md) or use the [notebook](spark/setup-spark-operator.ipynb)

### Run Spark Jobs with MinIO as Object Storage
Reading and writing data from and to MinIO using spark is very easy. You can follow the complete walkthrough [here](spark/spark-with-minio.md) or use the [notebook](spark/spark-with-minio.ipynb)

### Maintain Iceberg Table using Spark
Apache Iceberg is a table format for huge analytic datasets. It supports ACID transactions, scalable metadata handling, and fast snapshot isolation. You can follow the complete walkthrough using the [notebook](spark/spark-iceberg-minio.ipynb)

## Dremio
Dremio is a general purpose engine that enables you to query data from multiple sources, including object stores, relational databases, and data lakes.
In this section we will cover
* Setup Dremio on Kubernetes using Helm
* Run Dremio queries with MinIO as object storage and Iceberg tables

### Setup Dremio on K8s
To setup Dremio on kubernetes we will use [Helm](https://helm.sh/). You can follow the complete walkthrough using the [notebook](dremio/setup-dremio.ipynb)

### Access MinIO using Dremio
You can access datasets or Iceberg tables stored in MinIO using Dremio by adding a new source. You can follow the complete walkthrough using the [notebook](dremio/dremio-minio-iceberg.ipynb)

## Apache Kafka
Apache Kafka is a distributed streaming platform. It is used for building real-time data pipelines and streaming apps. It is horizontally scalable, fault-tolerant, fast, and runs in production in thousands of companies. In this section we will cover how to setup Kafka on Kubernetes and store Kafka topics in MinIO.

### Setup Kafka on K8s
To setup Kafka on kubernetes we will use [Strimzi](https://strimzi.io/). You can follow the complete walkthrough using the [notebook](kafka/setup-kafka.ipynb)

### Store Kafka Topics in MinIO
You can store Kafka topics in MinIO using Sink connectors. You can follow the complete walkthrough using the [notebook](kafka/kafka-minio.ipynb)

### Kafka Schema Registry and Iceberg Table (experimental)
You can use Kafka Schema Registry to store schemas for data management for kafka topics and you can als use them to create Iceberg tables (expreimental). You can follow the complete walkthrough using the [notebook](kafka/kafka-schema-registry-minio.ipynb)

## Kafka Spark Structured Streaming
In this section we will cover how to use Spark Structured Streaming to read data from Kafka topics and write to MinIO.

### Spark Structured Streaming
Spark Structured Streaming is a scalable and fault-tolerant stream processing engine built on the Spark SQL engine. You can follow the complete walkthrough using the [notebook](spark/spark-streaming.ipynb)

### End-to-End Spark Structured Streaming for Kafka
You can use Spark Structured Streaming to read data from Kafka topics and write to MinIO. You can follow the complete walkthrough using the [notebook](spark/end-to-end-spark-structured-streaming-kafka.ipynb)

## Join Community

Openlake is a MinIO project. You can contact the authors over the slack channel:

- [MinIO Slack](https://join.slack.com/t/minio/shared_invite/zt-wjdzimbo-apoPb9jEi5ssl2iedx6MoA)

## License

Openlake is released under GNU AGPLv3 license. Please refer to the [LICENSE](LICENSE) document for a complete copy of the license.
