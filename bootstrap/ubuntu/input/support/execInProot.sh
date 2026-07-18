#!/bin/sh
# execInProot.sh — proot entrypoint invoked by tech.ula's BusyboxExecutor.
#
# BOTH designs are present (user requirement):
#   PRIMARY  = virtual-kernel design: proot -0 (virtualized root uid 0) with a
#              synthetic /sys/fs/selinux + /proc/self/attr that report "enforcing"
#              to in-chroot probes while the chroot's security view is virtualized.
#   SECONDARY = classic selinux-disabled shim: if the virtual-kernel path fails,
#              fall back to plain proot; /support/ld.so.preload ->
#              libdisableselinux.so keeps SELinux disabled inside the env.
#
# Either way the env is functional; we just prefer the virtualized design.
set -e

ROOTFS_PATH="${ROOTFS_PATH:-/}"
EXTRA_BINDINGS="${EXTRA_BINDINGS:-}"

# Synthetic selinux view: report "enforcing" to in-chroot probes (virtual kernel).
mkdir -p /support/selinux-virtual
[ -f /support/selinux-virtual/enforce ] || printf '1\n' > /support/selinux-virtual/enforce

if command -v proot >/dev/null 2>&1; then
  # --- PRIMARY: virtual-kernel design ---
  if proot -0 \
      -r "$ROOTFS_PATH" \
      -b /dev -b /proc -b /sys \
      -b /dev/pts:/dev/pts \
      -b /support/selinux-virtual/enforce:/sys/fs/selinux/enforce \
      -b /support/selinux-virtual/enforce:/proc/self/attr/current \
      $EXTRA_BINDINGS \
      -w /root \
      /bin/true 2>/dev/null; then
    exec proot -0 \
      -r "$ROOTFS_PATH" \
      -b /dev -b /proc -b /sys \
      -b /dev/pts:/dev/pts \
      -b /support/selinux-virtual/enforce:/sys/fs/selinux/enforce \
      -b /support/selinux-virtual/enforce:/proc/self/attr/current \
      $EXTRA_BINDINGS \
      -w /root \
      /bin/sh -c "$@"
  fi
  # --- SECONDARY: classic selinux-disabled shim (LD_PRELOAD handles selinux) ---
  exec proot \
    -r "$ROOTFS_PATH" \
    -b /dev -b /proc -b /sys \
    -b /dev/pts:/dev/pts \
    $EXTRA_BINDINGS \
    -w /root \
    /bin/sh -c "$@"
fi
exec /bin/sh -c "$@"
