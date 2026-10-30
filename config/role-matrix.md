# Role Matrix — engineering WP2 (no OIDC in this package)

| Role | Draft parameter/mapping | Submit owned draft | Review/approve/reject | Query versions | Production identity |
|---|---|---|---|---|---|
| MAKER | YES | YES | NO | YES | WP6 OIDC pending |
| CHECKER | NO | NO | YES, only different maker | YES | WP6 OIDC pending |
| AUDITOR | NO | NO | NO | YES (read-only) | WP6 OIDC pending |
| ADMINISTRATOR | NO | NO | NO | YES (no regulator actions) | WP6 OIDC pending |
| ALCO | NO | NO | NO | YES (scoped access in UI WP6) | WP6 OIDC pending |

This is the **service-layer role policy**, implemented in WP2 via `Principal.role`
read from storage. The PostgreSQL database migration enforces approval SoD,
registered checker role, immutable approved revisions and workflow transitions.
**Not yet production-ready:** trusted OIDC/SSO claim mapping, principal lifecycle,
least-privilege DB roles, session management and feature-specific row filtering.
The test harness uses synthetic principals; passing these tests is NOT proof of
Bank identity integration or a full access-control penetration test.
