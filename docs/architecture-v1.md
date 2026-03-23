# AI Enterprise Search Platform v1 Architecture

## 1. Goal

Build a production-style, Glean-like enterprise search platform with:

- AWS EKS for runtime
- AWS S3 for document object storage
- AWS ECR for container images
- Redis on Oracle Cloud as the ingestion queue
- GitLab self-hosted on Oracle Cloud for CI/CD
- Postgres for transactional and metadata storage
- Qdrant for vector search
- LangChain/Python for AI orchestration
- Spring Boot for core platform services
- React for frontend

This repo already contains early versions of:

- `apps/gateway` using KrakenD
- `apps/document` as a Spring Boot document service with S3 integration
- `apps/auth` as an authentication service

For v1, we should treat the platform as **5 core services** plus a few managed/platform dependencies.

## 2. v1 Core Services

### 2.1 API Gateway

Responsibility:

- Single public entrypoint
- JWT validation / auth propagation
- Request routing
- Rate limiting
- Basic request/response shaping

Technology:

- KrakenD initially, because the repo already uses it

Public routes:

- `/api/auth/*` if `auth` remains exposed
- `/api/documents/*`
- `/api/query/*`
- `/api/admin/*` for operational APIs later

### 2.2 Document Service

Responsibility:

- Accept document uploads
- Store raw files in S3
- Persist document metadata/status in Postgres
- Generate presigned S3 download URLs
- Emit ingestion jobs into Redis
- Manage connectors and crawl registrations later

Technology:

- Spring Boot
- Postgres
- AWS SDK for S3
- Redis producer

Key states:

- `RECEIVED`
- `UPLOADED`
- `QUEUED`
- `PROCESSING`
- `INDEXED`
- `FAILED`

### 2.3 Worker Service

Responsibility:

- Consume ingestion jobs from Redis
- Fetch document from S3
- Extract text and metadata
- Chunk documents
- Generate embeddings
- Upsert vectors into Qdrant
- Write chunk metadata / job status back to Postgres

Technology:

- Python
- LangChain
- Redis consumer
- Qdrant client
- Postgres client

Why Python here:

- This is where LangChain, document parsing, OCR hooks, and model orchestration fit naturally

### 2.4 Query Service

Responsibility:

- Handle search and chat-style query flows
- Embed user query
- Retrieve relevant vectors from Qdrant
- Re-rank and assemble context
- Call LLM for answer generation
- Enforce authorization filters in retrieval
- Return answer + citations/snippets

Technology:

- Python
- LangChain
- Qdrant
- Postgres
- Optional Redis cache for hot queries

### 2.5 Vector DB

Responsibility:

- Store embeddings
- Filter by tenant/source/document metadata
- Return nearest-neighbor matches

Technology:

- Qdrant

Note:

- Qdrant is a deployable platform component, but for v1 it is acceptable to count it as one of the 5 runtime services since it is central to the product.

## 3. Supporting Platform Dependencies

These are not counted as the 5 core services, but they are required.

### 3.1 Postgres

Stores:

- tenants / organizations
- users / groups / ACL mappings
- document metadata
- source connector metadata
- ingestion jobs
- chunk registry
- query logs
- audit events

### 3.2 Redis on Oracle Cloud

Uses:

- ingestion queue
- retry queue / dead-letter handling
- lightweight distributed work coordination

Design note:

- Because Redis is outside AWS, all queue traffic crosses clouds. Keep ingestion asynchronous and idempotent so short network issues do not become user-facing failures.

### 3.3 AWS S3

Stores:

- original uploaded files
- normalized extracted artifacts if needed
- OCR outputs for large files later

### 3.4 Existing Auth Service

Your repo already has `apps/auth`. For v1 we have two realistic options:

- Keep it as a supporting sixth service for local/dev and early production
- Replace it later with enterprise SSO/IdP integration while the gateway validates tokens

Recommended path:

- Keep `auth` for now because it already exists
- Treat it as a supporting service, not part of the 5-service product boundary

## 4. Multicloud Deployment Model

### AWS

Run on AWS EKS:

- gateway
- document-service
- worker-service
- query-service
- qdrant
- postgres if self-managed in-cluster for dev only

Use AWS managed services in production where possible:

- EKS
- S3
- ECR
- AWS Load Balancer Controller for ingress
- Secrets Manager or External Secrets for secret delivery

### Oracle Cloud

Run on Oracle Cloud:

- GitLab
- Redis

Connectivity:

