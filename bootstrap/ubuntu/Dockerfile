# Sovereign ULA — Ubuntu 24.04 (Noble) rootfs build image.
#
# Runs input/main.sh INSIDE a noble container to produce a complete,
# latest-rolling chroot. The resulting rootfs.tar.gz is extracted by the app
# at runtime. This is OUR build — no tech.ula / UserLAnd assets.
#
# build.sh invokes this with `--target rootfs -o type=local,dest=output` and
# expects the final stage to contain exactly:
#   /rootfs.tar.gz          the packaged chroot
#   /busybox                static busybox for the app's support layer
#   /libdisableselinux.so   LD_PRELOAD shim built from input/disableselinux.c
FROM ubuntu:noble AS build

ENV DEBIAN_FRONTEND=noninteractive

# Build deps + busybox-static (shipped as an asset) + gcc for the shim.
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

# Copy our bootstrap input tree.
COPY input/ /input/

# Build the selinux-disable LD_PRELOAD shim.
RUN gcc -shared -fPIC -o /libdisableselinux.so /input/disableselinux.c

# Run the Noble bootstrap (installs packages, writes /support, etc).
# main.sh is not stored with the executable bit set; run via bash.
RUN bash /input/main.sh

# Stash busybox before packaging so it is not lost in the tar excludes.
RUN cp /usr/bin/busybox /busybox.static

# Produce the rootfs tarball. Exclude pseudo-filesystems, the build input,
# and the output dir itself. Numeric owner so it extracts cleanly in proot.
RUN mkdir -p /output \
    && cd / \
    && rm -rf /var/lib/apt/lists/* \
    && tar --numeric-owner \
        --exclude=./proc --exclude=./sys --exclude=./dev \
        --exclude=./input --exclude=./output \
        --exclude=./busybox.static --exclude=./libdisableselinux.so \
        -czf /output/rootfs.tar.gz .

# Final stage: exactly the artifacts build.sh expects, nothing else.
FROM scratch AS rootfs
COPY --from=build /output/rootfs.tar.gz /rootfs.tar.gz
COPY --from=build /busybox.static /busybox
COPY --from=build /libdisableselinux.so /libdisableselinux.so
