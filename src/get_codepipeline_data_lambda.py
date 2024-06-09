#!/usr/bin/env python3
"""Module contains lambda to fetch the codepipeline execution status for all pipelines within and account and then
upload it to an S3 Bucket"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from helper import dump_to_s3

log = logging.getLogger()

THREAD_WORKERS = 60
BUCKET_NAME = "panel-wdrozen-bucket"
CLIENT_CONFIG = Config(retries={"max_attempts": 5, "mode": "adaptive"})


def get_pipeline_exec(client, pipeline_name) -> str:
    """Zwraca status dla ostatnio wykonanego Pipeline"""
    try:
        response = client.list_pipeline_executions(
            pipelineName=pipeline_name, maxResults=1
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "PipelineNotFoundException":
            return "No Pipeline"
        return "Error"
    # Extract the most recent execution from the response
    if response.get("pipelineExecutionSummaries"):
        last_execution = response["pipelineExecutionSummaries"][0]["status"]
        return last_execution
    return "N/A"


def get_all_pipeline_info(args):
    """Tworzy raport dla każdego Pipeline"""
    pipeline_name, codepipeline_client = args
    log.info("Processing Pipeline: %s", pipeline_name)
    report_item = [
        get_pipeline_exec(client=codepipeline_client, pipeline_name=pipeline_name),
    ]
    return report_item


def lambda_handler(event, context):
    """Pobiera dane wykonania CodePipeline z konta powiązanego z profilem i zapisuje je w pliku JSON"""

    log.debug(context)
    log.info(event)
    setup = {}
    setup["profile"] = event.get("profile")
    report = []

    session = boto3.Session()

    codepipeline_client = session.client(
        "codepipeline", config=Config(max_pool_connections=THREAD_WORKERS)
    )

    pipelines = codepipeline_client.list_pipelines()
    pipeline = [
        (
            pipeline["name"],
            codepipeline_client,
        )
        for pipeline in pipelines.get("pipelines")
        # if repo["repositoryName"] in REPO_LIST
    ]
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as executor:
        results = list(executor.map(get_all_pipeline_info, pipeline))
    report = dict(zip([p[0].replace("-pipeline", "") for p in pipeline], results))

    dump_to_s3(report, bucket_name=BUCKET_NAME, file_name="data/codepipeline-data.json")

    return {"statusCode": 200, "body": "Lambda execution complete."}
