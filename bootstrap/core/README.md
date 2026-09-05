# bootstrap/core — FSM STATE 1: AGNOSTIC CORE

Universal execution layer, shared verbatim by every deployed distro. The
FSM enforcer (`hermes_fsm_enforce.yml`) forbids these files from living
inside any distro directory (`bootstrap/<distro>/`) — they must stay here.

## Contents

- `support/` — the universal support layer the tech.ula runtime expects at
  `/support/` inside the rootfs:
  - `support/common/extractFilesystem.sh`, `support/common/compressFilesystem.sh`
    (invoked by the tech.ula runtime — do NOT rename or move)
  - `support/execInProot.sh` (proot entrypoint)
  - `support/startSSHServer.sh`, `support/original/startSSHServer.sh`
    (original dropbear config = source-of-truth fallback)
  - `support/ssh-anchor.sh` (device-IMEI anchored SSH)
  - `support/startVNCServer*.sh`, `support/startXSDLServer.sh`
  - `support/addNonRootUser.sh`
  - `support/ld.so.preload` (SELinux-disable shim link), `support/userland_profile.sh`
- `sovereign-motd.sh` — first-boot MOTD walk-through banner (universal).
- `termuxvoid-shim.sh` — glibc/termux translation layer (aarch64 glibc
  packages run natively inside the env).

## How distros consume it

Distro builds (e.g. `bootstrap/ubuntu/`) use `bootstrap/` as the Docker build
context and copy `core/` in (`COPY core/ /core/`), then `main.sh` installs the
files into the rootfs `/support/` tree. Nothing here is distro-specific.