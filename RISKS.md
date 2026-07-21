# Risk register — Parallax

A living register. Every risk names an owner, a concrete observable tripwire, and a status. Risks
that cannot name an observable signature belong in speculation, not here. Seeded from the BLUEPRINT
chapter's "Failure Modes and Mitigations"; this table grows as the system does.

| Risk | Owner | Tripwire | Status |
|---|---|---|---|
| Extraction false positives pollute the commitment/assumption ledgers, eroding PM trust in the tool. Mitigation: entries are quote-anchored, start unconfirmed, need one-click confirm/reject, and precision is tuned to prefer missing a weak promise over inventing one. | eng lead | On any hand-labeled transcript batch, unconfirmed-ledger-entry precision drops below the EVAL.md threshold, or confirmed entries lacking a valid source-quote span appear in the store. | open |
| Observed metrics get gamed once the team knows they are watched (e.g. inflated commit counts), making the Drift Index read falsely healthy. Mitigation: the index reads breadth — trajectory, review latency, cross-signal agreement — not any single countable. | eng lead | Commit-count activity for an epic diverges from PR-merge reality beyond a set margin, or per-epic cross-signal agreement (commits vs PRs vs reviews) falls below its floor. | open |