- Site-to-site VPN or private interconnect between AWS VPC and OCI VCN
- Restrict Redis exposure to private network ranges
- Use TLS and authentication for Redis

Important risk:

- Cross-cloud latency between EKS and OCI Redis will directly impact ingestion throughput

Mitigation:

- Use batched workers
- Keep queue payloads lightweight
- Store document content in S3, not in Redis messages
- Make jobs idempotent by `job_id` and `document_version`

## 5. High-Level Request and Ingestion Flows

### 5.1 Upload / Index Flow

1. User uploads a file through frontend
2. Request goes to API Gateway
3. Gateway forwards to Document Service
4. Document Service stores file in S3
5. Document Service writes metadata row in Postgres
6. Document Service publishes ingestion job to Redis
7. Worker Service consumes job
8. Worker downloads file from S3
9. Worker extracts text, chunks content, generates embeddings
10. Worker upserts vectors into Qdrant
11. Worker updates document/job status in Postgres

### 5.2 Query / Answer Flow

1. User sends search or chat query through frontend
2. Gateway forwards to Query Service
3. Query Service validates tenant/user scope from JWT
4. Query Service embeds query
5. Query Service searches Qdrant with metadata filters
6. Query Service fetches document metadata/snippets from Postgres if needed
7. Query Service calls LLM with retrieved context
8. Query Service returns answer, citations, and matched documents

## 6. Core Data Boundaries

### Postgres

Suggested logical tables:

- `tenants`
- `users`
- `groups`
- `documents`
- `document_versions`
- `document_acl`
- `ingestion_jobs`
- `document_chunks`
- `query_logs`
- `connector_runs`

### Redis Job Payload

Keep payload minimal:

```json
{
  "job_id": "uuid",
  "tenant_id": "t1",
  "document_id": "uuid",
  "document_version": 3,
  "bucket": "enterprise-search-docs",
  "object_key": "tenant-a/emp001/doc123/file.pdf",
  "source_type": "upload",
  "requested_at": "2026-03-19T10:00:00Z"
}
```

### Qdrant Payload

Vector payload metadata should include:

- `tenant_id`
- `document_id`
- `document_version`
- `chunk_id`
- `source_type`
- `owner_emp_id`
- `acl_tags`
- `content_type`
- `created_at`

This is important so retrieval can apply authorization and tenant filters before generation.

## 7. Kubernetes Architecture

### Namespaces

Recommended namespaces:

- `search-ingress`
- `search-app`
- `search-data`
- `search-observability`

### Workloads

- `gateway` as a Deployment
- `document-service` as a Deployment
- `query-service` as a Deployment
- `worker-service` as a Deployment with autoscaling on queue depth
- `qdrant` as a StatefulSet
- `postgres` as StatefulSet only for dev/non-prod if self-hosted

### Ingress

- Public ALB -> KrakenD
- Internal ClusterIP services behind gateway

### Config and Secrets

- ConfigMaps for non-secret runtime config
- Secrets via External Secrets or Sealed Secrets
- IRSA for S3 access from EKS pods

### Scaling Rules

- Gateway scales on CPU / RPS
- Document Service scales on request volume
- Query Service scales on CPU + latency
- Worker Service scales on Redis queue depth
- Qdrant scales vertically first, then by collection/shard strategy later

## 8. Security Model

### Authentication

Short term:

- Existing `auth` service issues JWTs

Long term:

- Enterprise SSO via OIDC/SAML

### Authorization

Enforce at retrieval time using:

- tenant isolation
- per-document ACL metadata
- group membership expansion

### Secrets

Store:

- AWS credentials only for local dev
- In production prefer IAM roles / IRSA
- GitLab CI deploy credentials in GitLab protected variables
- Redis credentials in Kubernetes secrets
- LLM API keys in secrets manager

### Network Controls

- Private subnets for app/data workloads
- Security groups limiting Redis/Postgres/Qdrant access
- mTLS later for service-to-service traffic if using a service mesh

## 9. Observability and Operations

Must-have v1 telemetry:

- structured logs with `trace_id`, `tenant_id`, `document_id`, `job_id`
- Prometheus metrics
- Grafana dashboards
- OpenTelemetry tracing
- Sentry or equivalent application error tracking

Important dashboards:

- upload success/failure rate
- queue depth and worker lag
- document processing latency
- embedding latency
- query latency p50/p95/p99
- Qdrant search latency

## 10. CI/CD Design

GitLab on Oracle Cloud drives builds and deploys.

### Pipeline Stages

