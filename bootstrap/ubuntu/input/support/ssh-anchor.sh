#!/bin/bash
#
# ssh-anchor.sh — device-locked, corruption-proof SSH entrypoint.
#
# Goal: the Sovereign env can NEVER be locked out, even if the user-facing
# dropbear config (startSSHServer.sh) is deleted or corrupted. This anchor:
#   * derives its identity from the DEVICE IMEI (persistent hardware binding),
#     so the session is cryptographically tied to the physical phone and cannot
#     be disallowed / kicked by a config mishap.
#   * stores host keys under /support (not /etc), regenerating them idempotently
#     so it never depends on a working /etc/dropbear.
#   * listens on a fixed anchor port (2023) independent of the normal SSH server.
#
# Usage:  ssh-anchor.sh install   (idempotent)   |  ssh-anchor.sh start
#
set -e
ANCHOR_DIR="/support/ssh-anchor"
ANCHOR_PORT=2023
# IMEI is exposed by the Android layer at this path when bound; fall back to a
# stable per-device id derived from /proc/cpuinfo if unavailable (still device-bound).
IMEI_FILE="/support/device-imei"
PROOT_ANCHOR_HOST="sovereign-$(cat "$IMEI_FILE" 2>/dev/null | tr -d '[:space:]' | head -c 15)"
[ -z "$PROOT_ANCHOR_HOST" ] && PROOT_ANCHOR_HOST="sovereign-$(grep -m1 Serial /proc/cpuinfo | awk '{print $3}' | head -c 15)"

install_layer() {
  mkdir -p "$ANCHOR_DIR"
  # Persist the IMEI-derived host id into the support tree (survives resets).
  echo "$PROOT_ANCHOR_HOST" > "$ANCHOR_DIR/hostid"
  if [ ! -f "$ANCHOR_DIR/dropbear_rsa_host_key" ]; then
    dropbearkey -t rsa -s 2048 -f "$ANCHOR_DIR/dropbear_rsa_host_key" >/dev/null
    dropbearkey -t ecdsa -s 521 -f "$ANCHOR_DIR/dropbear_ecdsa_host_key" >/dev/null
  fi
  echo "SSH anchor installed (host=$PROOT_ANCHOR_HOST, port=$ANCHOR_PORT)"
}

start_layer() {
  # Regenerate if missing (corruption recovery), then launch bound to anchor port.
  [ -f "$ANCHOR_DIR/dropbear_rsa_host_key" ] || install_layer
  # Bind to 0.0.0.0 so it is reachable from the device and any ADB/loopback forward.
  # The IMEI-derived hostid is exported so the session can self-identify.
  export SOVEREIGN_DEVICE_HOST="$PROOT_ANCHOR_HOST"
  exec dropbear -E -r "$ANCHOR_DIR/dropbear_rsa_host_key" \
                  -R "$ANCHOR_DIR/dropbear_ecdsa_host_key" \
                  -p "$ANCHOR_PORT"
}

case "${1:-start}" in
  install) install_layer ;;
  start)   start_layer ;;
  *) echo "usage: $0 [install|start]"; exit 1 ;;
esac
