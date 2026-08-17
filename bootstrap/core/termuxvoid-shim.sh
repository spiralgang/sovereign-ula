#!/bin/bash
#
# glibc / termuxvoid translation layer (universal support add-on).
#
# The base chroot env (built by Arch/Alpine + proot) is standard aarch64 glibc.
# termuxvoid and other aarch64 glibc packages built for the Termux/Android
# userspace expect Android-ish prefixes and a Bionic-style loader, so they fail
# to find their interpreter/libs. This shim provides:
#   1. FHS compatibility symlinks so termuxvoid path expectations resolve.
#   2. a `tvrun` wrapper setting LD_LIBRARY_PATH so aarch64 glibc binaries run.
#
#   termuxvoid-shim.sh install   -> set up the layer
#   termuxvoid-shim.sh remove    -> tear it down
#
set -e
TV_ROOT="/support/termuxvoid"

install_layer() {
  mkdir -p "$TV_ROOT/bin"
  cat > "$TV_ROOT/bin/tvrun" <<'WRAP'
#!/bin/bash
# Run an aarch64 glibc binary built for the termuxvoid/Termux userspace.
set -e
BIN="$1"; shift
export LD_LIBRARY_PATH="/support/termuxvoid/lib:/usr/lib/aarch64-linux-gnu:/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$BIN" "$@"
WRAP
  chmod +x "$TV_ROOT/bin/tvrun"
  ln -sfn /usr "$TV_ROOT/compat-usr" 2>/dev/null || true
  cat > "$TV_ROOT/fhs.map" <<'MAP'
# termuxvoid path -> ubuntu noble path
/data/data/com.termux/files/usr  ->  /usr
/data/data/com.termux/files/home  ->  /home
MAP
  cat > /etc/profile.d/termuxvoid.sh <<'PROF'
export PATH="/support/termuxvoid/bin:$PATH"
PROF
  chmod +x /etc/profile.d/termuxvoid.sh
  echo "termuxvoid shim installed at $TV_ROOT"
}

remove_layer() {
  rm -rf "$TV_ROOT"
  rm -f /etc/profile.d/termuxvoid.sh
  echo "termuxvoid shim removed"
}

case "${1:-install}" in
  install) install_layer ;;
  remove)  remove_layer ;;
  *) echo "usage: $0 [install|remove]"; exit 1 ;;
esac
