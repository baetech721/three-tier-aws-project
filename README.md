Three-Tier AWS Cloud & DevOps Project
A portfolio-focused three-tier web application built while developing practical skills in AWS, Docker, Git, GitHub Actions, Terraform, IAM/OIDC, Amazon ECR, Nginx, PostgreSQL, and cloud troubleshooting.

The project was built incrementally rather than all at once. The goal was to understand how the individual components work together and to practice diagnosing real deployment and infrastructure failures.

Architecture
Current Architecture
text Internet | v +----------------------+ | EC2 #2 | | Web / Frontend | | | | Docker + Nginx | | Port 80 | +----------+-----------+ | /api/* | v +----------------------+ | EC2 #1 | | Backend / API | | | | Docker + FastAPI | | Port 8000 | +----------+-----------+ | v +----------------------+ | PostgreSQL / RDS | | Port 5432 | | Private | +----------------------+

The application uses Nginx as the frontend web tier, FastAPI as the backend API tier, and PostgreSQL as the database tier.

The intended production-style architecture is:

text Internet | v Application Load Balancer | +------------------+ | | v v Web Tier API Tier Nginx FastAPI | | +--------+---------+ | v RDS PostgreSQL

The longer-term architecture includes an Application Load Balancer, target groups, Auto Scaling, HTTPS, tighter security groups, and improved secrets management.

Technology Stack
Technology	Purpose
AWS	Cloud infrastructure
EC2	Compute / application servers
VPC	Network isolation
Security Groups	Network access control
Amazon RDS	Managed PostgreSQL database
Amazon ECR	Private Docker image registry
Docker	Application containerization
Nginx	Frontend web server / reverse proxy
FastAPI	Backend API
PostgreSQL	Application database
Git	Source control
GitHub	Source-code repository
GitHub Actions	CI/CD automation
GitHub OIDC	AWS authentication from GitHub Actions
IAM	Authentication and authorization
Terraform	Infrastructure as Code
S3	Terraform remote state
Prometheus	Metrics collection
Grafana	Metrics visualization
Node Exporter	Linux host metrics
Nginx Exporter	Nginx metrics
PostgreSQL Exporter	PostgreSQL metrics
AWS Region
The project uses:

text us-east-1

This is important because AWS resources are regional. A VPC, subnet, AMI, ECR repository, or other resource must be checked in the correct region before assuming that it does not exist.

Application Deployment Flow
The backend deployment path is:

text Developer | v GitHub | v GitHub Actions | v Docker Build | v Amazon ECR | v EC2 | v Running Docker Container

The frontend follows a similar process:

text GitHub | v GitHub Actions | v Docker Build | v Amazon ECR | v Frontend EC2 | v Nginx

The API image was successfully pushed to ECR and pulled onto EC2. The frontend image was also pushed to the three-tier-web ECR repository and successfully pulled by the frontend EC2 instance.

Docker
Backend
The API is containerized using Docker.

Example image:

bash docker build -t three-tier-api ./api

Run locally:

bash docker run -d -p 8000:8000 --name three-tier-api three-tier-api

Useful commands:

bash docker ps docker logs three-tier-api docker images docker stop three-tier-api docker rm three-tier-api

If Docker returns:

text permission denied

the current user may not have permission to access the Docker socket.

During development, the immediate workaround was:

bash sudo docker ...

Longer term, the user should be added to the Docker group rather than relying on sudo.

Nginx
The frontend uses Nginx to serve static files and proxy API requests.

Frontend requests use paths such as:

javascript fetch('/api/register')

Nginx routes:

