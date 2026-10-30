# Integration status (30 Oct 2026)

This repository assembles the pre-existing WP0, WP1, WP2 and technical audit deliverables into separate traceable Git commits with non-fast-forward local merges. **No GitHub PR has been merged**: the LRM repository has not been created or identified on the connected GitHub account. All commits here are LOCAL until a private target is provided and a push succeeds.

- Engine: foundation only; no operational LCR/NSFR/ILAAP.
- Regulation factors: DRAFT_UNVERIFIED; no active Bank-approved akad mapping.
- Test evidence: 113/113 local pytest passing on Python 3.13.5.
- Bank production release gate: HOLD.
- Sensitive source proposal PDF and Bank record data are not committed.

## Import into a new private repository

Create a **private** repository for the LRM project, then from the extracted worktree:

```sh
git remote add origin git@github.com:YOUR-OWNER/YOUR-PRIVATE-LRM-REPO.git
git push -u origin main
git push origin feature/wp1-data-contract feature/wp2-governance docs/technical-audit-rtm
```

For offline history restore use the accompanying `.bundle` instead:

```sh
git clone LRM_KB_Syariah_Git_History_20261030.bundle lrm-kb-syariah
```

Run required CI, PostgreSQL integration and security reviews before release.
