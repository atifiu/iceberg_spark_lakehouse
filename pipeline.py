from minio import Minio
from pyspark.sql import SparkSession

# Initialize MinIO client
client = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# Set up bucket in MinIO
minio_bucket = "my-first-bucket"
if not client.bucket_exists(minio_bucket):
    client.make_bucket(minio_bucket)

source_file = './data/data.csv'  # Ensure this file exists
destination_file = 'data.csv'
client.fput_object(minio_bucket, destination_file, source_file)

# Create Spark session with Iceberg and MinIO integration
iceberg_builder = SparkSession.builder \
    .appName("Iceberg Integration with MinIO") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.iceberg:iceberg-hive-runtime:1.5.0") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.spark_catalog.type", "hive") \
    .config("spark.sql.catalog.hive_catalog", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.hive_catalog.type", "hive") \
    .config("spark.sql.catalog.hive_catalog.uri", "thrift://hive-metastore:9083") \
    .config("spark.sql.catalog.hive_catalog.warehouse", f"s3a://{minio_bucket}/iceberg_data/") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .enableHiveSupport()
    
spark = iceberg_builder.getOrCreate()

# Debugging output to verify warehouse path
print("Warehouse path set to:", spark.conf.get("spark.sql.catalog.hive_catalog.warehouse"))

# Create and write data to an Iceberg table in Hive Metastore
data = [("Alice", 30), ("Bob", 25), ("Eve", 35)]
columns = ["name", "age"]
df = spark.createDataFrame(data, columns)
df.write.format("iceberg").mode("overwrite").saveAsTable("hive_catalog.default.iceberg_test")

# Read data from the Iceberg table
iceberg_df = spark.read.format("iceberg").load("hive_catalog.default.iceberg_test")
iceberg_df.show()
