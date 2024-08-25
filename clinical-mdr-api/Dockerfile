ARG PYTHON_IMAGE=python:3.11.9-slim
ARG TARGET=dev

## In shared stage we create the environment and settings that are shared between prod and dev
FROM $PYTHON_IMAGE as common-stage

## Create non-root user (arg has to be exported to env for later build stages)
ARG UID=1000
ARG USER=appuser
ENV USER="$USER"
RUN useradd --home-dir /home/$USER --user-group --create-home --uid $UID $USER

## Commands below run relative to this working directory
ARG WORKDIR=/app
WORKDIR $WORKDIR

## Copy Pipfiles into the working direcotyr
COPY ./Pipfile* ./


## In build stage we remove test files and pre-compile the Python code to be copied into the prod image
FROM $PYTHON_IMAGE as build-stage

WORKDIR /wd

COPY ./ ./

## Delete tests and byte-code compile application
RUN echo "Building build-stage" 1>&2 ; \
    rm -r clinical_mdr_api/tests \
    && python -m compileall -f -j 0 .


# In the prod image, we install packages and copy the compiled Python code
FROM common-stage as prod-stage

## Create virtual environment according to Pipfile.lock into user's home as root
RUN echo "Building prod-stage" 1>&2 ; \
    HOME=/home/$USER pipenv sync \
    # clean-up
    && rm -rf ~/.cache

## Copy the rest of the application owned by root
COPY --from=build-stage /wd ./

# build SBOM
RUN HOME=/home/$USER pipenv run build-sbom > sbom.md


## In dev stage we install dev packages too, and copy all Python code (non-compiled), including tests
FROM common-stage as dev-stage

## Install required system packages
RUN echo "Building dev-stage" 1>&2 ; \
    apt-get update \
    && apt-get -y install \
        gcc \
        python3-dev \
        git \
        curl \
        python3-cffi \
        python3-brotli \
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
        gcc \
    && pip install --upgrade pip pipenv wheel \
    # clean-up
    && apt-get clean && rm -rf /var/lib/apt/lists && rm -rf ~/.cache

## Run as non-root user
USER $USER

## Create virtual environment according to Pipfile.lock as user
RUN pipenv sync --dev \
    # clean-up
    && rm -rf ~/.cache

## Copy the rest of the application owned by root
COPY ./ ./

FROM ${TARGET}-stage as final

## Preferred to configure Uvicorn using env vars with UVICORN_ prefix, default values from build arguments
ARG UVICORN_HOST="0.0.0.0"
ARG UVICORN_PORT="5003"
ARG UVICORN_ROOT_PATH="/api"
ENV UVICORN_PORT="$UVICORN_PORT" \
    UVICORN_HOST="$UVICORN_HOST" \
    UVICORN_ROOT_PATH="$UVICORN_ROOT_PATH"

## Version information
ARG BUILD_NUMBER
ARG BUILD_BRANCH
ARG BUILD_COMMIT
ENV BUILD_NUMBER="$BUILD_NUMBER" \
    BUILD_BRANCH="$BUILD_BRANCH" \
    BUILD_COMMIT="$BUILD_COMMIT"

## Open up a port to listen on
EXPOSE $UVICORN_PORT

## Run as non-root user
USER $USER

## Run healthcheck on the API endpoint:
## checks every `interval` seconds, fails if `timeout`,
## unhealthy status is reached if `retries` number of consecutive failures,
## but failures does not count within `start-period` seconds of start.
HEALTHCHECK --start-period=60s --timeout=3s --interval=10s --retries=2 CMD \
    curl --fail --silent --show-error --max-time 2 \
    "http://localhost:$UVICORN_PORT/system/healthcheck" \
    > /dev/null || exit 1

## Preferred to configure Uvicorn using env vars with UVICORN_ prefix instead of cmd-line arguments
CMD pipenv run uvicorn clinical_mdr_api.main:app
