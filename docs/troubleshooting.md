Cloud & DevOps Troubleshooting Log

This document records the major infrastructure, deployment, authentication, networking, Docker, Terraform, Git, and AWS issues encountered while building the three-tier AWS application.

The purpose of this document is to demonstrate the troubleshooting process used to identify failures, gather evidence, apply targeted fixes, and verify the results.



1. GitHub Actions — AWS OIDC Authentication Failure

Symptom

GitHub Actions failed when attempting to authenticate to AWS.

Error:

Could not assume role with OIDC

AssumeRoleWithWebIdentity

Investigation

The following were checked:

GitHub Actions workflow permissions
id-token: write
GitHub OIDC provider
OIDC audience
IAM role ARN
IAM trust policy
IAM permissions policy
Repository/branch conditions
The important distinction was between authentication and authorization.

Root Cause

The IAM trust policy did not correctly match the identity information AWS was receiving from GitHub’s OIDC token.

Evidence

CloudTrail was used to inspect the failed AssumeRoleWithWebIdentity event.

Instead of continuing to guess at the policy, the actual identity information from the AWS event was compared against the IAM trust policy.

Fix

The IAM trust policy was corrected to match the identity AWS was actually receiving.

The GitHub workflow was then able to successfully assume the IAM role.

Verification

GitHub Actions

      ↓

GitHub OIDC Token

      ↓

AWS IAM OIDC Provider

      ↓

IAM Trust Policy

      ↓

STS AssumeRoleWithWebIdentity

      ↓

IAM Role

Lesson Learned

Do not change IAM permissions when the failure is authentication.

AssumeRoleWithWebIdentity → investigate OIDC and the trust policy.
not authorized to perform → investigate IAM permissions.
CloudTrail became the source of truth instead of guessing.



2. Terraform — Subnet Not Found

Symptom

Terraform failed with:

no matching EC2 Subnet found

Initial Possibility

Because the error came from AWS/Terraform, IAM permissions could have appeared to be a possible cause.

Investigation

The following were checked:

Subnet ID
AWS region
VPC association
Terraform data-source filters
Whether the subnet actually existed
Root Cause

The subnet ID configured in main.tf was incorrect.

Fix

The correct subnet ID was identified and entered into the Terraform configuration.

Verification

terraform plan

completed successfully.

The GitHub Actions Terraform workflow also passed.

Lesson Learned

A Terraform lookup error is not automatically an IAM problem.

When Terraform reports that a resource cannot be found, verify the resource ID, region, VPC, filters, and actual AWS resource before modifying permissions.



3. Terraform — EC2 vCPU Quota Exceeded

Symptom

Terraform failed while attempting to create an EC2 instance because the AWS account had reached its EC2 vCPU quota.

The account showed:

Applied quota: 16 vCPUs

Current utilization: 16 vCPUs

Investigation

The running EC2 instances were inspected.

Repeated Terraform/GitHub Actions testing had created multiple instances that remained running.

Root Cause

The AWS account had consumed its available EC2 vCPU quota through repeated test deployments.

Fix

Unnecessary EC2 instances were terminated.

Terraform was then run again.

Verification

Terraform successfully created the intended EC2 instance.

Lesson Learned

An EC2 provisioning failure is not automatically an IAM failure.

For EC2 capacity problems, check:

Running instances

      ↓

Instance sizes

      ↓

Current resource utilization

      ↓

AWS Service Quotas

      ↓

IAM permissions if necessary



4. Terraform — Temporary GitHub Actions Runners and State

Symptom

Repeated GitHub Actions Terraform runs created multiple EC2 instances.

The expected behavior was:

First run  → Create EC2

Second run → No changes

Instead, the behavior became:

Run 1 → Create EC2

Run 2 → Terraform does not know about EC2 → Create another EC2

Run 3 → Create another EC2

Investigation

The GitHub Actions environment was examined.

GitHub-hosted runners are temporary. Terraform state stored only on the runner does not automatically persist between independent workflow runs.

Root Cause

Terraform did not have reliable persistent remote state between CI/CD executions.

Fix

The project moved toward using an S3 backend for Terraform remote state.

Expected Result

Once remote state is correctly configured:

GitHub Actions

      ↓

Terraform

      ↓

S3 Remote State

      ↓

