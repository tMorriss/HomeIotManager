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
PODMAN_USER="${PODMAN_USER:-podman}"

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
sudo -u "${PODMAN_USER}" podman pull python:3.12-slim || true
sudo -u "${PODMAN_USER}" podman build -t "homeiot:${BUILD_TAG}" -f build/Dockerfile .

# 5. 既存 Pod の停止・削除
echo "Stopping and removing existing homeiot-pod if present..."
sudo -u "${PODMAN_USER}" podman pod stop homeiot-pod 2>/dev/null || true
sudo -u "${PODMAN_USER}" podman pod rm -f homeiot-pod 2>/dev/null || true

# 6. envsubst による pod.yaml の展開 & podman play kube で Pod 起動
echo "Starting Pod with podman play kube..."
envsubst < build/pod.yaml | sudo -u "${PODMAN_USER}" podman play kube -

# 7. クリーンアップ
echo "Cleaning up old images..."
sudo -u "${PODMAN_USER}" podman image prune -f || true

echo "=== Deployment Completed Successfully ==="
