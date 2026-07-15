#!/bin/sh
# Sovereign ULA — MOTD / settings walk-through banner.
# Sourced from /etc/profile.d/ and printed on interactive login.
# Uses the bundled sov_hero image path as the walk-through background ref.
#
# NOTE: the actual image is delivered by the Android app into the chroot at
# /support/sov_hero.jpeg (copied from the app's assets). This script merely
# points the terminal-based walk-through at it and renders an ASCII banner.

SOVEREIGN_MOTD_IMG="/support/sov_hero.jpeg"
SOVEREIGN_REPO="https://github.com/spiralgang/sovereign-ula"
SOVEREIGN_FUNDING="$SOVEREIGN_REPO#sponsors"   # GitHub Sponsors / funding link

print_banner() {
cat <<'EOF'

   ____  ____  ___  ___  ____  ____  _   _ ___ _   _  ____
  / ___||  _ \|_ _|/ _ \|  _ \|  _ \| | | |_ _| \ | |/ ___|
  \___ \| |_) || || | | | |_) | |_) | | | || ||  \| | |  _
   ___) |  _ < | || |_| |  _ <|  __/| |_| || || |\  | |_| |
  |____/|_| \_\___\___/|_| \_\_|    \___/|___|_| \_|\____|

  SOVEREIGN-ULA  ·  Ubuntu 24.04 (Noble)  ·  aarch64
  Self-sovereign Linux-in-a-box. No phoning home. Your device, your rules.

EOF
}

print_walkthrough() {
cat <<'EOF'
  ── FIRST-BOOT WALK-THROUGH ──────────────────────────────────────────
  1. PERMISSIONS
     Grant the requested permissions from Android Settings → Apps →
     SOVEREIGN-ULA. Required: Storage (all-files), Overlay, Accessibility.
     Use the in-app Sovereign Edge Panel to deep-link each grant.

  2. STORAGE / SHARED DOWNLOADS
     Your Android Shared Storage & Downloads are mounted at:
        /storage/shared    (Documents, Downloads, Pictures, Music …)
     Export/import your files there — it is the bridge to the host OS.

  3. COMMANDS & PACKAGES (pre-seeded, ready to use)
        apt/nala      · git/gh        · pip3/cpython
        node/npm      · gcloud        · cmake/make/gcc
        aapt/aapt2    · apktool       · @google/gemini-cli
        nvidia-smi (client libs)      · proot (chroot shell)
     Update the distro any time:   sudo apt update && sudo apt upgrade

  4. AI AGENTS / CLOUD ENVS
     Hermes Agent, Gemini CLI, GitHub CLI, and gcloud are pre-installed.
     Export your keys via:  export NVIDIA_API_KEY=…  (see Settings → Env)

  5. LICENSING & FUNDING
     SOVEREIGN-ULA rebrands the open-source UserLAnd runtime (GPLv3).
     Source & build: $SOVEREIGN_REPO
     Fund development: $SOVEREIGN_FUNDING

  ─────────────────────────────────────────────────────────────────────
EOF
}

# Only show on interactive, non-scrolled shells (avoid spamming scripts).
if [ -t 0 ] && [ -z "$SOVEREIGN_MOTD_SEEN" ]; then
    print_banner
    print_walkthrough
    export SOVEREIGN_MOTD_SEEN=1
fi