Existing Infrastructure

A subsequent plan should recognize resources already managed by Terraform.

Expected result:

Plan: 0 to add, 0 to change, 0 to destroy.

Lesson Learned

Terraform state is a critical part of Infrastructure as Code.

When Terraform runs from temporary CI/CD environments, state must be persisted reliably.

Do not repeatedly run terraform apply when the state-management strategy is not yet correct.



5. Terraform — Formatting Failure

Symptom

GitHub Actions failed during:

terraform fmt -check

Investigation

The Terraform configuration was inspected.

The issue was formatting rather than Terraform logic.

Root Cause

The Terraform files were not formatted according to Terraform’s standard formatting.

Fix

terraform fmt

The resulting changes were committed and pushed.

Verification

terraform fmt -check

passed.

Lesson Learned

terraform fmt changes formatting.

terraform fmt -check only verifies that formatting is already correct.

A formatting failure does not necessarily indicate a configuration or infrastructure problem.



6. Docker — Permission Denied

Symptom

Docker commands returned a permission-related error:

permission denied

Investigation

The Docker command was being executed as a user without permission to access the Docker socket.

Temporary Fix

sudo docker ...

Better Long-Term Approach

Add the user to the Docker group so Docker does not require sudo for normal development.

Lesson Learned

Using sudo can solve the immediate Docker permission problem, but it is better to correct the underlying user permissions.



7. Docker/API — Container Dependency Failure

Symptom

The API container failed because Python could not import:

Prometheus_fastapi_instrumentor

The error indicated a missing Python dependency.

Investigation

The container was examined using:

docker ps

docker logs <container>

The running process, dependencies, application startup, and exposed ports were also considered.

Root Cause

The required Python dependency was missing from the application’s environment.

Fix

The dependency was added to the project’s dependency configuration and the Docker image was rebuilt.

Verification

The container was rebuilt and the API validation workflow eventually passed.

Lesson Learned

When a container fails to start, do not immediately assume the issue is networking.

Start with:

Container status

      ↓

Container logs

      ↓

Application startup

      ↓

Dependencies

      ↓

Environment variables

      ↓

Ports



8. EC2 — Port 8000 Inaccessible

Symptom

The FastAPI application was expected to listen on:

TCP 8000

but external access failed.

Investigation

The application and container were checked locally first.

Useful commands:

docker ps

docker logs <container>

ss -tulpn

curl http://localhost:8000

The AWS security group was then examined.

Root Cause

The EC2 security group did not allow inbound TCP traffic on port 8000.

Fix

TCP port 8000 was temporarily allowed for testing.

Important Distinction

An application listening on port 8000 does not mean AWS networking allows traffic to port 8000.

Both layers must work:

FastAPI listening on 8000

        +

Security Group allowing 8000

        =

External connectivity

Lesson Learned

Separate application-level connectivity from network-level connectivity.



9. ECR — EC2 Image Pull Authentication

Requirement

The EC2 instance needed to pull private Docker images from Amazon ECR.

Architecture

EC2

 ↓

IAM Instance Role

 ↓

ECR Permissions

 ↓

Amazon ECR

Verification

The EC2 instance identity was checked using:

aws sts get-caller-identity

This confirmed that the EC2 instance was receiving AWS credentials through its IAM role.

Permission Model

The EC2 role uses:

AmazonEC2ContainerRegistryReadOnly

The instance only needs to pull images.

It does not need permissions to administer or push images to ECR.

Lesson Learned

Use IAM roles for EC2 workloads instead of storing long-lived AWS access keys on the server.



10. ECR — Docker Authentication

Authentication

The EC2 instance authenticates Docker to ECR using:

aws ecr get-login-password --region us-east-1 \

| sudo docker login \

--username AWS \

--password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

Expected Result

Login Succeeded

The image can then be pulled:

docker pull <exact-ECR-image-URI>

and verified:

docker images

Lesson Learned

When troubleshooting ECR pulls, verify both:

The AWS identity being used.
The ECR repository/image URI being requested.


11. Nginx — Frontend/API Routing

Symptom

The frontend could load, but API requests required proper routing from Nginx to FastAPI.

The frontend uses paths such as:

fetch('/api/register')

Intended Routing