1. lint
2. unit-test
3. integration-test
4. build-image
5. security-scan
6. push-to-ecr
7. deploy-dev
8. smoke-test
9. deploy-staging
10. deploy-prod

### Build Strategy

- Build Spring Boot services into OCI-compatible images
- Build Python services into slim images
- Push all images to AWS ECR

### Deploy Strategy

- GitLab runner triggers Helm upgrade into EKS
- Separate values files per environment
- Prefer GitOps later, but direct Helm from GitLab is fine for v1

### Release Strategy

- trunk-based development
- semantic image tags: `service:gitsha`
- optional stable tag per environment: `service:dev`, `service:staging`

## 11. Recommended Repository Structure

This structure fits the existing repo and leaves room for growth.

```text
enterprise-search-platform/
├── apps/
│   ├── gateway/                    # KrakenD config and gateway image
│   ├── auth/                       # Existing supporting auth service
│   ├── document-service/           # Spring Boot metadata + upload service
│   ├── worker-service/             # Python LangChain ingestion workers
│   ├── query-service/              # Python LangChain query/RAG service
│   └── web/                        # React frontend
├── shared/
│   ├── contracts/                  # OpenAPI, async schemas, shared DTO specs
│   ├── libs/
│   │   ├── java/                   # Shared Java libs if needed
│   │   └── python/                 # Shared Python utilities if needed
│   └── schemas/                    # JSON schemas for queue payloads and configs
├── infra/
│   ├── terraform/
│   │   ├── aws/
│   │   │   ├── bootstrap/          # state buckets, roles, base networking
│   │   │   ├── eks/
│   │   │   ├── ecr/
│   │   │   ├── s3/
│   │   │   ├── iam/
│   │   │   └── observability/
│   │   └── oci/
│   │       ├── gitlab/
│   │       ├── redis/
│   │       └── network/
│   └── scripts/                    # bootstrap and ops scripts
├── platform/
│   ├── helm/
│   │   ├── enterprise-search/      # umbrella chart
│   │   └── charts/
│   │       ├── gateway/
│   │       ├── document-service/
│   │       ├── worker-service/
│   │       ├── query-service/
│   │       ├── qdrant/
│   │       └── web/
│   ├── environments/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── policies/                   # network policies, pod security, RBAC
├── docs/
│   ├── architecture-v1.md
│   ├── api/
│   ├── decisions/
│   └── runbooks/
├── .gitlab-ci.yml
├── docker-compose.yml
└── README.md
```

## 12. How the Current Repo Should Evolve

Recommended near-term repo changes:

- rename `apps/document` -> `apps/document-service`
- keep `apps/auth` as-is for now
- add `apps/worker-service`
- add `apps/query-service`
- add `apps/web`
- convert `platform/helm` into real charts
- populate `infra/terraform/aws` and `infra/terraform/oci`
- define shared queue schema under `shared/schemas`

## 13. Recommended v1 API Ownership

### Gateway

- route definitions
- auth validation config
- public API surface

### Document Service

- `POST /documents`
- `GET /documents/{id}`
- `GET /documents/{id}/download-url`
- `GET /documents/{id}/status`
- `POST /documents/{id}/reindex`

### Query Service

- `POST /query/search`
- `POST /query/ask`
- `GET /query/suggestions`

### Worker Service

- internal only
- optional health/admin endpoints

## 14. Recommended Non-Functional Requirements for v1

- multi-tenant isolation from day one
- idempotent ingestion
- retries with dead-letter queue
- presigned S3 access instead of proxying large downloads through services
- document versioning support
- traceable ingestion pipeline
- environment-specific configs with no hardcoded endpoints

## 15. Suggested Build Order

1. Stabilize `gateway` and `document-service`
2. Introduce Postgres schema for documents + ingestion jobs
3. Add Redis producer flow from document upload
4. Build `worker-service` ingestion loop
5. Stand up Qdrant and vector upsert pipeline
6. Build `query-service` retrieval + answer flow
7. Add React frontend
8. Add Helm charts and GitLab CI/CD
9. Harden observability, retries, and security

## 16. Recommended Architecture Decision for v1

If we want the cleanest path with your current repo:

- Keep Spring Boot for control-plane and metadata APIs
- Use Python only where AI/embedding/RAG complexity lives
- Use KrakenD as the north-south gateway
- Treat Redis as an external queue abstraction, with the option to migrate later
- Keep auth separate for now, but do not let it block the core 5-service architecture

This gives you a practical v1 that matches the current codebase, supports multicloud constraints, and can grow into a more enterprise-grade system without re-platforming early.
