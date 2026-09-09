# GitBot architecture

GitBot has two repositories with different jobs: `Dashrath175/GitBot` is the public product source and is hard-blocked by the automation workflow; a user's private `owner/GitBot` repository is the automation target.

## Sources of truth

| Domain | Authority |
|---|---|
| reachable commits | fetched `origin/main` |
| GitBot commit attribution | committed `data/provenance.json` plus `GitBot-*` trailers |
| initialization | exact initialization commit |
| target, pause, vacation and sessions | committed control/state data |
| workflow status | GitHub Actions API |
| profile contribution graph | GitHub itself; it is never inferred from repository commit counts |

Dashboard output must label remote observations `VERIFIED`, `STALE`, `UNVERIFIED`, or `OFFLINE`. Planned and predicted values are never presented as actual activity.

## Provenance

Every GitBot-generated commit records a random event ID and a session ID in the committed ledger and in three commit trailers: `GitBot-Event-Id`, `GitBot-Session-Id`, and `GitBot-Schema`. Human-readable messages, author email, and changed files are not attribution evidence.
