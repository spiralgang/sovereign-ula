#!/bin/bash
# Build the Ubuntu 24.04 (Noble) rootfs for Sovereign ULA.
# Multi-arch via docker buildx + QEMU. Produces release/<arch>-rootfs.tar.gz
# plus release/<arch>-assets.tar.gz (busybox + selinux shim) — matching the
# UserLAnd-Assets release layout the app already consumes.
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

# Package the universal support assets (busybox + selinux shim) the way the
# app expects: <arch>-assets.txt + <arch>-assets.tar.gz
mkdir -p release/assets
cp output/busybox release/assets/busybox
cp output/libdisableselinux.so release/assets/libdisableselinux.so
cp -r input/support release/assets/support
tar -czvf "release/${ARCH}-assets.tar.gz" -C release/assets .
: > "release/${ARCH}-assets.txt"
for f in $(ls release/assets/); do
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
