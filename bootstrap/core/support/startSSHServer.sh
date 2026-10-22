#! /bin/bash
# EVOLVED startSSHServer.sh — run BOTH SSH designs concurrently (not fallback):
#   * NEW design : device-IMEI anchored SSH (ssh-anchor.sh) on port 2023.
#   * ORIGINAL    : CypherpunkArmory dropbear (source of truth) on port 2022.
# Both stay up; both keep SELinux disabled inside the env. Neither depends on
# the other, so the env can never be locked out.
set -e

# ORIGINAL dropbear (secondary/source-of-truth) — verbatim config.
/support/original/startSSHServer.sh 2>/dev/null || dropbear -E -p 2022 2>/dev/null || true

# NEW design — device-anchored SSH (primary choice).
/support/ssh-anchor.sh start 2>/dev/null || true

echo "SSH: original dropbear (2022) + device-anchored (2023) both attempted"
