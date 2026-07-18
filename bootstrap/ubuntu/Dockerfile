# Sovereign ULA — Ubuntu 24.04 (Noble) rootfs build image.
#
# Runs input/main.sh INSIDE a noble container to produce a complete,
# latest-rolling chroot. The resulting /output/rootfs.tar.gz is extracted by
# the app at runtime. This is OUR build — no tech.ula / UserLAnd assets.
FROM ubuntu:noble

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg tar xz-utils gpg && rm -rf /var/lib/apt/lists/* && apt-get clean && apt-get autoclean && apt-get autoremove
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg tar xz-utils gpg && rm -rf /var/lib/apt/lists/* && apt-get clean

# Build deps (tar, gpg, curl, ca-certs) + qemu for the cross-arch runtime shim
# the app's proot needs inside the chroot.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg tar xz-utils gpg \
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg tar xz-utils gpg && rm -rf /var/lib/apt/lists/* && apt-get clean

# Copy our bootstrap input tree.
COPY input/ /input/

# Run the Noble bootstrap (installs packages, writes /support, etc).
RUN /input/main.sh

# Produce the rootfs tarball. Exclude pseudo-filesystems, the build input,
# and the output dir itself. Numeric owner so it extracts cleanly in proot.
RUN mkdir -p /output \
    && cd / \
    && tar --numeric-owner \
        --exclude=/proc --exclude=/sys --exclude=/dev \
        --exclude=/input --exclude=/output \
        --exclude=/var/lib/apt/lists/* \
        -czf /output/rootfs.tar.gz .

# The outermost target is `rootfs` (see docker-bake.hcl / build.sh).
