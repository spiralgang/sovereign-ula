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
  echo "$f $(date +%s -r "release/assets/$f") $(md5sum "release/assets/$f" | awk '{print $1}')" >> "release/${ARCH}-assets.txt"
done
mv output/rootfs.tar.gz "release/${ARCH}-rootfs.tar.gz"
echo "Built: release/${ARCH}-rootfs.tar.gz + release/${ARCH}-assets.tar.gz"
