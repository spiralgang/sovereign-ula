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
