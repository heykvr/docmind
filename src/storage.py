import os
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.environ["MINIO_ENDPOINT"]
ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
BUCKET = os.environ["MINIO_BUCKET"]


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )


def ensure_bucket(client, bucket: str = BUCKET):
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def upload_file(client, local_path: Path, key: str, bucket: str = BUCKET):
    client.upload_file(str(local_path), bucket, key)


def list_pdf_keys(client, bucket: str = BUCKET) -> list[str]:
    paginator = client.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            if obj["Key"].lower().endswith(".pdf"):
                keys.append(obj["Key"])
    return sorted(keys)


def download_to_temp(client, key: str, bucket: str = BUCKET) -> Path:
    tmp_dir = Path(tempfile.gettempdir()) / "docmind_downloads"
    tmp_dir.mkdir(exist_ok=True)
    local_path = tmp_dir / Path(key).name
    client.download_file(bucket, key, str(local_path))
    return local_path


if __name__ == "__main__":
    client = get_client()
    ensure_bucket(client)

    data_dir = Path(__file__).parent.parent / "data"
    for pdf in sorted(data_dir.glob("*.pdf")):
        upload_file(client, pdf, pdf.name)
        print(f"uploaded {pdf.name}")

    print("\nbucket contents:", list_pdf_keys(client))
