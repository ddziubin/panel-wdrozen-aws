#!/usr/bin/env python3
import aws_cdk as cdk

from deployment_dashboard_app.deployment_dashboard_app_stack import (
    DeploymentDashboardAppStack,
)

app = cdk.App()
DeploymentDashboardAppStack(
    app,
    "DeploymentDashboardAppStack",
)

app.synth()
