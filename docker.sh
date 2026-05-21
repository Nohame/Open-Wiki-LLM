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
  logs)
    case "$2" in
      api)   docker compose logs -f openwikillm-api ;;
      front) docker compose logs -f frontend ;;
      *)     docker compose logs -f ;;
    esac
    ;;
  *)
    echo "Usage: ./docker.sh {start|stop|restart|ssh|logs [api|front]}"
    exit 1
    ;;
esac
