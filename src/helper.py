"""Zawiera pomocne metody do otrzymywania i tworzenia danych dla aplikacji Panel wdrożeń"""
import json
import boto3


def dump_to_s3(data, bucket_name, file_name):
    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json.dumps(data, indent=4),
            ContentType="application/json",
        )
        return True  # Successfully uploaded
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return False  # Failed to upload


def paginator(method, **kwargs):
    """
    Paginator używany z niektórymi wywołaniami boto3,
    gdy wymagana jest paginacja.
    """
    client = method.__self__
    iterator = client.get_paginator(method.__name__)
    for page in iterator.paginate(**kwargs).result_key_iters():
        yield from page
