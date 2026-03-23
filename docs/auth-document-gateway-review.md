# Auth, Document, Gateway Review

Date: 2026-03-19

Scope reviewed:

- `apps/auth`
- `apps/document`
- `apps/gateway`

Current status:

- Good enough for local prototype wiring
- Not yet ready to be treated as production-style platform components

## Summary

The current implementation already covers the happy path:

- auth can issue JWTs
- gateway can route requests
- document service can upload to S3 and generate download URLs

The main gaps before calling these services "almost ready" are:

- secret management
- password security
- document authorization
- production-safe JWT validation and key handling

## Findings

### 1. Hardcoded secrets and credentials in config

Severity: High

Files:

- [application.properties](d:/enterprise-search-platform/apps/auth/src/main/resources/application.properties#L6)
- [application.properties](d:/enterprise-search-platform/apps/auth/src/main/resources/application.properties#L28)
- [application.properties](d:/enterprise-search-platform/apps/document/src/main/resources/application.properties#L6)

Issue:

- DB credentials and JWT secret fallback values are committed in application config.
- This is unsafe and also makes environment separation harder.

Why it matters:

- Secrets should not live in source control.
- Production and local/dev config boundaries will become messy very quickly.

Recommended fix:

- move all DB credentials and JWT secrets to environment variables or secret managers
- remove sensitive fallback values from committed properties files
- add env-specific config profiles

### 2. Passwords are compared in plaintext

Severity: High

Files:

- [UsersServiceImpl.java](d:/enterprise-search-platform/apps/auth/src/main/java/com/enterprise/auth/service/impl/UsersServiceImpl.java#L42)
- [Users.java](d:/enterprise-search-platform/apps/auth/src/main/java/com/enterprise/auth/entity/Users.java#L36)

Issue:

- Login compares the request password directly to the stored DB password.

Why it matters:

- This is not acceptable outside a demo.
- Passwords should be stored hashed, not raw.

Recommended fix:

- store hashed passwords with `BCryptPasswordEncoder` or `Argon2`
- update login flow to verify hashes rather than raw string equality

### 3. Document authorization is missing at the service layer

Severity: High

Files:

- [DocumentController.java](d:/enterprise-search-platform/apps/document/src/main/java/com/enterprise/document/controller/DocumentController.java#L37)
- [DocumentService.java](d:/enterprise-search-platform/apps/document/src/main/java/com/enterprise/document/services/DocumentService.java#L73)

Issue:

- Download URL generation is based only on `docId`.
- There is no service-side ownership or tenant check.

Why it matters:

- Any valid token could potentially access another user’s document if they know or obtain the `docId`.

Recommended fix:

- propagate user identity and tenant context from JWT claims
- enforce ownership / ACL checks inside document service
- avoid relying only on gateway validation for authorization

### 4. Upload flow trusts `empId` from the client

Severity: Medium

Files:

- [DocumentController.java](d:/enterprise-search-platform/apps/document/src/main/java/com/enterprise/document/controller/DocumentController.java#L30)

Issue:

- The upload API accepts `empId` from request input instead of deriving identity from the authenticated token.

Why it matters:

- A caller can claim another employee ID unless the value is cross-checked against token claims.

Recommended fix:

- extract employee identity from JWT claims forwarded by gateway
- ignore or validate client-provided `empId`

### 5. Gateway uses a static local symmetric JWK file

Severity: High

Files:

- [krakend.json](d:/enterprise-search-platform/apps/gateway/krakend.json#L83)
- [jwk.json](d:/enterprise-search-platform/apps/gateway/jwk.json#L4)
- [JwtUtil.java](d:/enterprise-search-platform/apps/auth/src/main/java/com/enterprise/auth/utils/JwtUtil.java#L30)

Issue:

- Gateway validates JWTs using a local symmetric key file that must stay manually aligned with auth service secret configuration.

Why it matters:

- This is fragile across environments.
- It makes key rotation and operational safety harder.

Recommended fix:

- for local dev, keep this approach temporarily if needed
- for production-style design, move toward proper key distribution or OIDC/JWKS publishing
- at minimum, ensure gateway and auth consume the secret from the same externalized source

### 6. S3 config is localstack-centric

Severity: Medium

Files:

- [S3Config.java](d:/enterprise-search-platform/apps/document/src/main/java/com/enterprise/document/config/S3Config.java#L24)
- [S3Config.java](d:/enterprise-search-platform/apps/document/src/main/java/com/enterprise/document/config/S3Config.java#L36)
- [application.properties](d:/enterprise-search-platform/apps/document/src/main/resources/application.properties#L30)

Issue:

- `endpointOverride` is always configured, which is ideal for LocalStack but not for real AWS runtime.

Why it matters:

- In production on EKS, you typically want AWS-native endpoints and IAM/IRSA instead of static access keys and custom endpoints.

Recommended fix:

- make endpoint override optional
- support local and AWS runtime profiles separately
- use IAM roles in EKS rather than static credentials

### 7. Auth service mixes WebFlux, MVC, and blocking JPA

Severity: Medium

Files:

- [pom.xml](d:/enterprise-search-platform/apps/auth/pom.xml#L45)
- [pom.xml](d:/enterprise-search-platform/apps/auth/pom.xml#L50)

Issue:

- The auth service includes both `spring-boot-starter-webflux` and `spring-boot-starter-webmvc`, while the persistence layer is blocking JPA.

Why it matters:

- It adds unnecessary complexity and can confuse runtime behavior and future maintenance.

Recommended fix:

- simplify auth to MVC + JPA unless there is a strong reason to keep WebFlux

### 8. Duplicate JWT dependency declaration

Severity: Low

Files:

- [pom.xml](d:/enterprise-search-platform/apps/auth/pom.xml#L100)

Issue:

- `jjwt-api` is declared twice.

Why it matters:

- Mostly cleanup, but it should be removed to keep dependency management clear.

Recommended fix:

- remove the duplicate dependency entry

### 9. Upload path reads full files into memory

Severity: Low

Files:

- [DocumentService.java](d:/enterprise-search-platform/apps/document/src/main/java/com/enterprise/document/services/DocumentService.java#L51)
- [application.properties](d:/enterprise-search-platform/apps/document/src/main/resources/application.properties#L39)

Issue:

- Upload uses `file.getBytes()` while max upload size is configured up to `100MB`.

Why it matters:

- Under concurrent uploads, memory pressure can grow quickly.

Recommended fix:

- prefer streaming upload to S3 for larger files
- set conservative limits until worker pipeline and infra are in place

## Practical Assessment

### What is already good

- clear service separation is starting to emerge
- JWT issuance is implemented
- gateway routing is wired
- document upload + presigned download flow exists
- S3 integration is already connected

### What must be fixed before calling this production-style

- remove committed secrets
- hash passwords
- enforce ownership/ACL checks in document access
- stop trusting raw `empId` from request input
- make JWT validation/key distribution safer
- split local-dev and production runtime config

## Suggested Priority Order

1. Secret cleanup and config externalization
2. Password hashing in auth
3. Authorization enforcement in document service
4. JWT/key handling cleanup between auth and gateway
5. LocalStack-vs-AWS profile separation
6. Dependency and upload-path cleanup

## Note For Later

Because the next major focus is the AI side of the platform, this review can stay as a hardening backlog for the existing platform services while we move forward with:

- worker-service
- query-service
- Redis ingestion pipeline
- Qdrant integration
- AI retrieval and answer flow
