"""Moduł zawiera funkcje Lambda do pobierania informacji na temat CodeCommit, 
    a następnie przesyła wygenerowany plik json do S3 bucket"""
import boto3
import logging
from botocore.config import Config
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor

from helper import dump_to_s3

log = logging.getLogger()
THREAD_WORKERS = 4
QUEUED_SESSIONS = 4
BUCKET_NAME = "panel-wdrozen-bucket"
DEFAULT_BRANCH_NAME = "master"
DEV_BRANCH_NAME = "dev"
PROD_BRANCH_NAME = "prod"

CLIENT_CONFIG = Config(retries={"max_attempts": 5, "mode": "adaptive"})


def get_diffs(client, repository_name, source, target) -> int:
    """Zwraca liczbę zmian w plikach pomiędzy gałęzią źródłową i docelową"""
    try:
        differences = client.get_differences(
            repositoryName=repository_name,
            beforeCommitSpecifier=source,
            afterCommitSpecifier=target,
        )
        result = len(differences.get("differences"))
    except ClientError as err:
        if err.response["Error"]["Code"] == "CommitDoesNotExistException":
            result = -1
        else:
            print(err)
    return result


def get_branches(client, repository_name) -> dict:
    """Zwraca branche w danym repozytorium"""
    try:
        response = client.list_branches(repositoryName=repository_name)
    except ClientError as err:
        print(err)
    return sort_with_priority(response.get("branches"), ["dev", "int", "prod"])


def sort_with_priority(input_list, priority_items):
    """Sortuje tak, aby branche dev, int, prod były na początku listy"""
    priority = sorted(item for item in input_list if item in priority_items)
    non_priority = sorted(item for item in input_list if item not in priority_items)
    return priority + non_priority


def get_pr_summary(client, pull_request_id: str):
    """Zwraca informacje na temat Pull Requestu"""
    try:
        response = client.get_pull_request(pullRequestId=pull_request_id)
        pr = response.get("pullRequest")
    except ClientError as err:
        log.error(err)
    return {
        "Pull Request ID": pull_request_id,
        "Title": pr["title"],
        "Requester": pr.get("authorArn").split("/")[-1]
        if pr.get("authorArn")
        else "missing author",
        "Destination": pr["pullRequestTargets"][0]["destinationReference"].replace(
            "/refs/heads", ""
        ),
        # "Pull Request Age": get_elapsed_time(pr["creationDate"]),
        "Approval Status": evaluate_approval_state(
            client, pull_request_id=pull_request_id, revision_id=pr["revisionId"]
        ),
    }


def evaluate_approval_state(client, pull_request_id: str, revision_id: str) -> str:
    """Zwraca wartość true jeśli PR jest zaakceptowany"""
    try:
        response = client.evaluate_pull_request_approval_rules(
            pullRequestId=pull_request_id, revisionId=revision_id
        )
        if response.get("evaluation").get("overridden"):
            return "overridden"
        if response.get("evaluation").get("approved"):
            return "approved"
        if not response.get("evaluation").get("approvalRulesNotSatisfied"):
            return "No Approval Necessary"
    except ClientError as err:
        log.error(err)
    return "Approval Needed"


def get_pull_requests(client, repository_name) -> list:
    """Zwraca liste słowników zawierających informache na temat otwartych Pull request"""
    try:
        response = client.list_pull_requests(
            pullRequestStatus="OPEN", repositoryName=repository_name
        )
        pr_list = [
            get_pr_summary(client, pr_id) for pr_id in response.get("pullRequestIds")
        ]
    except ClientError as err:
        log.error(err)
    return pr_list


def get_repository_tags(client, repository_name) -> list:
    """Pobiera tagi repozytorium dla określonego repozytorium"""
    try:
        relevant_tag_names = "test1,testtag,test_tag1"
        if relevant_tag_names:
            response = client.get_repository(repositoryName=repository_name)
            repository_arn = response.get("repositoryMetadata")["Arn"]
            tags = client.list_tags_for_resource(resourceArn=repository_arn)
            result = tags.get("tags")
            tags_list = get_relevant_tags(relevant_tag_names.split(","), result)
            return tags_list
    except ClientError as err:
        print(err)
    return []


def get_relevant_tags(relevant_tag_list: list, tags: dict) -> list:
    """Filtruje wartości odpowiednich tagów repozytorium CodeCommit do zbioru"""
    tags_set = set()
    if len(tags) > 0:
        relevant_tags = {
            relevant_tag: tags.get(relevant_tag, None)
            for relevant_tag in relevant_tag_list
        }
        for tag_value in relevant_tags.values():
            if tag_value is not None:
                tags_set = tags_set.union(set(tag_value.strip().split("/")))

    return list(tags_set)


def get_project_from_arn(arn):
    """Przygotowywuje funkcję, aby wyodrębniała część projektu z ARN-ów"""
    return arn.split(":")[5]


def get_all_project_info(args):
    """Pobiera wszystkie potrzebne dane z CodeCommit"""
    repo_name, codecommit_client = args
    log.info("Processing Repository: %s", repo_name)

    # Using ThreadPoolExecutor to call the methods concurrently
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                get_repository_tags, client=codecommit_client, repository_name=repo_name
            ),
            executor.submit(
                get_diffs,
                client=codecommit_client,
                repository_name=repo_name,
                source=DEFAULT_BRANCH_NAME,
                target=DEV_BRANCH_NAME,
            ),
            executor.submit(
                get_diffs,
                client=codecommit_client,
                repository_name=repo_name,
                source=DEV_BRANCH_NAME,
                target=PROD_BRANCH_NAME,
            ),
            executor.submit(
                get_branches, client=codecommit_client, repository_name=repo_name
            ),
            executor.submit(
                get_pull_requests, client=codecommit_client, repository_name=repo_name
            ),
        ]
        report_item = [repo_name]
        for future in futures:
            report_item.append(future.result())
    return report_item


def lambda_handler(event, context):
    """Main handler to CICD Dashboard"""

    log.debug(context)
    log.info(event)

    report = []
    session = boto3.Session()

    codecommit_client = session.client("codecommit", config=CLIENT_CONFIG)
    all_repos = codecommit_client.list_repositories()

    repository_names = [
        (
            repo["repositoryName"],
            codecommit_client,
        )
        for repo in all_repos.get("repositories")
        # if repo["repositoryName"] in REPO_LIST
    ]
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as executor:
        results = list(executor.map(get_all_project_info, repository_names))
    report = dict(zip([p[0] for p in repository_names], results))
    dump_to_s3(report, bucket_name=BUCKET_NAME, file_name="data/codecommit-data.json")
    return {"statusCode": 200, "body": "Lambda execution complete."}
