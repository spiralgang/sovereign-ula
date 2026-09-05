# Sovereign ULA — Ubuntu 24.04 (Noble) rootfs build image.
FROM ubuntu:noble AS build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    tar \
    xz-utils \
    gpg \
    busybox-static \
    gcc \
    libc6-dev \
    && apt-get clean

# FSM layout: the universal support layer lives in bootstrap/core/ (agnostic
# core) while distro dirs only carry distro config. Build context is bootstrap/.
COPY ubuntu/input/ /input/
COPY core/ /core/

RUN gcc -shared -fPIC -o /libdisableselinux.so /input/disableselinux.c

# run main.sh (bootstrap)
RUN bash /input/main.sh

# ensure busybox at predictable path
RUN cp /usr/bin/busybox /busybox

# package explicit directories to avoid layer residue leaks; fallback to . if list empty
RUN mkdir -p /output \
    && cd / \
    && rm -rf /var/lib/apt/lists/* \
    && tar --numeric-owner \
        -czf /output/rootfs.tar.gz \
        --exclude=/proc --exclude=/sys --exclude=/dev \
        --exclude=/input --exclude=/output \
        --exclude=/busybox --exclude=/libdisableselinux.so \
        /bin /boot /etc /lib /lib64 /opt /root /sbin /srv /usr /var || \
        tar --numeric-owner -czf /output/rootfs.tar.gz .
FROM scratch AS rootfs
COPY --from=build /output/rootfs.tar.gz /rootfs.tar.gz
COPY --from=build /busybox /busybox
COPY --from=build /libdisableselinux.so /libdisableselinux.so
