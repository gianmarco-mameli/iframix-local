FROM --platform=$BUILDPLATFORM python:3.14-slim AS base

WORKDIR /home/app

COPY --exclude=docker-entrypoint.py . .

RUN chmod +x /home/app/scripts/apply-local-index-html-patch.py


RUN pip install --no-cache-dir --prefix /home/app/.local -r requirements.txt

WORKDIR /

COPY docker-entrypoint.py /docker-entrypoint.py
RUN chmod +x /docker-entrypoint.py

WORKDIR /srv

RUN mkdir -p photos photos_with_ai photos_temp thumbnails logs

FROM --platform=$BUILDPLATFORM buildpack-deps:noble-curl AS chisel

ARG BUILDPLATFORM
ARG CHISEL_VERSION=1.4.1
ARG UBUNTU_VERSION=26.04

SHELL ["/bin/bash", "-o", "pipefail", "-c", "-l"]

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install --no-install-recommends -qy \
        file=1:5.45-3build1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

RUN case "${BUILDPLATFORM}" in \
        linux/amd64)              ARCH=amd64    ;; \
        linux/arm64 | linux/arm64/v8) ARCH=arm64 ;; \
        linux/arm/v7)             ARCH=armhf    ;; \
        linux/arm/v6)             ARCH=armel    ;; \
        linux/ppc64le)            ARCH=ppc64el  ;; \
        linux/s390x)              ARCH=s390x    ;; \
        linux/386)                ARCH=386      ;; \
        *) echo "Unsupported BUILDPLATFORM: ${BUILDPLATFORM}" >&2; exit 1 ;; \
    esac \
    && curl -fSL --output chisel_v${CHISEL_VERSION}_linux_${ARCH}.tar.gz https://github.com/canonical/chisel/releases/download/v${CHISEL_VERSION}/chisel_v${CHISEL_VERSION}_linux_${ARCH}.tar.gz \
    && curl -fSL --output chisel_v${CHISEL_VERSION}_linux_${ARCH}.tar.gz.sha384 https://github.com/canonical/chisel/releases/download/v${CHISEL_VERSION}/chisel_v${CHISEL_VERSION}_linux_${ARCH}.tar.gz.sha384 \
    && sha384sum -c chisel_v${CHISEL_VERSION}_linux_${ARCH}.tar.gz.sha384 \
    && tar -xzf chisel_v${CHISEL_VERSION}_linux_${ARCH}.tar.gz -C /usr/bin/ chisel \
    && curl -fSL --output /usr/bin/chisel-wrapper https://raw.githubusercontent.com/canonical/rocks-toolbox/v1.2.0/chisel-wrapper \
    && chmod 755 /usr/bin/chisel-wrapper

COPY --from=base /home/app /rootfs/home/app
COPY --from=base /srv /rootfs/srv
COPY --from=base /docker-entrypoint.py /rootfs/docker-entrypoint.py

RUN groupadd \
        --gid=1654 \
        app \
    && useradd -l \
        --uid=1654 \
        --gid=1654 \
        --shell /bin/false \
        app \
    && chown -R 1654:1654 /rootfs/home/app /rootfs/srv /rootfs/docker-entrypoint.py \
    && mkdir -p "/rootfs/etc" \
    && rootOrAppRegex='^\(root\|app\):' \
    && grep "${rootOrAppRegex}" /etc/passwd > "/rootfs/etc/passwd" \
    && grep "${rootOrAppRegex}" /etc/group > "/rootfs/etc/group"

RUN chisel cut --release ubuntu-${UBUNTU_VERSION} --root rootfs \
        openssl_bins \
        python3_standard \
        ca-certificates_data

FROM scratch

COPY --from=chisel /rootfs /

WORKDIR /home/app

ENV PATH="/home/app/deps/bin:$PATH"

ENV BROKER_HOST=mosquitto
ENV BROKER_PORT=1883
ENV BROKER_WS_PORT=9001

ENV CERT_FILE=/home/app/server.crt
# trunk-ignore(trivy/DS-0031)
ENV KEY_FILE=/home/app/server.key

ENV AUTO_FETCH_ASSETS=1
ENV ASSET_FETCH_VERSION=docker

ENV API_EXTRA_ARGS=""

ENV IFRAMIX_BASE_PATH=/srv

EXPOSE 443

# HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
#     CMD /home/app/.venv/bin/python -c "import socket; sock = socket.create_connection(('127.0.0.1', 443), 5); sock.close()" || exit 1

VOLUME ["/srv"]

USER 1654

ENTRYPOINT ["python3"]
CMD ["/docker-entrypoint.py"]