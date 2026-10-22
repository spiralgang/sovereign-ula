# MASTER EVOLUTION PLAN — Sovereign ULA

## Vision
To transform the Sovereign ULA from a rebranded UserLAnd fork into a self-sovereign, agentic operating layer for Android—a foundation where AI agents can be deployed, managed, and evolved autonomously.

## Capability Levels
- **L1.0: Baseline Sovereign** (Current) - Rebranded APK, Ubuntu 24.04 Noble bootstrap, GHA CI/CD.
- **L2.0: Sovereign Control** - Fully functional Edge Panel, deep-linked permissions, and hardened signing enforcement.
- **L3.0: Agent-Ready Rootfs** - Pre-seeded agent toolchains (Hermes, Python, Node), automated environment setup, and integrated agent-comms.
- **L4.0: Recursive Evolution** - Integration of the Evolution App paradigm into the rootfs lifecycle; self-modifying bootstrap and config.
- **L5.0: Sovereign Ecosystem** - Cloud-synced environment state, Drive-backed agent memories, and cross-distro agent portability.

## Evolutionary Roadmap

### Phase 1: Foundation (L1.0 $\rightarrow$ L1.5)
- [x] Rebrand to `dev.sovereign.ula`.
- [x] Default to Ubuntu 24.04 (Noble).
- [x] Establish GHA Build $\rightarrow$ Sign $\rightarrow$ Release pipeline.
- [ ] Verify `sov_hero` branding across all touchpoints.

### Phase 2: Sovereign Control (L1.5 $\rightarrow$ L2.0)
- [ ] **Edge Panel Implementation**: Develop the `EdgePanelService` and the Sovereign settings category.
- [ ] **Permission Orchestration**: Create deep-links from the app to Android system settings for required permissions.
- [ ] **Signing Hardening**: Ensure `SovereignApplication` strictly enforces release-cert signatures.

### Phase 3: Agent-Ready Rootfs (L2.0 $\rightarrow$ L3.0)
- [ ] **Toolchain Pre-seeding**: Update `bootstrap/core/` to include essential agent deps (curl, git, python3, nodejs).
- [ ] **Agent Bootstrap**: Create a `/etc/sovereign-agent/` config that allows agents to initialize upon first boot.
- [ ] **MOTD Evolution**: Transform the first-boot MOTD into an interactive agent-onboarding guide.

### Phase 4: Recursive Evolution (L3.0 $\rightarrow$ L4.0)
- [ ] **Evolutionary Manifest**: Expand `.evolution-app.json` to track detailed capability matrices.
- [ ] **Self-Modifying Bootstrap**: Implement a mechanism where the Evolution App can push updates to the bootstrap scripts via PRs, which are then reflected in the next rootfs build.
- [ ] **Automated Gap Analysis**: Integrate codebase auditing tools into the rootfs to feed back into the Evolution App.

### Phase 5: Sovereign Ecosystem (L4.0 $\rightarrow$ L5.0)
- [ ] **State Persistence**: Implement Google Drive / Cloud backup for agent memories and environment configs.
- [ ] **Multi-Distro Core**: Abstract the agent toolchain so it can be deployed across Ubuntu, Debian, and Arch without modification.
- [ ] **Sovereign Registry**: Create a registry of "Evolutionary Modules" (pre-verified agent capabilities) that can be opted-into via the app.

## Tracking
- **Current Level**: 1.0
- **Next Objective**: Phase 2 - Edge Panel & Permission Orchestration.