text /api/* → FastAPI backend everything else → frontend static files

The Dockerfile was updated to copy the custom Nginx configuration:

dockerfile FROM nginx:latest COPY . /usr/share/nginx/html COPY nginx.conf /etc/nginx/conf.d/default.conf

The proxy configuration uses:

nginx proxy_pass http://BACKEND_PRIVATE_IP:8000/;

The trailing slash is important for the intended /api/ path handling.

GitHub Actions CI/CD
The CI workflow performs several validation stages.

Current CI Pipeline
text Checkout | v Python Setup | v Install Dependencies | v Run Tests | v Build Docker Image | v Run Container | v Validate FastAPI | v Validate Ports / Logs | v Build Nginx Image | v Validate PostgreSQL Compose | v GitHub OIDC | v AWS IAM | v Amazon ECR | v Push Docker Images

The workflow includes:

Python 3.12
Dependency installation
Password/hash tests
Docker builds
Docker container tests
FastAPI import validation
Uvicorn validation
Port checks
Container status checks
Container log checks
API testing
Nginx image building
PostgreSQL Compose validation
GitHub OIDC authentication
Amazon ECR authentication
Docker image pushes
The CI pipeline reached a green/working state after resolving the dependency, Nginx, OIDC, and Terraform formatting issues.

GitHub OIDC → AWS IAM
GitHub Actions authenticates to AWS without storing long-lived AWS access keys in GitHub.

The authentication chain is:

text GitHub Actions | v GitHub OIDC Token | v AWS IAM OIDC Provider | v IAM Trust Policy | v STS AssumeRoleWithWebIdentity | v IAM Role | v AWS Services

The OIDC provider is:

text token.actions.githubusercontent.com

The expected audience is:

text sts.amazonaws.com

GitHub Actions requires:

yaml permissions: id-token: write contents: read

The role-to-assume value must be the IAM role ARN, not the OIDC provider ARN.

IAM Authentication vs Authorization
One of the most important lessons from this project:

Authentication
Authentication answers:

"Can GitHub prove to AWS who it is?"

This involves:

text OIDC IAM OIDC Provider Trust Policy STS

Authorization
Authorization answers:

"What is the authenticated role allowed to do?"

This involves:

text IAM Permissions Policies

These are separate problems.

If the error is:

text AssumeRoleWithWebIdentity

investigate the OIDC provider and IAM trust policy.

If the error says:

text not authorized to perform ...

investigate the IAM role's permissions.

Adding ECR permissions will not fix an OIDC trust-policy failure.

Major OIDC Troubleshooting Incident
GitHub Actions initially failed with:

text Could not assume role with OIDC

and:

text AssumeRoleWithWebIdentity

The following were checked:

GitHub workflow permissions
OIDC provider
OIDC audience
IAM role ARN
IAM trust relationship
IAM permissions
GitHub Actions configuration
The key breakthrough came from checking CloudTrail.

The identity information shown by the failed AWS event was used to correct the IAM trust policy.

After the trust policy matched the identity AWS was actually receiving:

text AssumeRoleWithWebIdentity

began working.

Troubleshooting lesson
Do not keep changing permissions when the problem is authentication.

Use:

text CloudTrail ↓ Failed AssumeRoleWithWebIdentity event ↓ Inspect actual claims/identity ↓ Compare with trust policy ↓ Correct trust policy ↓ Retry ↓ Verify

CloudTrail became the source of truth instead of guessing.

Terraform
Terraform is used to manage infrastructure through Infrastructure as Code.

Current Terraform flow:

text GitHub | v GitHub Actions | v OIDC | v IAM Role | v Terraform | v AWS

Terraform successfully ran:

text terraform init terraform validate terraform plan terraform apply

and successfully created an EC2 instance.

Current Terraform Configuration
Terraform currently references existing AWS infrastructure through data sources:

text Existing VPC Existing Subnet Existing Ubuntu AMI Existing Security Group

Terraform creates:

text EC2 Instance

This demonstrates:

Terraform provider configuration
Resources
Data sources
Existing infrastructure lookup
EC2 provisioning
Terraform plan
Terraform apply
GitHub Actions integration
IAM/OIDC authentication
The entire three-tier architecture has not yet been recreated using Terraform.

Terraform State
Repeated GitHub Actions runs exposed an important Terraform problem.

GitHub Actions runners are temporary.

If Terraform state is not persisted between runs, a new runner may not know that Terraform already created a resource.

This can result in:

text Run 1 → Create EC2 Run 2 → Terraform does not know about EC2 Run 2 → Create another EC2 Run 3 → Create another EC2

This caused multiple EC2 instances to be created during testing.

The project therefore moved toward using an S3 backend for remote Terraform state.

The desired result after state is correctly configured is:

text Plan: 0 to add, 0 to change, 0 to destroy.

Important rule
Do not repeatedly run:

bash terraform apply

until Terraform state is being handled correctly.

Terraform Troubleshooting
Incorrect Subnet ID
Terraform reported:

text no matching EC2 Subnet found

The initial reaction could have been to investigate IAM.

That would have been the wrong direction.

The actual problem was an incorrect subnet ID in main.tf.

After the correct subnet ID was found and entered:

text Terraform plan → passed GitHub Actions → passed

General rule
When a Terraform data source says:

text no matching ...

check:

Resource ID
AWS region
VPC association
Terraform filters
Whether the resource actually exists
Do not automatically change IAM permissions.

EC2 Quota Troubleshooting
Terraform later failed because the AWS account had reached its EC2 vCPU quota.

The account showed:

text Applied quota: 16 vCPUs Current utilization: 16 vCPUs

The cause was repeated test workflows creating EC2 instances that remained running.

The unnecessary instances were terminated.

Terraform then successfully created the intended instance.

Lesson
A quota/capacity error is not automatically an IAM problem.

When EC2 creation fails:

text Check running instances ↓ Check instance sizes ↓ Check Service Quotas ↓ Then investigate IAM if necessary

Terraform Formatting
GitHub Actions also failed on:

text terraform fmt -check

This did not mean the Terraform logic was wrong.

terraform fmt formats Terraform files.

bash terraform fmt

terraform fmt -check only checks whether the files are already correctly formatted.

The fix was:

bash terraform fmt

followed by committing the formatting change.

Git Troubleshooting
Untracked Files
If:

bash git status

shows files in red under:

text Untracked files

Git sees the files but they have not been staged.

Use:

bash git add .

Then:

bash git status

Git Remote Typo
One issue was using:

text orgin

instead of:

text origin

Check the remote:

bash git remote -v

Correct it with:

bash git remote set-url origin

GitHub Password Authentication
GitHub no longer accepts normal account passwords for Git operations.

SSH authentication was configured instead.

Typical workflow:

bash ssh-keygen -t ed25519 eval "$(ssh-agent -s)" ssh-add ~/.ssh/id_ed25519

The public key can be added to GitHub.

Never share:

text ~/.ssh/id_ed25519

The private key must remain private.

Test:

bash ssh -T git@github.com

Git Ownership Problems
Using:

bash sudo git ...

caused repository ownership problems.

Errors included:

text detected dubious ownership

and:

text could not lock git config file

The ownership fix was:

bash sudo chown -R 
(
w
h
o
a
m
i
)
:
(whoami) .

After fixing ownership, normal Git commands should be used:

bash git init git add . git commit git push

Avoid using sudo for normal Git operations.

Files That Should Not Be Committed
The repository should not contain:

text .env venv/ pycache/ *.pyc

Example .gitignore:

gitignore venv/ pycache/ *.pyc .env

Database credentials were moved out of the Docker Compose configuration and into environment variables.

Example:

yaml POSTGRES_USER: ${POSTGRES_USER} POSTGRES_PASSWORD: ${POSTGRES_PASSWORD} POSTGRES_DB: ${POSTGRES_DB}

The .env file stays on the server and is not pushed to GitHub.

Docker/API Troubleshooting
One major error was:

text No module named 'Prometheus_fastapi_instrumentor'

This was identified as a Python dependency/import problem.

It was important not to immediately assume that this was the only reason port 8000 appeared closed.

The debugging process checked:

text Container status ↓ Container logs ↓ Running processes ↓ Listening ports ↓ Uvicorn ↓ FastAPI ↓ API response

The missing dependency was fixed and the CI pipeline eventually passed.

Port 8000 Troubleshooting
Port 8000 was initially inaccessible externally because the EC2 security group did not allow it.

For testing, TCP 8000 was opened.

Important distinction:

text Application listening on 8000 ≠ Security Group allowing 8000

Both must be checked.

Useful checks:

bash docker ps docker logs ss -tulpn curl http://localhost:8000

Then investigate the AWS security group if local access works but external access fails.

ECR + EC2 IAM
EC2 uses an IAM role to pull Docker images from ECR.

The EC2 role uses:

text AmazonEC2ContainerRegistryReadOnly

The server only needs to pull images. It does not need permission to administer or push to ECR.

The EC2 role was verified from inside the instance using:

bash aws sts get-caller-identity

This confirmed that the instance was receiving AWS credentials through its IAM role.

This is preferable to storing long-lived AWS access keys on the server.

ECR Authentication
The deployment uses Amazon ECR as the private Docker image registry.

Example authentication:

bash aws ecr get-login-password --region us-east-1 \ | sudo docker login \ --username AWS \ --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

Expected result:

text Login Succeeded

Then:

bash docker pull

and verify:

bash docker images

Database Architecture
The project moved toward using Amazon RDS for PostgreSQL instead of running PostgreSQL manually on another EC2 instance.

Target:

text API EC2 | | TCP 5432 v RDS PostgreSQL

The database should remain private.

Recommended security-group model:

text API EC2 Security Group | | TCP 5432 v RDS Security Group

Do NOT use:

text 0.0.0.0/0 → TCP 5432

The database should not be publicly accessible.

Database Security
Database credentials must not be stored in:

GitHub
source code
Docker images
public repositories
The current learning environment keeps credentials outside the repository.

AWS Secrets Manager can be introduced later for the production-style version.

Frontend → API Troubleshooting
The frontend successfully loads from the web EC2.

Registration was not yet considered fully functional until the PostgreSQL/RDS connection is established.

Possible failure layers include:

text Frontend ↓ Nginx ↓ API ↓ Database

A useful private-network test from the frontend EC2 is:

bash curl http://<API_PRIVATE_IP>:8000

If this works:

text Frontend EC2 → API EC2

is functioning.

The next layer to investigate is the database connection.

Networking Troubleshooting
A useful general rule:

Connection timeout
Investigate:

text Security Groups NACLs Routes Listeners Private/Public IP Service availability

HTTP 403
Investigate:

text Authentication Authorization IAM Application permissions

HTTP 404
Investigate:

text Application route Nginx route API path Proxy configuration

Container won't start
Investigate:

text docker ps docker logs image environment variables ports startup command

Terraform unexpectedly recreates resources
Investigate:

text terraform plan Terraform state backend lifecycle resource configuration

EC2 Networking
The project uses Ubuntu EC2 instances.

The frontend communicates with the API through the VPC using the API instance's private address.

For temporary learning/testing, hardcoding a private API IP can work.

However, this should eventually be replaced with:

text Load Balancer Target Groups Service discovery / dynamic infrastructure

because private IP addresses can change when infrastructure is recreated.

Monitoring
The monitoring portion of the project is designed around:

text Prometheus | v Metrics | v Grafana

Planned/used exporters include:

text Node Exporter → Linux/EC2 metrics Nginx Exporter → Nginx metrics PostgreSQL Exporter → PostgreSQL metrics FastAPI Prometheus instrumentation → Application metrics

Grafana can use Prometheus as a metrics data source and visualize:

CPU usage
Memory usage
Disk usage
Network activity
Nginx traffic
HTTP requests
API metrics
PostgreSQL metrics
The API also uses Prometheus instrumentation so application-level metrics can be exposed.

Troubleshooting Method
The most important skill developed through this project is not memorizing AWS console buttons.

The troubleshooting process is:

text 1. Read the error ↓ 2. Identify the category ↓ 3. Identify the service ↓ 4. Identify where the evidence should exist ↓ 5. Inspect the evidence ↓ 6. Form a hypothesis ↓ 7. Apply the smallest reasonable fix ↓ 8. Rerun ↓ 9. Verify

The core pattern is:

text ERROR ↓ LOCATION ↓ EVIDENCE ↓ FIX ↓ VERIFICATION

Examples:

Error	First Investigation
not authorized	IAM permissions
AssumeRoleWithWebIdentity	OIDC / IAM trust policy
no matching EC2 Subnet found	Subnet ID / VPC / region
InvalidSubnet	VPC/Subnets
InvalidVpc	VPC ID / region
EC2 quota error	EC2 instances / Service Quotas
Container won't start	docker ps / docker logs
HTTP 403	Authentication / authorization
HTTP 404	Route / proxy / application
Connection timeout	Security groups / routes / NACLs
Unexpected Terraform recreation	State / plan / backend
GitHub Actions failure	Failed workflow step / exact error
Lessons Learned
1. Authentication and authorization are different
A role successfully assuming does not mean it has permission to perform every AWS action.

2. Read the exact error before changing anything
The exact error often tells you which layer is broken.

3. Do not automatically blame IAM
A Terraform error can be caused by:

Wrong ID
Wrong region
Wrong VPC
Wrong subnet
Wrong configuration
Missing permission
These need to be separated.

4. State matters
Infrastructure as Code requires persistent state when running from temporary CI/CD environments.

5. Green CI does not automatically mean deployment is complete
GitHub Actions can successfully build and push a new image without automatically replacing the container already running on EC2.

6. Private infrastructure should stay private
RDS should not be exposed publicly.

7. IAM roles are preferable to long-lived AWS keys
EC2 receives AWS permissions through its IAM role.

GitHub Actions receives AWS access through OIDC.

8. Reproducibility matters
Changes should eventually be reproducible through GitHub, Docker, Terraform, and CI/CD rather than manually modifying running servers.

Current Project Status
Completed
 Three-tier application structure
 Frontend/Nginx tier
 FastAPI backend
 PostgreSQL configuration
 Docker containerization
 Git/GitHub repository
 GitHub Actions CI
 Docker image builds
 API testing
 Nginx image build
 Amazon ECR
 EC2 deployment
 EC2 IAM role for ECR
 GitHub OIDC
 IAM trust-policy troubleshooting
 CloudTrail-based OIDC debugging
 Terraform
 Terraform EC2 provisioning
 Terraform data sources
 Terraform plan/apply
 Terraform through GitHub Actions
 Terraform state moved toward S3
 AWS troubleshooting practice
 Monitoring stack planning
In Progress / Next
 Complete RDS PostgreSQL connection
 Verify API → RDS connectivity
 Verify registration/login end-to-end
 Complete frontend → Nginx → API → RDS flow
 Complete Terraform remote-state workflow
 Practice Terraform state commands
 Practice importing existing resources
 Build a larger Terraform project
 Add Application Load Balancer
 Add target groups
 Add health checks
 Add Auto Scaling
 Improve HTTPS/security
 Improve secrets management
 Expand monitoring dashboards
 Move toward Kubernetes/EKS
Terraform Learning Roadmap
The current Terraform project demonstrates the fundamentals.

Next areas:

text Terraform State ↓ Variables ↓ Outputs ↓ Modules ↓ Dependencies ↓ Lifecycle / Meta-Arguments ↓ Import ↓ Environment Separation ↓ Secrets Handling ↓ Safe Destroy / Recovery ↓ Multi-Resource Terraform Project

A strong Terraform capstone for this project would be:

text VPC | +-- Subnets | +-- Security Groups | +-- EC2 | +-- RDS | +-- Load Balancer | +-- Auto Scaling

Project Goal
The purpose of this project is not simply to deploy a website.

It demonstrates the ability to work across multiple cloud/DevOps layers:

text Linux ↓ Git ↓ GitHub ↓ Docker ↓ GitHub Actions ↓ OIDC ↓ IAM ↓ ECR ↓ EC2 ↓ VPC / Security Groups ↓ Nginx ↓ FastAPI ↓ RDS PostgreSQL ↓ Terraform ↓ Prometheus / Grafana

The project is intentionally being developed through troubleshooting rather than only following a deployment guide.

The primary objective is:

Understand what the error means, know what evidence is needed, know where to find that evidence, apply a targeted fix, and verify the result.

Portfolio Skills Demonstrated
AWS EC2
AWS VPC
AWS Security Groups
AWS IAM
AWS OIDC
AWS CloudTrail
Amazon ECR
Amazon RDS
Docker
Nginx
FastAPI
PostgreSQL
Git
GitHub
GitHub Actions
Terraform
Terraform State
CI/CD
Infrastructure as Code
Linux administration
Cloud networking
Application troubleshooting
Infrastructure troubleshooting
Monitoring with Prometheus/Grafana
Final Architecture Goal
text INTERNET | v +-------------------+ | Application | | Load Balancer | +---------+---------+ | +----------+----------+ | | v v +-------------+ +-------------+ | Nginx/Web | | API Tier | | EC2 | | FastAPI EC2 | +------+------+ +------+------+ | | +----------+----------+ | v +-------------------+ | RDS PostgreSQL | | Private | +-------------------+ Supporting Infrastructure: GitHub ↓ GitHub Actions ↓ OIDC ↓ IAM ↓ Terraform / AWS Docker ↓ Amazon ECR ↓ EC2 Prometheus ↓ Exporters ↓ Grafana

This repository represents an evolving cloud/DevOps lab focused on building practical infrastructure, automation, deployment, monitoring, and troubleshooting skills.
