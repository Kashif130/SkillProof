"""Breaks SkillProof in known ways; every mutant must make at least one test fail."""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", ".."))
ORIG = open(os.path.join(SRC, "contracts", "SkillProof.py")).read()

E = "{ERROR_EXPECTED}"
MUTANTS = {
    "ownership token not required": [(
        '    if not _has_token(text0.lower(), token.lower()):\n        return json.dumps({"status": "no_token"})\n', '')],
    "level not capped by evidence": [(
        '    level = min(LEVEL_NAMES.index(verdict), cap)', '    level = LEVEL_NAMES.index(verdict)')],
    "cap ignores unreadable pages": [(
        '    cap = min(len(pages), MAX_EVIDENCE)', '    cap = MAX_EVIDENCE')],
    "supporting pages never fetched": [(
        '    for u in urls[1:]:', '    for u in []:')],
    "level none is not a rejection": [(
        '    if verdict == "none":\n        return json.dumps({"status": "llm_fail"})\n', '')],
    "verdict parser accepts extra keys": [(
        'list(obj.keys()) != ["level"]', '"level" not in obj')],
    "verdict parser case-insensitive": [(
        'isinstance(v, str) and v in LEVEL_NAMES', 'isinstance(v, str) and v.lower() in LEVEL_NAMES')],
    "unreachable page counts as a rejection": [
        ('        if status_out == "unreachable":\n            raise gl.vm.UserError(f"{ERROR_TRANSIENT} Ownership page unreachable, try again later")\n', ''),
        ('        if status_out not in ("llm_fail", "no_token"):\n            raise gl.vm.UserError(f"{ERROR_LLM} Unknown verification status")\n        self.reject_reasons[sub] = status_out',
         '        self.reject_reasons[sub] = status_out')],
    "rejections cost no attempt": [(
        '        self.attempts[sub] = u256(used + 1)\n        self.window_until[sub] = _plus_secs(now, APPEAL_WINDOW_SECS)',
        '        self.window_until[sub] = _plus_secs(now, APPEAL_WINDOW_SECS)')],
    "attempt cap not enforced": [(
        '        if used >= MAX_ATTEMPTS:\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} Attempts exhausted - use appeal()")\n', '')],
    "rejection reason not stored": [(
        '        self.reject_reasons[sub] = status_out\n        self.claim_evidence[sub] = evidence\n',
        '        self.claim_evidence[sub] = evidence\n')],
    "evidence host allowlist ignored": [(
        '            if not self._host_allowed(host):\n                raise gl.vm.UserError(f"{ERROR_EXPECTED} Evidence host not allowed: {host}")\n', '')],
    "suffix rule matches bare domain": [(
        '        for i in range(1, len(labels) - 1):', '        for i in range(0, len(labels) - 1):')],
    "evidence count unlimited": [(
        '        if not (1 <= len(urls) <= MAX_EVIDENCE):', '        if not (1 <= len(urls)):')],
    "fragment not stripped": [(
        '            u = raw.split("#")[0]', '            u = raw')],
    "holder can claim again": [
        ('        if status not in ("none", "rejected", "expired", "appeal_rejected", "appeal_expired", "burned"):',
         '        if status not in ("none", "rejected", "expired", "appeal_rejected", "appeal_expired", "burned", "approved"):'),
        ('        if self.submissions.get(sub, "none") == "approved":\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} Wallet already holds a badge for this skill")\n', '')],
    "pending appeal does not block claims": [(
        '        if status not in ("none", "rejected", "expired", "appeal_rejected", "appeal_expired", "burned"):',
        '        if status not in ("none", "rejected", "expired", "appeal_rejected", "appeal_expired", "burned", "appeal_pending"):')],
    "appeal window not enforced": [(
        '        if until == "" or now > until:\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} The appeal window has closed")\n', '')],
    "moderator can decide own appeal": [(
        '        if str(gl.message.sender_address).lower() == w:\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} You cannot decide your own appeal")\n', '')],
    "anyone can resolve appeals": [(
        '        self._only_mod()\n        self._get_skill(skill)\n        w = wallet.lower()', '        self._get_skill(skill)\n        w = wallet.lower()')],
    "approval accepts any level": [(
        '            if not (1 <= lv <= 3):\n                raise gl.vm.UserError(f"{ERROR_EXPECTED} Level must be 1, 2 or 3 when approving")\n', '')],
    "rejected appeal burns remaining attempts": [(
        '            self.submissions[sub] = "appeal_rejected"\n',
        '            self.submissions[sub] = "appeal_rejected"\n            self.attempts[sub] = u256(MAX_ATTEMPTS)\n')],
    "approved appeal loses evidence": [(
        'SOURCE_APPEAL, self.claim_evidence.get(sub, ""))', 'SOURCE_APPEAL, "")')],
    "expire_stale ignores the appeal window": [(
        '            if until == "" or now <= until:\n                raise gl.vm.UserError(f"{ERROR_EXPECTED} Appeal window is still open")\n', '')],
    "burn does not revoke": [(
        '        b.revoked = True\n        b.burned = True\n', '        b.burned = True\n')],
    "anyone can revoke": [(
        '        self._only_mod()\n        self._get_skill(skill)\n        if not (1 <= len(reason)', '        self._get_skill(skill)\n        if not (1 <= len(reason)')],
    "revoke reason optional": [(
        '        if not (1 <= len(reason) <= MAX_REASON):', '        if len(reason) > MAX_REASON:')],
    "revoked badge can be refreshed": [(
        '        if b.revoked:\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} Badge is revoked or burned")\n', '')],
    "refresh cooldown removed": [(
        '        if b.last_refresh_at != "" and now < _plus_secs(b.last_refresh_at, REFRESH_COOLDOWN_SECS):\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refresh cooldown: try again later")\n', '')],
    "refresh can downgrade": [(
        '            if level < current:\n                b.last_refresh_result = "lower_level"\n                return\n', '')],
    "expiry ignored": [(
        '        if now >= b.expires_at:\n            return False, "expired"\n', '')],
    "badge lifetime wrong": [(
        'BADGE_TTL_SECS = 365 * 24 * 3600', 'BADGE_TTL_SECS = 30 * 24 * 3600')],
    "missing clock guessed as valid": [(
        '            return None, "clock_unavailable"', '            return True, "ok"')],
    "serial not incremented": [(
        '        serial = int(sk.issued) + 1', '        serial = 1')],
    "wallet index duplicated on re-claim": [(
        '        if not self.in_wallet_index.get(sub, False):', '        if True:')],
    "disabled skill accepts claims": [(
        '        if not sk.enabled:\n            raise gl.vm.UserError(f"{ERROR_EXPECTED} This skill is not accepting claims")\n', '')],
    "pause ignored by claims": [(
        '        self._require_running()\n        sk = self._get_skill(skill)\n        if not sk.enabled', '        sk = self._get_skill(skill)\n        if not sk.enabled')],
    "moderators can edit host list": [(
        '        self._only_owner()\n        h = host.strip().lower()', '        self._only_mod()\n        h = host.strip().lower()')],
    "moderators can appoint moderators": [(
        '        self._only_owner()\n        self.moderators[str(user)] = enabled', '        self._only_mod()\n        self.moderators[str(user)] = enabled')],
    "anyone can accept ownership": [(
        '        if not self.has_pending_owner or gl.message.sender_address != self.pending_owner:', '        if False:')],
    "badge reported transferable": [(
        '        return False\n\n    @gl.public.view\n    def get_config', '        return True\n\n    @gl.public.view\n    def get_config')],
    "rubric left out of the prompt": [(
        'Grading rubric for this skill: {rubric}', 'Grading rubric for this skill: (none)')],
    "verify_skill ignores min level": [(
        '"valid": (valid and meets) if valid is not None else None,', '"valid": valid,')],
    "verify_skill accepts a bad time": [(
        '        if when != "" and not _valid_iso(when):', '        if False:')],
    "appeal queue lists resolved appeals": [(
        ' \\\n                    and self.submissions.get(sub, "none") == "appeal_pending":', ':')],
    "appeal queue lists superseded appeals": [(
        'int(self.appeal_seq.get(sub, u256(0))) == i', 'True')],
    "skill listing shows replaced serials": [(
        'and sub in self.badges and int(self.badges[sub].serial) == i:', 'and sub in self.badges:')],
    "comments not excluded from main content": [(
        '    for marker in COMMENT_MARKERS:\n        k = low_region.find(marker)\n        if k >= 0:\n            region = region[:k]\n            low_region = low_region[:k]\n', '')],
    "node clock only accepts one format": [(
        '    if rest not in ("", "Z", "z", "+00:00", "+0000", "+00"):', '    if rest not in ("Z",):')],
    "calendar dates not validated": [(
        '    if not (1 <= d <= _days_in_month(y, mo)):\n        return False\n', '')],
}

