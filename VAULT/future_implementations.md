# VAULT — Sovereign ULA : Future Implementations

This file is the living roadmap for the Sovereign ULA app. The GOAL is the
**Sovereign ULA app** (rebranded UserLAnd / tech.ula runtime, package
`dev.soveriegn.ula`). The unique features we ship on top are the Sovereign
Edge Panel settings, the floating edge-panel overlay, mandatory signing
enforcement, billing-off, and Arch as the default distribution. Everything below
is future work layered onto that base.

## 1. GNU/glibc (tech.ula) ↔ glibc-com.termux shim compatibility  [Gemini track]
- Problem: tech.ula env packages are GNU/glibc-built; com.termux env packages are
  bionic/glibc-built for the Termux runtime. They don't load into the same process
  space without translation.
- Goal: a shim translation layer so BOTH package sets can be used together inside
  the Sovereign ULA container.
- Approach (Gemini-owned): LD_PRELOAD shim + syscall/loader translation; shared
  `/compat` mount exposing each env's libc; `binfmt` registration so the opposite
  libc binaries exec through the shim automatically.

## 2. Smart auto-bundle package manager  [Gemini track]
Replaces/adopts the `pkg` `setup` command with intelligent bundling:
- Suggest related command packages when a base package is installed (like a proper
  meta-bundle): e.g. install `git` -> suggest `bash-completions`, `git-extras`.
- Auto community repositories: opt-in community repo sources fetched + verified.
- Automated package management: tracks duplicate install downloads; stores ONE
  canonical copy and symlinks consumers to it. Only on EXPORT from the env does it
  materialize a duplicate generic package, so in-env storage stays minimal (least
  storage + RAM weight).
- Start packages: `nala`, `aptly`, `aptitude`, `bash-completion`,
  `apt-completion` wired into the setup suggester.

## 3. Process + second-user isolation
- A second, unprivileged user inside the env so commands run separately from the
  primary UID (process/permission containment).
- cgroup/namespace controls so the Sovereign app can cap CPU/RAM per command.

## 4. Virtual runtime containerization
We already SSH into a virtual engine / virtual runtime / virtual env. Formalize it:
- **Virtual kernel**: a minimal guest kernel + userland boot inside the Sovereign
  ULA container (proot/PRoot already provides the userspace; add the kernel shim).
- **Virtual zram**: compressed RAM block device for the env's swap/tmp to cut
  storage + RAM weight.
- **Virtual CPUs / GPUs**: expose vCPU scheduling; if the host/GPU passthrough is
  possible, map a virtual GPU (`vGPU`) into the env for compute.
- **Virtual storage over cloud network**: the app's storage weight lives as GBs on a
  virtual cloud network; back the env's `/data` with an AWS-backed volume (S3/EFS
  style) so the container "runs on" remote storage the same way tech.ula runs
  anywhere. Auto-bootstrap the latest, best, lite Arch packages on first boot.

## 5. In-app update prompt (user-optional)
- A Release feed (GitHub Releases) polled on launch; if a newer signed APK exists,
  show an OPTIONAL "update available" dialog that downloads + offers to install
  (user-driven, never forced). Verifies the new APK's cert against the mandated
  release cert before offering install.

## 6. Build/CI hardening (done in main workflow; track here)
- ubuntu-latest Gradle assembleRelease -> apksigner -> GitHub Release.
- Pinned old SDK platforms (android-28 r06 / android-29 r04) + NDK 21.4.7075529 for
  the fragile AGP 3.4.3 toolchain.
- Secrets: SOVEREIGN_KEYSTORE_BASE64 / ALIAS / passwords. Mandatory cert SHA-256 in
  SovereignApplication.kt.
