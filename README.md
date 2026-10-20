# SkillProof v0.1

Non-transferable (soulbound) skill badges for GenLayer, backed by evidence that validators fetch and an LLM grades.

## How a claim works
1. Owner or a moderator registers a skill with a grading rubric (`add_skill`).
2. The developer reads their token with `get_ownership_token(wallet, skill)`: `SKP-<wallet>-<skill>`.
3. They publish that token in the main content of the FIRST evidence page (a profile README, a gist, a GitHub Pages site).
4. They call `submit_claim(skill, "https://...|https://...")` with 1 to 3 https links joined by `|`.
5. Validators fetch the pages, check the token, and the LLM answers `{"level": "none|basic|intermediate|advanced"}`.
6. The level is capped by readable evidence pages: 1 page basic, 2 intermediate, 3 advanced.

## Rules enforced on-chain
- Ownership token required on evidence page 1, never in comments, navigation or footer.
- Evidence hosts come from an owner-managed allowlist (https only, no ports, no user@host). `*.example.com` suffix rules supported.
- LLM output must be exactly one key, `level`, with one of four lowercase strings. Anything else reverts and costs no attempt.
- Technical failures (unreachable or unreadable ownership page, malformed LLM output, unusable node clock) revert and cost no attempt.
- Genuine rejections (`no_token`, `llm_fail`) cost one of 3 attempts and store a reason code.
- Appeals are reviewed by moderators; a rejected or expired appeal never costs unused attempts. A pending appeal blocks new claims. Moderators cannot decide their own appeal.
- Badges are wallet-bound: no transfer, approve or delegate function exists. The holder can `burn_badge` and later claim again.
- Badges expire after 365 days. `refresh_badge` renews or upgrades (never downgrades), 24 h cooldown, works on an expired badge.
- Moderators `revoke_badge` (reason required) and `reinstate_badge`. A burned badge cannot be reinstated.

## For verifiers
`verify_skill(wallet, skill, min_level, at)` returns `valid`, `reason` (`ok`, `expired`, `revoked`, `burned`, `level_too_low`, `no_badge`, `clock_unavailable`), level, expiry. Pass `at` (UTC `YYYY-MM-DDTHH:MM:SSZ`) for a point-in-time check. If the node gives no clock in a read call, `valid` is `null` and `expires_at` lets you decide. `get_badge_metadata` returns marketplace-style metadata with `soulbound: true`.

## Tests
```
python3 tests/offline/run_offline.py .     # 127 tests
python3 tests/offline/run_mutants.py       # 49 mutants, all must be caught
```
Offline tests use an SDK shim: they prove contract logic, not consensus behaviour. Run the live flow on StudioNet before submitting (see deploy/DEPLOYMENT.md).

## Known limits
- LLM grading is subjective. Rubrics should be concrete (commit history, tests, originality). `strict_eq` consensus can fail when validators disagree on a level; the call then fails and the user may retry.
- Token proves control of the first page, not authorship of the supporting pages. The prompt asks the model to credit only matching-author work; that is a heuristic.
