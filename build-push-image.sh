#!/bin/bash
set -euo pipefail
# set -x
cd $(dirname $0)

# Path to your docker-compose.yaml file
COMPOSE_FILE="docker-compose-build.yaml"

# Build images
docker compose -f $COMPOSE_FILE build

# Extract image names using sed and awk
IMAGES=$(sed -n 's/^\s*image:\s*\(.*\)/\1/p' "$COMPOSE_FILE" | awk '{print $1}' | grep hudzy)

# Push each image
for IMAGE in $IMAGES; do
  echo "Pushing image: $IMAGE"
  docker push "$IMAGE"
done
