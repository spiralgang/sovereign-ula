#!/bin/bash
#
# Sovereign ULA — Ubuntu 24.04 (Noble) rootfs bootstrap builder.
#
# Runs INSIDE a noble container (see Dockerfile). Produces /output/rootfs.tar.gz
# that, once extracted by the app's /support/common/extractFilesystem.sh, yields a
# complete chroot whose /support tree matches exactly what tech.ula expects:
#   /support/common/extractFilesystem.sh
#   /support/common/compressFilesystem.sh
#   /support/execInProot.sh
#   /support/startSSHServer.sh  /support/startVNCServer.sh  /support/startXSDLServer.sh
#   /support/busybox  /support/libdisableselinux.so
#   /support/sovereign-motd.sh  /support/termuxvoid-shim.sh
#
# The support layer is UNIVERSAL (aarch64 Linux + Alpine combined env framework) —
# it is identical for every deployed distro. Only the distro rootfs differs.
#
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# --- base networking for the chroot ---
# NOTE: inside `docker build`, /etc/hosts and /etc/resolv.conf are read-only
# bind mounts managed by Docker — writing them fails the build. Docker's own
# copies already provide working DNS during the build. Write our runtime
# versions to staging paths; the app's proot environment uses these, and the
# bind-mounted originals are excluded from the packaged rootfs anyway.
echo "127.0.0.1 localhost" > /etc/hosts.sovereign || true
{ echo "nameserver 8.8.8.8"; echo "nameserver 1.1.1.1"; } > /etc/resolv.conf.sovereign || true
# Best-effort for real (non-docker) chroot bootstraps where these ARE writable:
echo "127.0.0.1 localhost" > /etc/hosts 2>/dev/null || true
{ echo "nameserver 8.8.8.8"; echo "nameserver 1.1.1.1"; } > /etc/resolv.conf 2>/dev/null || true

# --- modern sources: Ubuntu 24.04 (Noble), deb822 format ---
cat > /etc/apt/sources.list.d/ubuntu.sources <<'EOF'
Types: deb
URIs: http://archive.ubuntu.com/ubuntu/
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://security.ubuntu.com/ubuntu/
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
: > /etc/apt/sources.list

# --- profile drop-in (unset selinux shim, sane PATH) ---
cat > /etc/profile.d/userland.sh <<'EOF'
#!/bin/sh
unset LD_PRELOAD
unset LD_LIBRARY_PATH
export LIBGL_ALWAYS_SOFTWARE=1
EOF
chmod +x /etc/profile.d/userland.sh

apt-get update

# --- core packages UserLAnd needs ---
apt-get install -y --no-install-recommends \
    sudo dropbear libgl1 libglx-mesa0 tightvncserver xterm xfonts-base \
    twm expect wget curl

# --- modern "better than 8-years-ago" command / agent stack (pre-seeded) ---
apt-get install -y --no-install-recommends \
    git gh python3 python3-pip python3-venv nodejs npm ca-certificates gnupg \
    lsb-release software-properties-common cmake make gcc g++ pkg-config \
    unzip zip sqlite3 openssh-client

# Google Cloud SDK (gcloud)
if [ ! -f /usr/bin/gcloud ]; then
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list
  apt-get update
  apt-get install -y --no-install-recommends google-cloud-cli
fi

# Android packaging tooling (aapt2, apktool)
apt-get install -y --no-install-recommends aapt || true
if [ ! -x /usr/local/bin/apktool ]; then
  curl -fsSL https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar \
    -o /usr/local/bin/apktool.jar
  printf '#!/bin/sh\nexec java -jar /usr/local/bin/apktool.jar "$@"\n' > /usr/local/bin/apktool
  chmod +x /usr/local/bin/apktool
fi

# NVIDIA client libs (so nvidia-smi / CUDA apps resolve inside the chroot)
apt-get install -y --no-install-recommends nvidia-utils-535 libcuda1-535 libnvidia-ml1 \
  || echo "nvidia libs optional; skipped if unavailable in noble"

apt-get install -y --no-install-recommends pulseaudio

# --- glibc / termuxvoid translation layer (universal support add-on) ---
install -Dm755 /input/termuxvoid-shim.sh /support/termuxvoid-shim.sh
/support/termuxvoid-shim.sh install

# --- ship MOTD + support scripts into the rootfs /support tree ---
install -Dm755 /input/sovereign-motd.sh /support/sovereign-motd.sh

# --- device-anchored SSH: a resilient dropbear instance bound to the DEVICE
#     IMEI so the env can ALWAYS be reached even if the user-facing dropbear
#     config (startSSHServer.sh) gets corrupted. Host keys live in /support and
#     the session is cryptographically tied to the physical phone, guaranteeing
#     no lockout / no disallow. ---
install -Dm755 /input/support/ssh-anchor.sh /support/ssh-anchor.sh
/support/ssh-anchor.sh install || true

# --- install the universal support layer expected by tech.ula ---
install -Dm755 /input/support/common/extractFilesystem.sh /support/common/extractFilesystem.sh
install -Dm755 /input/support/common/compressFilesystem.sh /support/common/compressFilesystem.sh
install -Dm755 /input/support/execInProot.sh           /support/execInProot.sh
install -Dm755 /input/support/startSSHServer.sh        /support/startSSHServer.sh
# Preserve the ORIGINAL (source-of-truth) dropbear config as a fallback reference.
install -Dm755 /input/support/original/startSSHServer.sh /support/original/startSSHServer.sh
install -Dm755 /input/support/startVNCServer.sh        /support/startVNCServer.sh
install -Dm755 /input/support/startVNCServerStep2.sh   /support/startVNCServerStep2.sh
install -Dm755 /input/support/startXSDLServer.sh       /support/startXSDLServer.sh
install -Dm755 /input/support/addNonRootUser.sh        /support/addNonRootUser.sh
install -Dm644 /input/support/ld.so.preload            /support/ld.so.preload
install -Dm644 /input/support/userland_profile.sh      /support/userland_profile.sh

# --- clean apt caches so the tarball stays small ---
apt-get clean
rm -rf /var/lib/apt/lists/*

# --- tar the rootfs (exclude virtual fs + build artifacts) ---
tar -czvf /output/rootfs.tar.gz \
    --exclude sys --exclude dev --exclude proc \
    --exclude mnt --exclude etc/mtab \
    --exclude output --exclude input --exclude .dockerenv \
    /

# --- static busybox + selinux-disable shim for early extraction ---
apt-get update
apt-get -y install busybox-static build-essential
cp /bin/busybox /output/busybox
gcc -shared -fpic /input/disableselinux.c -o /output/libdisableselinux.so

echo "rootfs build complete: $(du -h /output/rootfs.tar.gz | cut -f1)"
