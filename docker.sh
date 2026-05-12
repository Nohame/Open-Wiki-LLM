#!/usr/bin/env bash

set -e

SERVICE_NAME="openwikillm-api"

case "$1" in
  start)
    docker compose up -d
    ;;
  stop)
    docker compose down
    ;;
  restart)
    docker compose down
    docker compose up -d
    ;;
  ssh)
    docker compose exec "$SERVICE_NAME" bash
    ;;
  *)
    echo "Usage: ./docker.sh {start|stop|restart|ssh}"
    exit 1
    ;;
esac
