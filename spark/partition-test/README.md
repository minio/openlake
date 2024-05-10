# Setup
Start by running the following command to install the required dependencies.

```bash
docker-compose up -d
```

This will start the following services:
* MinIO
* PySpark Jupyter Notebook
* Postgres
* Hive Metastore

Go to [http://localhost:8888](http://localhost:8888) to access the Jupyter Notebook.

## Notebooks
* [Hive-table](notebooks/hive-table.ipynb) - Create a Hive table and query it using Spark SQL
* [Partition-committer](notebooks/partition-committer.ipynb) - Uses S3A partition Committers on top of MinIO

