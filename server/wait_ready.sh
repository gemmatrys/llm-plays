#!/usr/bin/env bash
# Wait until the vLLM server is ready (or crashed), then show the tail.
for i in $(seq 1 100); do
  if docker logs vllm 2>&1 | grep -qE "Application startup complete|Traceback"; then
    break
  fi
  sleep 15
done
echo "=== status ==="
docker ps --filter name=vllm --format "table {{.Names}}\t{{.Status}}"
echo "=== log tail ==="
docker logs vllm 2>&1 | tail -15
