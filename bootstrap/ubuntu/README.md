# Sovereign ULA — Ubuntu 24.04 (Noble) bootstrap

Modernized replacement for the 8-year-old `UserLAnd-Assets-Debian` bootstrap,
built for **Sovereign ULA** (`dev.soveriegn.ula`).

## How it fits the runtime

The tech.ula runtime (which we forked) builds a **universal chroot base env**
(Arch Linux + Alpine + proot machinery) and then **overlays the chosen distro's
rootfs** on top to operate. So:

- `input/main.sh` builds the **Ubuntu 24.04 (Noble)** rootfs filesystem.
- `input/support/*` is the **universal support layer** (`/support/common/*`,
  `execInProot.sh`, SSH/VNC servers, MOTD, glibc/termuxvoid shim) — identical
  for every deployed distro.
- `build.sh` packages `release/<arch>-rootfs.tar.gz` + `release/<arch>-assets.tar.gz`
  in the layout the app already pulls from `spiralgang/UserLAnd-Assets-Ubuntu`.

## FSM Architecture: File Organization Rules

**All distro builds MUST respect the Finite State Machine (FSM) boundary**:

### bootstrap/core/ (Universal — ALL distros)
- **Agnostic scripts** that run on every Linux distro (Arch, Alpine, Ubuntu, Debian, etc.)
- **Examples**: `termuxvoid-shim.sh`, `extractFilesystem.sh`, `addNonRootUser.sh`, busybox, etc.
- **Shared across**: Every deployed distro in `bootstrap/<distro>/input/support/`
- **Single source of truth**: Only one copy allowed

### bootstrap/<distro>/input/ (Distro-specific ONLY)
- **Main build script**: `main.sh` — customizations unique to this distro
- **Distro-specific support**: `sovereign-motd.sh`, SELinux shims, etc.
- **DO NOT include**: Files from bootstrap/core/ (violates FSM boundary)
- **Build process**: `build.sh` stages `bootstrap/core/*` → `/input/` automatically

## CI/CD Validation

The workflow `.github/workflows/hermes_fsm_enforce.yml` enforces this boundary:

```bash
BANNED_DISTRO_FILES="extractFilesystem.sh|addNonRootUser.sh|termuxvoid-shim.sh|busybox|tvrun"
```

**Violation Result**: PR is rejected immediately to save LLM compute.

## Build

```bash
# one arch
./build.sh arm64
# all arches via bake
docker buildx bake -f docker-bake.hcl
```

Requires Docker with `binfmt-support` + `qemu-user-static` for cross-arch.

## What's pre-seeded (vs the 8-year-old Debian build)

- Noble (24.04) instead of buster/jammy
- `gh`, `git`, `python3`+pip, `node`/`npm`, `gcloud`, `cmake`/`make`/`gcc`,
  `aapt2`/`apktool`, `nvidia` client libs, `sqlite3`, `openssh-client`
- `termuxvoid-shim.sh` — translation layer so aarch64 glibc packages (termuxvoid)
  run natively inside the env
- `sovereign-motd.sh` — first-boot walk-through banner (sov_hero background)