/api/*

   ↓

FastAPI backend



Everything else

   ↓

Frontend static files

Root Cause

Nginx needed to be configured as the reverse proxy for API requests.

Configuration

The Nginx configuration uses:

proxy_pass http://BACKEND_PRIVATE_IP:8000/;

The trailing slash is important for the intended /api/ path handling.

Lesson Learned

HTTP 404 errors should lead to investigation of:

Frontend route

      ↓

Nginx route

      ↓

Proxy configuration

      ↓

FastAPI route

rather than automatically assuming an AWS networking problem.



12. PostgreSQL — Database Connectivity

Target Architecture

The database architecture was moved toward:

API EC2

   |

   | TCP 5432

   v

RDS PostgreSQL

The database should remain private.

Recommended Security Group Model

API EC2 Security Group

        |

        | TCP 5432

        v

RDS Security Group

Incorrect Configuration

The database should not use:

0.0.0.0/0 → TCP 5432

Troubleshooting Approach

If the API cannot connect to PostgreSQL:

API application

      ↓

Database hostname

      ↓

DNS/network reachability

      ↓

Security Group

      ↓

Port 5432

      ↓

RDS availability

      ↓

Database credentials

      ↓

PostgreSQL authentication

Lesson Learned

Database connectivity should be investigated layer by layer rather than changing multiple settings simultaneously.



13. Git — Untracked Files

Symptom

Running:

git status

showed files under:

Untracked files

Meaning

Git could see the files, but they had not been added to the staging area.

Fix

git add .

Then verify:

git status

Lesson Learned

Git tracks files only after they are added to the repository’s staging process.



14. Git — Remote Name Typo

Symptom

A Git command failed because the remote was referenced as:

orgin

instead of:

origin

Investigation

The configured remotes were checked:

git remote -v

Fix

git remote set-url origin <repository-url>

Lesson Learned

When Git cannot push to a remote, inspect the configured remote rather than assuming the repository itself is broken.



15. GitHub — Password Authentication

Symptom

Normal GitHub account passwords could not be used for Git authentication.

Fix

SSH authentication was configured.

Typical setup:

ssh-keygen -t ed25519

eval "$(ssh-agent -s)"

ssh-add ~/.ssh/id_ed25519

The public key was added to GitHub.

Verification

ssh -T git@github.com

Security Lesson

Never share:

~/.ssh/id_ed25519

The private key must remain private.



16. Git — Repository Ownership Problems

Symptom

Using sudo git caused repository ownership problems.

Errors included:

detected dubious ownership

and:

could not lock git config file

Root Cause

Files in the repository had become owned by the root user after Git commands were executed with sudo.

Fix

sudo chown -R $(whoami):$(whoami) .

Normal Workflow After Fix

git init

git add .

git commit

git push

Lesson Learned

Avoid using sudo for normal Git operations.

Running development tools as root can create permission and ownership problems that are harder to diagnose later.



17. Secrets — Environment Variables

Problem

Database credentials should not be stored directly in source code or committed to GitHub.

Unsafe Pattern

POSTGRES_USER: actual_username

POSTGRES_PASSWORD: actual_password

POSTGRES_DB: actual_database

Improved Pattern

POSTGRES_USER: ${POSTGRES_USER}

POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

POSTGRES_DB: ${POSTGRES_DB}

Credentials are supplied through environment variables.

The .env file is excluded from Git:

.env

Production Improvement

AWS Secrets Manager can be introduced for a more production-oriented architecture.

Lesson Learned

Credentials should be separated from source code and container images.



18. CloudTrail — Using Evidence Instead of Guessing

One of the most important troubleshooting techniques developed during the project was using CloudTrail to investigate AWS authentication failures.

Instead of repeatedly changing IAM policies:

Error

 ↓

CloudTrail

 ↓

Actual AWS event

 ↓

Identity information

 ↓

Compare with policy

 ↓

Targeted change

 ↓

Retry

 ↓

Verify

This approach reduced guesswork and helped distinguish authentication failures from authorization failures.



General Troubleshooting Decision Guide

IAM Authorization Error

Example:

not authorized to perform ...

Investigate:

IAM permissions policy

 ↓

Action

 ↓

Resource

 ↓

Conditions

 ↓

Role/user being used



OIDC Authentication Error

Example:

AssumeRoleWithWebIdentity

Investigate:

GitHub workflow permissions

 ↓

OIDC provider

 ↓

Audience

 ↓

Subject/identity claims

 ↓

IAM trust policy

 ↓

CloudTrail



Terraform Resource Not Found

Example:

no matching EC2 Subnet found

Investigate:

Resource ID

 ↓

AWS region

 ↓

VPC

 ↓

Terraform filters

 ↓

Resource existence



Terraform Unexpectedly Creates Resources

Investigate:

terraform plan

 ↓

Terraform state

 ↓

Backend

 ↓

Resource configuration

 ↓

Import/state relationship



EC2 Creation Failure

Investigate:

Instance limits

 ↓

vCPU quota

 ↓

Instance type

 ↓

Subnet

 ↓

Security groups

 ↓

IAM permissions



Container Failure

Investigate:

docker ps

 ↓

docker logs

 ↓

Image

 ↓

Dependencies

 ↓

Environment variables

 ↓

Startup command

 ↓

Ports



Connection Timeout

Investigate:

Application

 ↓

Listening port

 ↓

Security Group

 ↓

NACL

 ↓

Route table

 ↓

Private/public addressing

 ↓

Service availability



HTTP 403

Investigate:

Authentication

 ↓

Authorization

 ↓

IAM/application permissions



HTTP 404

Investigate:

Requested URL

 ↓

Nginx route

 ↓

Proxy configuration

 ↓

Backend route

 ↓

Application



Troubleshooting Method Used Throughout the Project

The general troubleshooting process is:

1. Read the exact error

        ↓

2. Identify the affected layer

        ↓

3. Identify the AWS/application service involved

        ↓

4. Determine where reliable evidence exists

        ↓

5. Inspect the evidence

        ↓

6. Form a hypothesis

        ↓

7. Apply the smallest reasonable fix

        ↓

8. Rerun the failing operation

        ↓

9. Verify the result

The core pattern is:

ERROR

  ↓

LOCATION

  ↓

EVIDENCE

  ↓

HYPOTHESIS

  ↓

FIX

  ↓

VERIFICATION

The goal is not simply to make an error disappear.

The goal is to understand:

What failed?
Where did it fail?
Why did it fail?
What evidence proves the cause?
What change fixes it?
How can the fix be verified?
How can the problem be prevented in the future?


Key Troubleshooting Lessons

1. Authentication and authorization are different

Successfully assuming an IAM role does not mean that the role has permission to perform every AWS action.

2. Read the exact error first

The error message often identifies the layer that needs investigation.

3. Do not automatically blame IAM

AWS-related errors can come from:

Incorrect IDs
Incorrect regions
Incorrect networking
Incorrect Terraform configuration
Resource quotas
Application failures
Docker problems
Missing permissions
4. Use evidence

CloudTrail, Terraform plans, Docker logs, AWS resource configuration, and system commands provide evidence that is more reliable than guessing.

5. Change one layer at a time

Changing IAM, networking, application configuration, and Docker settings simultaneously makes it difficult to identify the actual cause.

6. Verify after every fix

A successful command is not always proof that the entire system works.

Verify the actual intended behavior.

7. State matters

Terraform requires reliable state when infrastructure is managed through temporary CI/CD environments.

8. Green CI does not guarantee a successful deployment

A workflow can successfully build and push an image while an older container is still running on EC2.

9. Private infrastructure should remain private

RDS PostgreSQL should only be reachable from the application tier and should not be exposed to the public internet.

10. IAM roles are preferable to long-lived access keys

EC2 can receive AWS permissions through an IAM instance role, while GitHub Actions can authenticate through OIDC.



Final Takeaway

The most valuable skill developed through this project was not memorizing AWS commands.

It was learning how to troubleshoot across multiple infrastructure layers.

The project repeatedly required moving through:

Application

    ↓

Container

    ↓

Host

    ↓

Network

    ↓

AWS service

    ↓

IAM

    ↓

Terraform

    ↓

CI/CD

The troubleshooting approach developed through these incidents is:

Understand what the error means, identify the layer where it occurred, gather evidence from the correct source, form a hypothesis, make a targeted change, and verify the result.

This methodology can be applied beyond this specific three-tier application to AWS infrastructure, DevOps pipelines, cloud security, IAM, Kubernetes, and production environments.

