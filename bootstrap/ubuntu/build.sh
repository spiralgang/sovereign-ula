#!/bin/bash
set -euo pipefail
ARCH="${1:-arm64}"
PLATFORM="linux/arm64"
QEMU="qemu-aarch64-static"
case "$ARCH" in
  arm64) PLATFORM="linux/arm64"; QEMU="qemu-aarch64-static" ;;
  arm)   PLATFORM="linux/arm/v7"; QEMU="qemu-arm-static" ;;
  x86_64) PLATFORM="linux/amd64"; QEMU="qemu-x86_64-static" ;;
  x86)   PLATFORM="linux/386"; QEMU="qemu-i386-static" ;;
  *) echo "unknown arch $ARCH"; exit 1 ;;
esac

mkdir -p release output input
cp /usr/bin/$QEMU input/$QEMU 2>/dev/null || true

# --- Stage universal support layer from bootstrap/core/ into /input/ ---
# The FSM architecture requires agnostic scripts like termuxvoid-shim.sh to
# live only in bootstrap/core/ (universal). However, main.sh expects them at
# /input/ during Docker build. Copy them here before the build runs.
echo "Staging universal support from bootstrap/core/..."
cp ../core/termuxvoid-shim.sh input/termuxvoid-shim.sh 2>/dev/null || \
  { echo "WARNING: termuxvoid-shim.sh not found in bootstrap/core/" >&2; }

echo "Ensuring buildx builder exists..."
if ! docker buildx ls | grep -q "agent-builder"; then
  docker buildx create --use --name agent-builder || true
fi

echo "Building noble rootfs for $ARCH ($PLATFORM)..."
docker buildx build \
  --platform "$PLATFORM" \
  --build-arg IMAGE_ARCH="arm64v8" \
  --build-arg IMAGE_DISTRO="ubuntu" \
  --build-arg IMAGE_VERSION="noble" \
  --build-arg IMAGE_PLATFORM="$PLATFORM" \
  --build-arg QEMU_FILE="$QEMU" \
  --target rootfs \
  -o type=local,dest=output \
  -f Dockerfile .

# Verify artifacts exist
if [ ! -f output/rootfs.tar.gz ]; then
  echo "ERROR: output/rootfs.tar.gz missing" >&2
  ls -la output || true
  exit 2
fi
if [ ! -f output/busybox ] && [ ! -f output/busybox.static ] && [ ! -f /busybox ]; then
  echo "ERROR: busybox not found in output" >&2
  ls -la output || true
  exit 3
fi
if [ ! -f output/libdisableselinux.so ] && [ ! -f /libdisableselinux.so ]; then
  echo "ERROR: libdisableselinux.so not found in output" >&2
  ls -la output || true
  exit 4
fi

ROOTFS_SIZE=$(stat -c%s output/rootfs.tar.gz || true)
if [ -z "$ROOTFS_SIZE" ] || [ "$ROOTFS_SIZE" -lt 20000000 ]; then
  echo "ERROR: rootfs.tar.gz too small ($ROOTFS_SIZE bytes) — aborting" >&2
  exit 5
fi

mkdir -p release/assets
cp output/busybox release/assets/busybox 2>/dev/null || cp /busybox release/assets/busybox 2>/dev/null || true
cp output/libdisableselinux.so release/assets/libdisableselinux.so 2>/dev/null || cp /libdisableselinux.so release/assets/libdisableselinux.so 2>/dev/null || true
cp -r input/support release/assets 2>/dev/null || true
tar -czvf "release/${ARCH}-assets.tar.gz" -C release/assets .
: > "release/${ARCH}-assets.txt"
for f in $(ls release/assets/ 2>/dev/null); do
  echo "$f $(date +%s -r "release/assets/$f") $(md5sum "release/assets/$f" | awk '{print $1}')" >> "release/${ARCH}-assets.txt"
done
mv output/rootfs.tar.gz "release/${ARCH}-rootfs.tar.gz"
echo "Built: release/${ARCH}-rootfs.tar.gz + release/${ARCH}-assets.tar.gz"
