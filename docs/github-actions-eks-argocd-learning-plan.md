# GitHub Actions, ECR, EKS, and Argo CD Learning Plan

This document defines what we will learn before implementing the production CI/CD pipeline for this repository. It is intentionally a plan only. No workflow, infrastructure, or deployment behavior is changed by this document.

## Goal

Build a proper end-to-end delivery path for the enterprise search platform:

1. Learn GitHub Actions fundamentals correctly.
2. Handle secrets and cloud access securely.
3. Run code quality, tests, and security scans.
4. Build Docker images for services.
5. Push versioned images to Amazon ECR.
6. Deploy application changes to Amazon EKS.
7. Introduce Argo CD for GitOps-based Kubernetes delivery.
8. Add operational checks, approvals, rollback strategy, and observability.

## Target Architecture

The target pipeline should separate continuous integration from continuous delivery.

CI will run in GitHub Actions:

- Checkout source code.
- Validate formatting and linting.
- Run unit and integration tests.
- Run dependency, container, and secret scans.
- Build Docker images.
- Push immutable image tags to Amazon ECR.
- Update deployment metadata for GitOps.

CD will be handled by Argo CD:

- Watch a GitOps repository or deployment path.
- Detect image or manifest changes.
- Sync changes into EKS.
- Report deployment health.
- Support rollback through Git history or Argo CD rollback.

GitHub Actions should not directly mutate the cluster for normal application deployment once Argo CD is introduced. GitHub Actions prepares and publishes artifacts; Argo CD reconciles Kubernetes state.

## What We Will Learn

### 1. GitHub Actions Fundamentals

Topics:

- Workflow file structure.
- Events: `push`, `pull_request`, `workflow_dispatch`, tags, and releases.
- Jobs, steps, runners, and runner labels.
- Hosted runners versus self-hosted runners.
- Job dependencies with `needs`.
- Environment variables and outputs.
- Reusable workflows.
- Composite actions.
- Workflow permissions.
- Caching dependencies.
- Matrix builds for multiple services.

Expected outcome:

- We can explain how a workflow runs from trigger to job completion.
- We can design separate CI jobs for frontend, Java services, Python services, Docker builds, and deployment preparation.

### 2. Runner Strategy

Topics:

- When to use GitHub-hosted runners.
- When self-hosted runners are justified.
- Risks of Docker socket access.
- Runner isolation.
- Ephemeral runners.
- Runner labels and job routing.
- Cleaning workspaces between jobs.

Expected outcome:

- We choose a runner model deliberately.
- We avoid giving broad host access to untrusted workflows.
- We understand the security difference between local testing runners and production CI runners.

### 3. Secrets and Identity

Topics:

- GitHub repository secrets.
- GitHub organization secrets.
- GitHub environments and environment-scoped secrets.
- Required reviewers for protected environments.
- Avoiding plaintext secrets in workflow files.
- Secret masking limitations.
- AWS IAM roles.
- GitHub OIDC federation with AWS.
- Short-lived AWS credentials.
- Least-privilege IAM policies.

Expected outcome:

- We avoid static AWS access keys where possible.
- GitHub Actions authenticates to AWS using OIDC.
- Secrets are scoped by environment, not globally shared across every job.

### 4. Branching, Environments, and Promotion

Topics:

- Pull request validation.
- Main branch build.
- Preview or development environment.
- Staging environment.
- Production environment.
- Manual approvals.
- Deployment protection rules.
- Release tags.
- Semantic versioning.

Expected outcome:

- Pull requests run validation only.
- Merges to `main` can publish images and update development or staging.
- Production requires an explicit approval or release event.

### 5. Code Quality and Tests

Topics:

- Java build and tests with Maven.
- Python test strategy.
- Frontend build and checks.
- Service-level test jobs.
- Integration tests with Docker Compose dependencies.
- Test reports and artifacts.
- Required status checks.

Expected outcome:

- A failing test blocks image publishing and deployment.
- Each service has a clear validation path.
- Test output is visible in GitHub Actions.

### 6. Security Scanning

Topics:

- Secret scanning.
- Dependency vulnerability scanning.
- Container image scanning.
- Static analysis.
- Software bill of materials.
- License checks.
- Supply chain risks in third-party actions.
- Pinning GitHub Actions by version or SHA.

Candidate tools:

- GitHub Advanced Security or open-source alternatives.
- Trivy for container and dependency scans.
- Gitleaks for secret scanning.
- Semgrep or CodeQL for static analysis.
- Syft for SBOM generation.
- Grype for vulnerability scanning.

Expected outcome:

- We define which scans are blocking and which are advisory.
- Critical issues block deployment.
- Scan results are stored as workflow artifacts or GitHub security reports.

### 7. Docker Image Build Strategy

Topics:

- Dockerfile review per service.
- Build context minimization.
- Multi-stage builds.
- BuildKit.
- Image tagging strategy.
- Immutable tags using commit SHA.
- Human-friendly tags for branches and releases.
- Multi-architecture builds if needed.
- Image provenance and attestations.

Expected outcome:

- Every deployable service produces a reproducible image.
- Images are tagged with commit SHA.
- Production deployments never depend on mutable `latest` tags.

### 8. Amazon ECR

Topics:

- ECR repository layout.
- Repository naming by service.
- Authentication from GitHub Actions to ECR.
- Lifecycle policies.
- Image scanning in ECR.
- Cross-account access if needed.
- Retention rules.

Expected outcome:

- GitHub Actions can push images to ECR using short-lived AWS credentials.
- ECR stores immutable build artifacts.
- Old images are cleaned up safely.

### 9. Amazon EKS

Topics:

