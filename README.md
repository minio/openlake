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

## Join Community

Openlake is a MinIO project. You can contact the authors over the slack channel:

- [MinIO Slack](https://join.slack.com/t/minio/shared_invite/zt-wjdzimbo-apoPb9jEi5ssl2iedx6MoA)

## License

Openlake is released under GNU AGPLv3 license. Please refer to the [LICENSE](LICENSE) document for a complete copy of the license.
