from constructs import Construct
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_events,
    aws_events_targets,
    aws_lambda,
)

import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deployment


class DeploymentDashboardAppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Definiuję potrzebne zmienne
        s3_bucket_name = "panel-wdrozen-bucket"

        # Tworzę publiczny S3 Bucket, w którym bedę przechowywać dane oraz stworzę strone z panelem wdrożeń
        dashboard_bucket = s3.Bucket(
            self,
            "panel-wdrozen-pracamgr.com",
            bucket_name=s3_bucket_name,
            website_index_document="index.html",
            block_public_access=s3.BlockPublicAccess(block_public_policy=False),
            public_read_access=True,
            versioned=False,
            removal_policy=RemovalPolicy.DESTROY,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=[],
                    max_age=3000,
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(90),
                    noncurrent_version_expiration=Duration.days(1),
                    id="RetentionRule",
                )
            ],
        )

        dashboard_bucket.add_to_resource_policy(
            permission=iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[
                    dashboard_bucket.arn_for_objects("*"),
                    dashboard_bucket.bucket_arn,
                ],
                principals=[iam.StarPrincipal()],
            )
        )

        # Umieszczam pliki w buckecie
        s3_deployment.BucketDeployment(
            self,
            id="bucketdeployment",
            sources=[s3_deployment.Source.asset("./webapp")],
            destination_bucket=dashboard_bucket,
        )

        # Tworze role oraz dla Lambdy, która pozyskuje dane z codecommit
        self._fetch_codecommit_data = iam.Role(
            self,
            f"fetch-codecommit-role",
            role_name=f"fetch-codecommit-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        self._fetch_codecommit_data.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                ],
                resources=[f"{dashboard_bucket.bucket_arn}*"],
            )
        )

        self._fetch_codecommit_data.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["codecommit:*"],
                resources=["*"],
            )
        )

        # Tworze role oraz dla Lambdy, która pozyskuje dane o CodePipeline
        self._fetch_codepipeline_data = iam.Role(
            self,
            f"fetch-pipeline-role",
            role_name=f"fetch-pipeline-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        self._fetch_codepipeline_data.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                ],
                resources=[f"{dashboard_bucket.bucket_arn}*"],
            )
        )

        self._fetch_codepipeline_data.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["codepipeline:*"],
                resources=["*"],
            )
        )

        # Tworze role oraz dla Lambdy, która pozyskuje dane o CodeBuild
        self._fetch_codebuild_data = iam.Role(
            self,
            f"fetch-codebuild-role",
            role_name=f"fetch-codebuild-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        self._fetch_codebuild_data.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                ],
                resources=[f"{dashboard_bucket.bucket_arn}*"],
            )
        )

        self._fetch_codebuild_data.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["codebuild:*"],
                resources=["*"],
            )
        )

        # Tworzę lambdę do otrzymywania informacji na temat CodeCommit
        self.get_codecommit = aws_lambda.Function(
            self,
            id="GetCodeCommitInfo",
            code=aws_lambda.Code.from_asset("./src/"),
            handler="get_codecommit_data_lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.minutes(15),
            role=self._fetch_codecommit_data,
        )

        # Tworzę lambdę do otrzymywania informacji na temat CodePipeline
        self.get_codepipeline = aws_lambda.Function(
            self,
            id="GetCodePipelineInfo",
            code=aws_lambda.Code.from_asset("./src/"),
            handler="get_codepipeline_data_lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.minutes(15),
            role=self._fetch_codepipeline_data,
        )

        # Tworzę lambdę do otrzymywania informacji na temat CodeBuild
        self.get_codebuild = aws_lambda.Function(
            self,
            id="GetCodeBuildInfo",
            code=aws_lambda.Code.from_asset("./src/"),
            handler="get_codebuild_data_lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.minutes(15),
            role=self._fetch_codebuild_data,
        )

        self.rule = aws_events.Rule(
            self,
            "Run every 15 minutes",
            schedule=aws_events.Schedule.cron(
                minute="15", hour="*", week_day="*", month="*", year="*"
            ),
        )
        self.rule.add_target(aws_events_targets.LambdaFunction(self.get_codecommit))
        self.rule.add_target(aws_events_targets.LambdaFunction(self.get_codepipeline))
        self.rule.add_target(aws_events_targets.LambdaFunction(self.get_codebuild))
