# Post-Phase 4: Retrieval, Prompting, Evaluation, and Memory

## Objective

Improve retrieval relevance and agent consistency after Phase 4 establishes the
security, privacy, and grounding boundaries.

## Phase 5: Metadata Filtering and Isolation

Metadata filtering is applied before lexical or vector retrieval. It improves
relevance and is required for tenant isolation.

### Log Metadata

- Tenant, environment, service, level, and timestamp.
- Status code, endpoint, exception type, trace ID, and request ID.

### RAG Metadata

- Tenant, team, service, environment, document type, source, and version.
- Creation time, validity period, and access classification.

### Work

- Define a shared filter schema with Pydantic.
- Extract filters from requests using deterministic parsing first.
- Validate inferred filters before executing retrieval.
- Enforce authorization filters in backend code.
- Add filter indexes and payload indexes where supported.
- Return applied filters in result metadata for auditing.

## Phase 6: BM25 and Hybrid Retrieval

### Logs

Use OpenSearch BM25 through controlled `match` and `multi_match` queries for exact
operational terms such as exception names, endpoints, error codes, and class names.
Combine BM25 with structured metadata filters and time ranges.

### RAG Documents

Use hybrid retrieval:

```text
Dense semantic retrieval
        +
Sparse/BM25 lexical retrieval
        |
Reciprocal Rank Fusion
        |
Candidate documents
```

Keep RAG documents in Qdrant and add sparse vectors, or maintain a synchronized
lexical document index in OpenSearch. Prefer one authoritative ingestion pipeline
regardless of the selected storage approach.

### Embedding Improvement

`bert-base-uncased` is a base language model rather than a retrieval-optimized
sentence embedding model. Evaluate a small sentence-transformer embedding model
before tuning fusion weights.

## Phase 7: Reranking

Retrieve a broad candidate set and rerank only the final candidates:

```text
BM25 top 20 + dense top 20
 -> fuse and deduplicate
 -> cross-encoder reranker
 -> final top 5
```

An initial small model candidate is:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

### Work

- Add reranking after hybrid retrieval and before prompt construction.
- Preserve original lexical, dense, fusion, and reranker scores.
- Set a bounded candidate count to control latency.
- Evaluate relevance before and after reranking.
- Skip reranking for exact trace ID, request ID, or document ID lookups.

## Phase 8: Prompt Architecture

### Zero-Shot Baseline

Continue using zero-shot instructions for simple tool routing, summaries, and
final-answer generation. Measure baseline behavior before adding examples.

### Few-Shot Prompting

Add small, curated examples where output consistency matters:

- Tool selection and multi-tool sequencing.
- Domain refusal versus error-specific code assistance.
- Root-cause and remediation result structure.
- Dashboard specification generation.
- Insufficient-evidence responses.

Store prompts separately from service implementation:

```text
app/prompts/
  enterprise_agent.py
  domain_classifier.py
  remediation.py
  dashboard.py
```

Do not request or expose hidden chain-of-thought. Require concise evidence,
decisions, confidence, and tool traces instead.

## Phase 9: Evaluation and Retrieval Testing

### Datasets

- Exact log lookup queries.
- Service, environment, and time-filter queries.
- Known incident and runbook questions.
- Multi-tool investigations.
- Unrelated and adversarial requests.
- Cases with insufficient or conflicting evidence.

### Metrics

- Retrieval recall and precision at K.
- Reranker relevance.
- Tool-selection accuracy.
- Evidence faithfulness and unsupported-claim rate.
- Domain refusal precision and recall.
- PII leakage rate.
- End-to-end latency and provider-fallback behavior.

Use MLflow for traces, experiment metadata, parameters, and result comparison.
Add DeepEval or another focused evaluation package only after the golden dataset
and expected behavior are defined.

## Phase 10: Conversation Context Management

- Monitor model context usage by session.
- Keep recent messages and current tool evidence in short-term memory.
- Summarize older conversation sections when a token threshold is reached.
- Preserve links from summaries to persisted chat messages.
- Prevent summaries from overriding newer evidence.

## Phase 11: Long-Term Memory

Use a separate Qdrant collection from RAG documents.

### Semantic Memory

- Durable user, team, service, environment, and incident facts.
- Provenance, confidence, timestamps, access scope, and expiration.

### Procedural Memory

- Reusable investigation workflows.
- Explicit versioning and review before procedures influence agent behavior.

Memory extraction should run after the response and must use sanitized content.
Retrieval must apply the same tenant and authorization filters as other data.

## Phase 12: Semantic Cache

- Cache semantically equivalent, low-volatility requests.
- Include tenant, filters, time range, index version, tool version, and model
  configuration in cache identity.
- Use short TTLs or bypass caching for live log investigations.
- Never reuse cached results across tenants or authorization scopes.
- Evaluate hit quality and stale-result risk before enabling by default.

## Recommended Build Order

1. Metadata filtering and tenant isolation.
2. OpenSearch BM25 improvements.
3. Hybrid dense and sparse RAG retrieval.
4. Candidate fusion and reranking.
5. Structured prompt modules and selected few-shot examples.
6. Golden datasets and retrieval/agent evaluations.
7. Conversation context summarization.
8. Semantic and procedural long-term memory.
9. Semantic caching.