failures = 0
only = sys.argv[1] if len(sys.argv) > 1 else None
for name, reps in MUTANTS.items():
    if only and only not in name:
        continue
    text = ORIG
    ok = True
    for old, new in reps:
        if text.count(old) != 1:
            print(f"SKIP   {name}: pattern occurs {text.count(old)} times"); ok = False; break
        text = text.replace(old, new)
    if not ok:
        failures += 1
        continue
    d = tempfile.mkdtemp(prefix="sp_mut_")
    shutil.rmtree(d)
    shutil.copytree(SRC, d)
    open(os.path.join(d, "contracts", "SkillProof.py"), "w").write(text)
    out = subprocess.run([sys.executable, os.path.join(d, "tests", "offline", "run_offline.py"), d],
                         capture_output=True, text=True, cwd=d).stdout
    fails = [l for l in out.splitlines() if l.startswith("FAIL")]
    summary = [l for l in out.splitlines() if "passed" in l]
    status = "CAUGHT" if fails else "MISSED"
    if not fails:
        failures += 1
    print(f"{status:7} {name}: {summary[-1] if summary else 'no summary'}")
    for f in fails[:1]:
        print("         ", f[:110])
    shutil.rmtree(d, ignore_errors=True)

print("\nall mutants caught" if failures == 0 else f"\n{failures} mutant(s) survived or were skipped")
sys.exit(1 if failures else 0)