- EKS cluster basics.
- Kubernetes namespaces.
- Deployments, Services, Ingress, ConfigMaps, and Secrets.
- IAM roles for service accounts.
- Cluster access control.
- Environment separation.
- Kubernetes health checks.
- Resource requests and limits.
- Horizontal scaling.

Expected outcome:

- We understand what must exist in the cluster before application deployment.
- Application manifests are environment-aware.
- Cluster access is not granted broadly to every workflow job.

### 10. Argo CD and GitOps

Topics:

- GitOps principles.
- Argo CD Applications.
- App of Apps pattern.
- Helm, Kustomize, or plain manifests.
- Sync policies.
- Manual versus automatic sync.
- Health checks.
- Drift detection.
- Rollback.
- Image update strategies.

Expected outcome:

- Argo CD owns Kubernetes deployment reconciliation.
- GitHub Actions updates GitOps state after publishing images.
- Argo CD deploys the exact image tag produced by CI.

### 11. Pipeline Design With Argo CD

Initial target flow:

1. Developer opens a pull request.
2. GitHub Actions runs linting, tests, and security checks.
3. Pull request cannot merge unless required checks pass.
4. Merge to `main` triggers image builds.
5. Images are pushed to ECR with commit SHA tags.
6. GitHub Actions updates the GitOps manifest or values file with the new image tag.
7. Argo CD detects the Git change.
8. Argo CD syncs the application to EKS.
9. Argo CD reports health and sync status.

Production flow:

1. A release tag or manual workflow starts production promotion.
2. GitHub environment approval is required.
3. GitOps production manifests are updated.
4. Argo CD syncs production after approval.
5. Rollback is done by reverting the GitOps change or using Argo CD rollback.

## Repository Areas We Will Eventually Touch

Likely future implementation areas:

- `.github/workflows/`
- `docker-compose.yml`
- Service Dockerfiles, if missing or incomplete.
- Kubernetes manifests or Helm charts.
- Argo CD application manifests.
- Documentation for local and cloud setup.

This planning document does not modify any of those areas.

## Implementation Phases

### Phase 1: GitHub Actions Basics

- Keep the existing self-hosted runner smoke test.
- Add simple validation workflows.
- Learn workflow triggers, jobs, steps, and runner labels.
- Avoid AWS or deployment changes in this phase.

### Phase 2: Service Validation

- Add Java build and test jobs.
- Add Python test jobs.
- Add frontend lint/build jobs.
- Add dependency caching.
- Publish test reports as artifacts.

### Phase 3: Security Baseline

- Add secret scanning.
- Add dependency scanning.
- Add static analysis.
- Add container scanning after images are introduced.
- Decide blocking thresholds.

### Phase 4: AWS Authentication

- Configure GitHub OIDC with AWS.
- Create least-privilege IAM roles.
- Test AWS identity without pushing or deploying.
- Remove need for long-lived AWS keys.

### Phase 5: Image Build and ECR Push

- Create or refine Dockerfiles.
- Build each service image.
- Tag images with commit SHA.
- Push to ECR.
- Add ECR lifecycle policies.

### Phase 6: EKS Deployment Foundation

- Define Kubernetes namespaces.
- Define application manifests or Helm charts.
- Configure ingress, config, and secrets strategy.
- Validate deployment manually before automation.

### Phase 7: Argo CD GitOps

- Install or connect Argo CD.
- Define Argo CD applications.
- Decide GitOps repository structure.
- Let Argo CD deploy to development first.
- Add staging and production promotion later.

### Phase 8: Production Controls

- Add GitHub environments.
- Add manual approvals.
- Add deployment status reporting.
- Add rollback procedures.
- Add audit documentation.

## Security Rules We Should Follow

- Do not commit tokens, credentials, kubeconfigs, or cloud keys.
- Prefer GitHub OIDC over static AWS secrets.
- Restrict GitHub token permissions per workflow.
- Do not give pull request workflows access to deployment secrets.
- Do not deploy from untrusted forked pull requests.
- Pin third-party GitHub Actions to trusted versions or SHAs.
- Use immutable image tags for deployment.
- Avoid deploying mutable `latest` tags.
- Keep production deployment behind approvals.
- Keep self-hosted runners isolated from sensitive host resources.

## Questions To Answer Before Implementation

- Will we use GitHub-hosted runners, self-hosted runners, or both?
- Which AWS account and region will host ECR and EKS?
- What are the service names and final Docker image names?
- Will Kubernetes manifests live in this repository or a separate GitOps repository?
- Will we use Helm, Kustomize, or plain YAML?
- Will Argo CD use automatic sync for development?
- Should staging and production require manual sync or approval?
- Which scans must block merge?
- Which scans must block deployment?
- What rollback strategy do we want for each environment?

## Suggested Learning Order

1. GitHub Actions fundamentals.
2. Workflow permissions and secret handling.
3. Runner security.
4. Test and build workflows.
5. Security scanning.
6. AWS OIDC.
7. Docker image builds.
8. ECR push.
9. Kubernetes and EKS basics.
10. Argo CD and GitOps.
11. Promotion, approvals, rollback, and observability.

## Definition of Done For The Future Pipeline

The final pipeline should be considered ready when:

- Pull requests run all required checks.
- Main branch builds deployable images.
- Images are pushed to ECR with immutable tags.
- Critical security issues block deployment.
- AWS access uses OIDC and least privilege.
- Argo CD deploys to EKS from Git-tracked desired state.
- Staging and production have clear promotion rules.
- Rollback is documented and tested.
- Secrets are not stored in source control or workflow files.
- The team can explain each step of the pipeline and why it exists.
