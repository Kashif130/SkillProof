# Deployment and live-proof checklist (StudioNet)

Source SHA-256 (contracts/SkillProof.py): 725c089f77e677f23b9b30deae187707993096bffc0ccd8f2334888ba720d0bf

1. Deploy contracts/SkillProof.py (no constructor args). Record address, deploy tx, deployer, time.
2. As owner: add_skill("solidity", "Solidity", "<concrete rubric>"). set_moderator(<second wallet>, true).
3. Host a page you control (e.g. frontend public/skillproof/index.html) containing SKP-<wallet>-<skill>.
4. Capture finalized txs for: submit_claim success, genuine rejection, appeal + resolve_appeal approve, appeal + reject, refresh_badge (renew/upgrade), revoke_badge, reinstate_badge, burn_badge + re-claim.
5. Capture one verify_skill result and one get_badge_metadata result.
6. Clock check on the new deployment: call debug_clock(); claims, appeals and refresh must not fail with "Contract clock unavailable".
7. Wait for FINALIZED, not just accepted, before recording a tx.
