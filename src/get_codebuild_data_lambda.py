#!/usr/bin/env python3
"""Moduł zawiera funkcje Lambda do pobierania informacji na temat CodeBuild, 
    a następnie przesyła wygenerowany plik json do S3 bucket"""
import logging

import boto3
from botocore.exceptions import ClientError

from helper import dump_to_s3, paginator

log = logging.getLogger()

OUTPUT_FILE_COV = "codebuild-cov-data.dev.json"
OUTPUT_FILE_UNIT = "codebuild-unit-data.dev.json"
DATA_FOLDER_PATH = "data"
S3_BUCKET_NAME = "panel-wdrozen-bucket"


def get_project_from_arn(arn):
    """
    Funkcja wyodrębnia nazwę projektu z arn.
    """
    return arn.split(":")[5]


def get_unit_tests(client):
    """Zwraca wyniki testów jednostkowych dla danego raportu Codebuild"""
    try:
        log.info("Harvesting Unit Tests")
        test_report_dict = {}
        build_reports = paginator(client.list_reports)
        unit_test_reports = [arn for arn in build_reports if "-unit" in arn]
        first_arns = {}
        for arn in unit_test_reports:
            project = get_project_from_arn(arn)
            if project not in first_arns:
                first_arns[project] = arn

        for report_arn in list(first_arns.values()):
            unit_test_report = client.describe_test_cases(reportArn=report_arn)
            project_name = report_arn.split("-unit")[0]

            passes = sum(
                1
                for f_c in unit_test_report.get("testCases")
                if f_c.get("status") == "SUCCEEDED"
            )
            fails = sum(
                1
                for f_c in unit_test_report.get("testCases")
                if f_c.get("status") == "FAILED"
            )
            skipped = sum(
                1
                for f_c in unit_test_report.get("testCases")
                if f_c.get("status") == "SKIPPED"
            )
            total_tests = len(unit_test_report.get("testCases"))
            log.info(
                "%s, %s, %s, %s, %s", project_name, total_tests, passes, fails, skipped
            )
            test_report_dict[project_name] = [passes, skipped, fails, total_tests]
    except ClientError as err:
        log.info(err)
    return test_report_dict


def get_coverage(client):
    """Zwraca podsumowanie raportu pokrycia dla każdego raportu Codebuild"""
    try:
        report_dict = {}
        build_reports = paginator(client.list_reports)
        coverage_only_reports = [arn for arn in build_reports if "coverage" in arn]
        first_arns = {}
        for arn in coverage_only_reports:
            project = get_project_from_arn(arn)
            if project not in first_arns:
                first_arns[project] = arn

        for report_arn in list(first_arns.values()):
            coverage_report = client.describe_code_coverages(reportArn=report_arn)
            project_name = report_arn.split("-coverage")[0]
            branches = {}
            lines = {}
            branches["covered"] = sum(
                f_c.get("branchesCovered")
                for f_c in coverage_report.get("codeCoverages")
                if f_c.get("branchesCovered")
            )
            branches["missed"] = sum(
                f_c.get("branchesMissed")
                for f_c in coverage_report.get("codeCoverages")
                if f_c.get("branchesMissed")
            )
            branches["total"] = (branches["covered"] + branches["missed"]) or 1

            lines["covered"] = sum(
                f_c.get("linesCovered")
                for f_c in coverage_report.get("codeCoverages")
                if f_c.get("linesCovered")
            )
            lines["missed"] = sum(
                f_c.get("linesMissed")
                for f_c in coverage_report.get("codeCoverages")
                if f_c.get("linesMissed")
            )
            lines["total"] = (lines["covered"] + lines["missed"]) or 1

            log.info("%s, %s, %s", project_name, branches["covered"], branches["total"])
            branches_percentage = round(
                (branches["covered"] / branches["total"]) * 100, 1
            )
            lines_percentage = round((lines["covered"] / lines["total"]) * 100, 1)
            log.info("%s, %s, %s", project_name, branches_percentage, lines_percentage)
            report_dict[project_name] = [lines_percentage, branches_percentage]
    except ClientError as err:
        log.error(err)
    return report_dict


def lambda_handler(event, context):
    """Poiera statystyki raportu CodeBuild"""

    log.debug(context)
    log.info(event)

    session = boto3.Session()

    codebuild_client = session.client("codebuild")

    cov_report = {}
    cov_dict = get_coverage(codebuild_client)
    for project_name in cov_dict:
        cov_report[project_name] = cov_dict.get(project_name)

    unit_dict = get_unit_tests(codebuild_client)

    unit_report = {}
    for project_name in cov_dict:
        unit_report[project_name] = [unit_dict.get(project_name)]

    dump_to_s3(
        cov_report,
        bucket_name=S3_BUCKET_NAME,
        file_name=f"{DATA_FOLDER_PATH}/{OUTPUT_FILE_COV}",
    )
    dump_to_s3(
        unit_report,
        bucket_name=S3_BUCKET_NAME,
        file_name=f"{DATA_FOLDER_PATH}/{OUTPUT_FILE_UNIT}",
    )

    return {"statusCode": 200, "body": "Lambda execution complete."}
