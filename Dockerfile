# Global ARG, available to all stages (if renewed)
ARG WORKDIR="/app"
FROM python:3.11-alpine AS builder

# Renew (https://stackoverflow.com/a/53682110):
ARG WORKDIR

# Don't buffer `stdout`:
ENV PYTHONUNBUFFERED=1
# Don't create `.pyc` files:
ENV PYTHONDONTWRITEBYTECODE=1
# https://github.com/rust-lang/cargo/issues/2808
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true

# For building CFFI / Crypgotraphy (needed on ARM builds):
RUN apk add gcc make musl-dev libffi-dev rust cargo git openssl-dev

RUN pip install poetry
RUN poetry config virtualenvs.in-project true

WORKDIR ${WORKDIR}

COPY --chown=1000:1000 pyproject.toml .
RUN poetry install --only main
COPY --chown=1000:1000 . .
# END Builder

FROM python:3.11-alpine

ARG WORKDIR
WORKDIR ${WORKDIR}

# For FlaskOIDC library
RUN mkdir /app/instance && chown 1000:1000 /app/instance

RUN mkdir /data
RUN chown 1000:1000 /data

RUN adduser app -DHh ${WORKDIR} -u 1000
USER 1000

COPY --chown=app:app --from=builder ${WORKDIR} .

# General variables
ENV TZ="UTC"
ENV COLOR="blue-grey"
ENV HS_SERVER=http://localhost/
ENV KEY=""
ENV DATA_DIRECTORY=/data
# ENV SCRIPT_NAME=/
ENV DOMAIN_NAME=http://localhost
ENV AUTH_TYPE=""
ENV LOG_LEVEL="Info"

# BasicAuth variables
ENV BASIC_AUTH_USER=""
ENV BASIC_AUTH_PASS=""

# Flask OIDC Variables
ENV OIDC_AUTH_URL=https://localhost
ENV OIDC_CLIENT_ID=Headscale-WebUI
ENV OIDC_CLIENT_SECRET=secret

# Jenkins build args
ARG GIT_COMMIT_ARG=""
ARG GIT_BRANCH_ARG=""
ARG APP_VERSION_ARG=""
ARG BUILD_DATE_ARG=""
ARG HS_VERSION_ARG=""

# About section on the Settings page
ENV GIT_COMMIT=$GIT_COMMIT_ARG
ENV GIT_BRANCH=$GIT_BRANCH_ARG
ENV APP_VERSION=$APP_VERSION_ARG
ENV BUILD_DATE=$BUILD_DATE_ARG
ENV HS_VERSION=$HS_VERSION_ARG

VOLUME /etc/headscale
VOLUME /data

EXPOSE 5000/tcp
ENTRYPOINT ["/app/entrypoint.sh"]

# Temporarily reduce to 1 workerd
CMD gunicorn -w 1 -b 0.0.0.0:5000 server:app
