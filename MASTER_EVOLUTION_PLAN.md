# Master Evolution Plan: sovereign-ula

## Current Objective
- [ ] Wave A: Un-break CI (Repair workflows and remove junk)

## Roadmap
1. **Wave A: Un-break CI**
   - Repair \`.github/workflows/ai-agent-review.yml\` and \`distro-deploy-listener.yml\`.
   - Clean up CodeQL matrix and remove duplicate enforcer workflows.
   - Remove junk scripts (\`create.py\`, \`run_ula_job.py\`).
2. **Wave B: Finish FSM Migration**
   - Rewire universal layer into \`bootstrap/core/\`.
   - Remove banned files from \`bootstrap/ubuntu/input/\`.
   - Fix enforcer's recursive scan blind spot.
3. **Wave C: Restore the Compile**
   - Remove duplicate declarations in \`GithubApiClient.kt\` and \`GithubAppsFetcher.kt\`.
   - Fix duplicate blocks in \`app/build.gradle\`.
4. **Wave D: Sync Governance Docs**
   - Update \`PLANS.md\`, \`README.md\`, \`AGENT_INSTRUCTIONS.md\`, and \`RULES.md\` to reflect Ubuntu Noble default.
5. **Wave E: Land the Agentic Layer**
   - Integrate \`.agent/\` suite and \`bootstrap/core/agent-tooling/\`.
6. **Wave F: Hardening & Cleanliness**
   - Untrack \`decoded/\` artifacts.
   - Enable unit tests in CI.
