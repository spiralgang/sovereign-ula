#!/bin/sh
# Sovereign ULA — MOTD / settings walk-through banner.
# Sourced from userland_profile.sh; prints on interactive login.
# The bundled sov_hero image is delivered by the app into /support/sov_hero.jpeg
# and is shown as the in-app MOTD background by the Android UI.
SOVEREIGN_REPO="https://github.com/spiralgang/sovereign-ula"
SOVEREIGN_FUNDING="$SOVEREIGN_REPO#sponsors"

print_banner() {
cat <<'EOF'

   ____  ____  ___  ___  ____  ____  _   _ ___ _   _  ____
  / ___||  _ \|_ _|/ _ \|  _ \|  _ \| | | |_ _| \ | |/ ___|
  \___ \| |_) || || | | | |_) | |_) | | | || ||  \| | |  _
   ___) |  _ < | || |_| |  _ <|  __/| |_| || || |\  | |_| |
  |____/|_| \_\___\___/|_| \_\_|    \___/|___|_| \_|\____|

  SOVEREIGN-ULA  ·  Ubuntu 24.04 (Noble)  ·  aarch64
  Self-sovereign Linux-in-a-box. No phoning home.

EOF
}

print_walkthrough() {
SOVEREIGN_MOTD_IMG="/support/sov_hero.jpeg"
cat <<EOF
  ── FIRST-BOOT WALK-THROUGH ──────────────────────────────────────────
  1. PERMISSIONS  Grant from Android Settings → Apps → SOVEREIGN-ULA:
     Storage (all-files), Overlay, Accessibility. Use the in-app Edge
     Panel to deep-link each grant.
  2. SHARED STORAGE  Mounted at /storage/internal (Doc/DL/Pictures/Music).
     Export/import there — it bridges to the host OS.
  3. COMMANDS (pre-seeded)  apt/nala · git/gh · pip3 · node/npm · gcloud
     · cmake/make/gcc · aapt2/apktool · proot · nvidia-smi (client)
  4. AI / CLOUD  Hermes, Gemini CLI, gh, gcloud pre-installed. Export keys:
     export NVIDIA_API_KEY=…   (see Settings → Env)
  5. LICENSING & FUNDING  Rebrand of open-source UserLAnd (GPLv3).
     Source: $SOVEREIGN_REPO   Fund: $SOVEREIGN_FUNDING
  6. MOTD IMAGE  $SOVEREIGN_MOTD_IMG (sov_hero) shown as walk-through bg.
  ─────────────────────────────────────────────────────────────────────
EOF
}

if [ -t 0 ] && [ -z "${SOVEREIGN_MOTD_SEEN:-}" ]; then
    print_banner
    print_walkthrough
    export SOVEREIGN_MOTD_SEEN=1
fi
