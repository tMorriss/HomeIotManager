#!/bin/bash
set -euo pipefail

echo "=== HomeIotManager Deployment Script ==="

# 1. [skip ci] コミットチェック
COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "")
if echo "${COMMIT_MSG}" | grep -q "\[skip ci\]"; then
    echo "Found [skip ci] in commit message. Skipping deployment."
    exit 0
fi

# 2. 必須環境変数のバリデーション
REQUIRED_VARS=(
    "DB_HOST"
    "DB_PORT"
    "DB_USER"
    "DB_PASS"
    "DB_NAME"
    "TARGET_PHONE_IPS"
    "HUE_BRIDGE_IP"
    "HUE_API_USER"
    "HUE_ON_SCENE_ID"
    "IFTTT_WEBHOOK_KEY"
    "SWITCHBOT_WEBHOOK_TOKEN"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "Error: Required environment variable $var is not set." >&2
        exit 1
    fi
done

# 3. BUILD_TAG の生成
BUILD_TAG="$(date +%Y%m%d%H%M%S)-${GIT_COMMIT:-latest}"
export BUILD_TAG
echo "Building tag: ${BUILD_TAG}"

# 4. ベースイメージの pull & podman build
echo "Building podman image homeiot:${BUILD_TAG}..."
podman pull python:3.12-slim || true
podman build -t "homeiot:${BUILD_TAG}" -f build/Dockerfile .

# 5. 既存 Pod の停止・削除
echo "Stopping and removing existing homeiot-pod if present..."
podman pod stop homeiot-pod 2>/dev/null || true
podman pod rm -f homeiot-pod 2>/dev/null || true

# 6. envsubst による pod.yaml の展開 & podman play kube で Pod 起動
RENDERED_POD_YAML=$(mktemp /tmp/pod-manifest.XXXXXX.yaml)
trap 'rm -f "${RENDERED_POD_YAML}"' EXIT

echo "Rendering pod.yaml with envsubst..."
envsubst < build/pod.yaml > "${RENDERED_POD_YAML}"

echo "Starting Pod with podman play kube..."
podman play kube "${RENDERED_POD_YAML}"

# 7. ヘルスチェック (8930/healthz)
echo "Running health check on http://127.0.0.1:8930/healthz..."
MAX_RETRIES=30
RETRY_INTERVAL=2
HEALTHCHECK_PASSED=0

for i in $(seq 1 ${MAX_RETRIES}); do
    if curl -s -f http://127.0.0.1:8930/healthz > /dev/null; then
        echo "Health check passed!"
        HEALTHCHECK_PASSED=1
        break
    fi
    echo "Waiting for web server to be ready... (${i}/${MAX_RETRIES})"
    sleep ${RETRY_INTERVAL}
done

if [ ${HEALTHCHECK_PASSED} -ne 1 ]; then
    echo "Error: Health check failed after ${MAX_RETRIES} attempts." >&2
    podman pod logs homeiot-pod 2>/dev/null || true
    exit 1
fi

# 8. クリーンアップ
echo "Cleaning up old images..."
podman image prune -f || true

echo "=== Deployment Completed Successfully ==="
