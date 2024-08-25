ARG NGINX_IMAGE=nginx:1.27.1-alpine3.20-slim
ARG NODE_IMAGE=node:lts-alpine3.20

## Build stage
FROM $NODE_IMAGE as build-stage

WORKDIR /app

## Install Node packages
COPY ./package*.json ./
RUN yarn install

## Version information
ARG BUILD_NUMBER
ARG BUILD_BRANCH
ARG BUILD_COMMIT
ENV BUILD_NUMBER="$BUILD_NUMBER" \
    BUILD_BRANCH="$BUILD_BRANCH" \
    BUILD_COMMIT="$BUILD_COMMIT"

# Build the app
COPY ./ .
RUN yarn run update-config /app/build.json
RUN yarn docs:build

## Production stage
FROM $NGINX_IMAGE as production-stage

COPY --from=build-stage /app/docs/.vuepress/dist /usr/share/nginx/html
COPY --from=build-stage /app/build.json /usr/share/nginx/html
COPY --from=build-stage /app/sbom.md /usr/share/nginx/html
COPY --from=build-stage /app/LICENSE.md /usr/share/nginx/html/license.md
COPY ./nginx/default.conf /etc/nginx/conf.d/

ARG PORT=5006
ENV PORT=$PORT
EXPOSE $PORT

## Runs healthcheck on the application root
## checks every `interval` seconds, fails if `timeout`,
## unhealthy status is reached if `retries` number of consecutive failures,
## but failures does not count within `start-period` seconds of start.
HEALTHCHECK --start-period=10s --timeout=2s --interval=10s --retries=2 CMD \
    wget -q -T 1 -O - "http://localhost:$PORT/" \
    > /dev/null || exit 1
