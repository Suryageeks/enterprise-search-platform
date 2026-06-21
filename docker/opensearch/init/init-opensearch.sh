#!/bin/sh
set -eu

OPENSEARCH_URL="${OPENSEARCH_URL:-http://opensearch:9200}"
INDEX_NAME="${OPENSEARCH_LOG_INDEX:-normalized-logs-v1}"
ALIAS_NAME="${OPENSEARCH_LOG_ALIAS:-normalized-logs}"

echo "Waiting for OpenSearch at ${OPENSEARCH_URL}"
until curl -fsS "${OPENSEARCH_URL}/_cluster/health" >/dev/null; do
  sleep 2
done

echo "Creating index template for normalized logs"
curl -fsS -X PUT "${OPENSEARCH_URL}/_index_template/normalized-logs-template" \
  -H "Content-Type: application/json" \
  --data-binary @- <<'JSON'
{
  "index_patterns": ["normalized-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "dynamic": true,
      "properties": {
        "timestamp": { "type": "date" },
        "service": { "type": "keyword" },
        "environment": { "type": "keyword" },
        "level": { "type": "keyword" },
        "message": {
          "type": "text",
          "fields": {
            "keyword": { "type": "keyword", "ignore_above": 512 }
          }
        },
        "traceId": { "type": "keyword" },
        "requestId": { "type": "keyword" },
        "statusCode": { "type": "integer" },
        "host": { "type": "keyword" },
        "endpoint": { "type": "keyword" },
        "exceptionType": { "type": "keyword" },
        "tags": { "type": "keyword" },
        "rawSource": { "type": "keyword" },
        "ingestedAt": { "type": "date" },
        "durationMs": { "type": "integer" },
        "method": { "type": "keyword" },
        "userId": { "type": "keyword" }
      }
    }
  }
}
JSON

if curl -fsS -I "${OPENSEARCH_URL}/${INDEX_NAME}" >/dev/null; then
  echo "Index ${INDEX_NAME} already exists"
else
  echo "Creating ${INDEX_NAME}"
  curl -fsS -X PUT "${OPENSEARCH_URL}/${INDEX_NAME}" \
    -H "Content-Type: application/json" \
    --data-binary @- <<JSON
{
  "aliases": {
    "${ALIAS_NAME}": {}
  }
}
JSON
fi

echo "Loading mock normalized log data"
curl -fsS -X POST "${OPENSEARCH_URL}/${INDEX_NAME}/_bulk?refresh=true" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @- <<'NDJSON'
{"index":{"_id":"mock-001"}}
{"timestamp":"2026-06-13T04:00:00Z","service":"gateway","environment":"dev","level":"INFO","message":"Request routed to payment service","traceId":"trace-1001","requestId":"req-1001","statusCode":200,"host":"gateway-1","endpoint":"/payments/charge","method":"POST","durationMs":42,"tags":["gateway","payments"],"rawSource":"mock-payment.log","ingestedAt":"2026-06-13T04:00:05Z","userId":"user-001"}
{"index":{"_id":"mock-002"}}
{"timestamp":"2026-06-13T04:01:00Z","service":"payment","environment":"dev","level":"ERROR","message":"Database timeout while charging order","traceId":"trace-1002","requestId":"req-1002","statusCode":502,"host":"payment-1","endpoint":"/payments/charge","method":"POST","durationMs":3500,"exceptionType":"TimeoutException","tags":["payments","database"],"rawSource":"mock-payment.log","ingestedAt":"2026-06-13T04:01:05Z","userId":"user-002"}
{"index":{"_id":"mock-003"}}
{"timestamp":"2026-06-13T04:02:00Z","service":"payment","environment":"dev","level":"ERROR","message":"Database timeout while charging order","traceId":"trace-1003","requestId":"req-1003","statusCode":504,"host":"payment-2","endpoint":"/payments/charge","method":"POST","durationMs":4200,"exceptionType":"TimeoutException","tags":["payments","database"],"rawSource":"mock-payment.log","ingestedAt":"2026-06-13T04:02:05Z","userId":"user-003"}
{"index":{"_id":"mock-004"}}
{"timestamp":"2026-06-13T04:03:00Z","service":"catalog","environment":"dev","level":"WARN","message":"Product cache miss rate elevated","traceId":"trace-1004","requestId":"req-1004","statusCode":200,"host":"catalog-1","endpoint":"/catalog/items","method":"GET","durationMs":280,"tags":["catalog","cache"],"rawSource":"mock-catalog.log","ingestedAt":"2026-06-13T04:03:05Z","userId":"user-004"}
{"index":{"_id":"mock-005"}}
{"timestamp":"2026-06-13T04:04:00Z","service":"orders","environment":"dev","level":"ERROR","message":"Payment authorization failed after downstream 502","traceId":"trace-1002","requestId":"req-1005","statusCode":502,"host":"orders-1","endpoint":"/orders","method":"POST","durationMs":1900,"exceptionType":"DownstreamServiceException","tags":["orders","payments"],"rawSource":"mock-orders.log","ingestedAt":"2026-06-13T04:04:05Z","userId":"user-002"}
NDJSON

OPENSEARCH_URL="${OPENSEARCH_URL}" INDEX_NAME="${INDEX_NAME}" \
  sh /scripts/seed-mock-logs.sh

echo "OpenSearch index initialization complete"
