#!/bin/sh
set -eu

OPENSEARCH_URL="${OPENSEARCH_URL:-http://opensearch:9200}"
INDEX_NAME="${INDEX_NAME:-normalized-logs-v1}"
BULK_FILE="/tmp/mock-logs.ndjson"
BULK_RESPONSE="/tmp/mock-logs-response.json"

: >"${BULK_FILE}"

append_log() {
  id="$1"
  document="$2"

  printf '{"index":{"_id":"%s"}}\n' "${id}" >>"${BULK_FILE}"
  printf '%s\n' "${document}" >>"${BULK_FILE}"
}

echo "Generating deterministic OpenSearch mock logs"

# 120 successful requests across the main services.
i=1
while [ "${i}" -le 120 ]; do
  case $((i % 5)) in
    0) service="gateway"; endpoint="/api/search"; method="GET" ;;
    1) service="payment"; endpoint="/payments/charge"; method="POST" ;;
    2) service="orders"; endpoint="/orders"; method="POST" ;;
    3) service="catalog"; endpoint="/catalog/items"; method="GET" ;;
    *) service="auth"; endpoint="/auth/token"; method="POST" ;;
  esac

  minute=$(printf '%02d' $((i % 60)))
  second=$(printf '%02d' $(((i * 7) % 60)))
  duration=$((20 + (i * 13) % 430))

  append_log "mock-normal-${i}" \
    "{\"timestamp\":\"2026-06-21T08:${minute}:${second}Z\",\"service\":\"${service}\",\"environment\":\"prod\",\"level\":\"INFO\",\"message\":\"Request completed successfully\",\"traceId\":\"trace-normal-${i}\",\"requestId\":\"req-normal-${i}\",\"statusCode\":200,\"host\":\"${service}-$((i % 3 + 1))\",\"endpoint\":\"${endpoint}\",\"method\":\"${method}\",\"durationMs\":${duration},\"tags\":[\"mock\",\"success\"],\"rawSource\":\"mock-${service}.log\",\"ingestedAt\":\"2026-06-21T08:${minute}:${second}Z\",\"userId\":\"user-$((i % 25 + 1))\"}"

  i=$((i + 1))
done

# 60 failures covering database, downstream, cache, auth, and rate-limit scenarios.
i=1
while [ "${i}" -le 60 ]; do
  case $((i % 6)) in
    0) service="payment"; endpoint="/payments/charge"; status=504; exception="TimeoutException"; message="Database timeout while charging order"; tag="database" ;;
    1) service="orders"; endpoint="/orders"; status=500; exception="OrderProcessingException"; message="Order processing failed during persistence"; tag="database" ;;
    2) service="auth"; endpoint="/auth/token"; status=401; exception="AuthenticationException"; message="Authentication failed for invalid credentials"; tag="security" ;;
    3) service="gateway"; endpoint="/api/search"; status=429; exception="RateLimitException"; message="Request rejected by rate limiter"; tag="rate-limit" ;;
    4) service="catalog"; endpoint="/catalog/items"; status=503; exception="CacheBackendException"; message="Catalog cache backend unavailable"; tag="cache" ;;
    *) service="catalog"; endpoint="/catalog/items"; status=500; exception="RedisConnectionException"; message="Redis connection refused while loading catalog"; tag="redis" ;;
  esac

  minute=$(printf '%02d' $((i % 60)))
  second=$(printf '%02d' $(((i * 11) % 60)))
  duration=$((900 + (i * 173) % 5200))

  append_log "mock-error-${i}" \
    "{\"timestamp\":\"2026-06-21T09:${minute}:${second}Z\",\"service\":\"${service}\",\"environment\":\"prod\",\"level\":\"ERROR\",\"message\":\"${message}\",\"traceId\":\"trace-error-${i}\",\"requestId\":\"req-error-${i}\",\"statusCode\":${status},\"host\":\"${service}-$((i % 3 + 1))\",\"endpoint\":\"${endpoint}\",\"method\":\"POST\",\"durationMs\":${duration},\"exceptionType\":\"${exception}\",\"tags\":[\"mock\",\"error\",\"${tag}\"],\"rawSource\":\"mock-${service}.log\",\"ingestedAt\":\"2026-06-21T09:${minute}:${second}Z\",\"userId\":\"user-$((i % 25 + 1))\"}"

  i=$((i + 1))
done

# 40 slow or degraded requests for latency dashboards.
i=1
while [ "${i}" -le 40 ]; do
  if [ $((i % 2)) -eq 0 ]; then
    service="catalog"
    endpoint="/catalog/search"
    message="Catalog search latency above threshold"
  else
    service="payment"
    endpoint="/payments/status"
    message="Payment status lookup latency above threshold"
  fi

  minute=$(printf '%02d' $((i % 60)))
  second=$(printf '%02d' $(((i * 17) % 60)))
  duration=$((1200 + (i * 97) % 2800))

  append_log "mock-warning-${i}" \
    "{\"timestamp\":\"2026-06-21T10:${minute}:${second}Z\",\"service\":\"${service}\",\"environment\":\"prod\",\"level\":\"WARN\",\"message\":\"${message}\",\"traceId\":\"trace-warning-${i}\",\"requestId\":\"req-warning-${i}\",\"statusCode\":200,\"host\":\"${service}-$((i % 3 + 1))\",\"endpoint\":\"${endpoint}\",\"method\":\"GET\",\"durationMs\":${duration},\"tags\":[\"mock\",\"latency\"],\"rawSource\":\"mock-${service}.log\",\"ingestedAt\":\"2026-06-21T10:${minute}:${second}Z\",\"userId\":\"user-$((i % 25 + 1))\"}"

  i=$((i + 1))
