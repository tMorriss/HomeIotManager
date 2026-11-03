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

if [ -z "${HOME:-}" ]; then
    echo "Error: HOME is not set for the deployment user." >&2
    exit 1
fi
PODMAN_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export HOME XDG_RUNTIME_DIR="$PODMAN_RUNTIME_DIR"

# 3. BUILD_TAG の生成
BUILD_TAG="$(date +%Y%m%d%H%M%S)-${GIT_COMMIT:-latest}"
export BUILD_TAG
echo "Building tag: ${BUILD_TAG}"

# 4. ベースイメージの pull & podman build
echo "Building podman image localhost/homeiot:${BUILD_TAG}..."
podman pull python:3.12-slim || true
podman build -t "localhost/homeiot:${BUILD_TAG}" -f build/Dockerfile .

# 5. 既存 Quadlet サービスと旧 podman play kube Pod を停止・削除
echo "Stopping and removing existing homeiot-pod if present..."
systemctl --user stop homeiot-web.service homeiot-worker.service homeiot-pod.service 2>/dev/null || true
podman pod rm -f homeiot-pod 2>/dev/null || true

# 6. 設定値を Podman Secrets に登録
create_or_update_secret() {
    local name="$1"
    local value="$2"
    echo "Updating Podman secret: $name"
    if podman secret exists "$name"; then
        podman secret rm "$name"
    fi
    printf '%s' "$value" | podman secret create "$name" -
}

create_or_update_secret homeiot_db_host "$DB_HOST"
create_or_update_secret homeiot_db_port "$DB_PORT"
create_or_update_secret homeiot_db_user "$DB_USER"
create_or_update_secret homeiot_db_pass "$DB_PASS"
create_or_update_secret homeiot_db_name "$DB_NAME"
create_or_update_secret homeiot_target_phone_ips "$TARGET_PHONE_IPS"
create_or_update_secret homeiot_hue_bridge_ip "$HUE_BRIDGE_IP"
create_or_update_secret homeiot_hue_api_user "$HUE_API_USER"
create_or_update_secret homeiot_hue_on_scene_id "$HUE_ON_SCENE_ID"
create_or_update_secret homeiot_ifttt_webhook_key "$IFTTT_WEBHOOK_KEY"
create_or_update_secret homeiot_switchbot_webhook_token "$SWITCHBOT_WEBHOOK_TOKEN"

# 7. Quadlet ユニットを配置
QUADLET_DIR="$HOME/.config/containers/systemd/homeiot"
echo "Deploying Quadlet unit files to $QUADLET_DIR..."
mkdir -p "$QUADLET_DIR"
export BUILD_TAG
envsubst '$BUILD_TAG' < build/quadlet/homeiot.pod.template > "$QUADLET_DIR/homeiot.pod"
envsubst '$BUILD_TAG' < build/quadlet/homeiot-web.container.template > "$QUADLET_DIR/homeiot-web.container"
envsubst '$BUILD_TAG' < build/quadlet/homeiot-worker.container.template > "$QUADLET_DIR/homeiot-worker.container"

# 8. Quadlet サービスを再読み込み・起動
echo "Reloading systemd user daemon and restarting Quadlet services..."
systemctl --user daemon-reload
systemctl --user start homeiot-pod.service homeiot-web.service homeiot-worker.service
systemctl --user --no-pager --full status homeiot-pod.service

# 9. 古い HomeIotManager イメージを削除
echo "Cleaning up old images..."
podman images --filter "reference=localhost/homeiot" --format '{{.Tag}}' | \
    while IFS= read -r old_tag; do
        if [ -n "$old_tag" ] && [ "$old_tag" != "$BUILD_TAG" ]; then
            podman rmi "localhost/homeiot:$old_tag" || true
        fi
    done

echo "=== Deployment Completed Successfully ==="
