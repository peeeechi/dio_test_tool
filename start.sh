#!/bin/bash -eu

# X11の許可設定
xhost +local:docker

docker compose up --build

# コンテナの停止
docker compose down

# X11の許可を戻す
xhost -local:docker