done

# 20 distributed traces with four related service events each (80 documents).
trace=1
while [ "${trace}" -le 20 ]; do
  minute=$(printf '%02d' $((trace % 60)))
  trace_id="trace-distributed-${trace}"
  user_id="user-$((trace % 25 + 1))"

  if [ $((trace % 3)) -eq 0 ]; then
    payment_status=504
    payment_level="ERROR"
    payment_message="Payment database timeout in distributed request"
    payment_exception=",\"exceptionType\":\"TimeoutException\""
    order_status=502
    order_level="ERROR"
    order_message="Order failed because payment service timed out"
  else
    payment_status=200
    payment_level="INFO"
    payment_message="Payment completed for distributed request"
    payment_exception=""
    order_status=201
    order_level="INFO"
    order_message="Order completed successfully"
  fi

  append_log "mock-trace-${trace}-gateway" \
    "{\"timestamp\":\"2026-06-21T11:${minute}:01Z\",\"service\":\"gateway\",\"environment\":\"prod\",\"level\":\"INFO\",\"message\":\"Incoming checkout request\",\"traceId\":\"${trace_id}\",\"requestId\":\"req-trace-${trace}-gateway\",\"statusCode\":200,\"host\":\"gateway-1\",\"endpoint\":\"/checkout\",\"method\":\"POST\",\"durationMs\":25,\"tags\":[\"mock\",\"distributed-trace\"],\"rawSource\":\"mock-gateway.log\",\"ingestedAt\":\"2026-06-21T11:${minute}:01Z\",\"userId\":\"${user_id}\"}"

  append_log "mock-trace-${trace}-catalog" \
    "{\"timestamp\":\"2026-06-21T11:${minute}:02Z\",\"service\":\"catalog\",\"environment\":\"prod\",\"level\":\"INFO\",\"message\":\"Inventory validated for checkout\",\"traceId\":\"${trace_id}\",\"requestId\":\"req-trace-${trace}-catalog\",\"statusCode\":200,\"host\":\"catalog-1\",\"endpoint\":\"/catalog/inventory\",\"method\":\"GET\",\"durationMs\":140,\"tags\":[\"mock\",\"distributed-trace\"],\"rawSource\":\"mock-catalog.log\",\"ingestedAt\":\"2026-06-21T11:${minute}:02Z\",\"userId\":\"${user_id}\"}"

  append_log "mock-trace-${trace}-payment" \
    "{\"timestamp\":\"2026-06-21T11:${minute}:03Z\",\"service\":\"payment\",\"environment\":\"prod\",\"level\":\"${payment_level}\",\"message\":\"${payment_message}\",\"traceId\":\"${trace_id}\",\"requestId\":\"req-trace-${trace}-payment\",\"statusCode\":${payment_status},\"host\":\"payment-1\",\"endpoint\":\"/payments/charge\",\"method\":\"POST\",\"durationMs\":$((300 + trace * 210))${payment_exception},\"tags\":[\"mock\",\"distributed-trace\",\"payment\"],\"rawSource\":\"mock-payment.log\",\"ingestedAt\":\"2026-06-21T11:${minute}:03Z\",\"userId\":\"${user_id}\"}"

  append_log "mock-trace-${trace}-orders" \
    "{\"timestamp\":\"2026-06-21T11:${minute}:04Z\",\"service\":\"orders\",\"environment\":\"prod\",\"level\":\"${order_level}\",\"message\":\"${order_message}\",\"traceId\":\"${trace_id}\",\"requestId\":\"req-trace-${trace}-orders\",\"statusCode\":${order_status},\"host\":\"orders-1\",\"endpoint\":\"/orders\",\"method\":\"POST\",\"durationMs\":$((500 + trace * 220)),\"tags\":[\"mock\",\"distributed-trace\",\"orders\"],\"rawSource\":\"mock-orders.log\",\"ingestedAt\":\"2026-06-21T11:${minute}:04Z\",\"userId\":\"${user_id}\"}"

  trace=$((trace + 1))
done

echo "Loading 300 additional mock logs into ${INDEX_NAME}"
curl -fsS -X POST "${OPENSEARCH_URL}/${INDEX_NAME}/_bulk?refresh=true" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary "@${BULK_FILE}" >"${BULK_RESPONSE}"

if ! grep -q '"errors":false' "${BULK_RESPONSE}"; then
  echo "OpenSearch bulk load reported errors"
  cat "${BULK_RESPONSE}"
  exit 1
fi

echo "Additional OpenSearch mock data loaded successfully"
