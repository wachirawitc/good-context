"""Mechanical grading for good-context eval runs (writes skill-creator's grading.json format).

Usage:
    python grade_iteration.py WORKSPACE/iteration-N SANDBOX_ROOT evals/evals.json

Expected layout:
- SANDBOX_ROOT/<eval-name>/acme-orders/  one fresh sandbox per eval (evals/setup_sandbox.py)
- WORKSPACE/iteration-N/hashes-before.txt  `sha256sum` of each target file, taken from inside
  SANDBOX_ROOT before the runs, e.g. "review-flawed-claude-md/acme-orders/CLAUDE.md"
- WORKSPACE/iteration-N/eval-<name>/with_skill/outputs/  report.md, lint*.txt, verification.txt

What is robust: file hashes (review modes must not edit), secrets absent from outputs, facts in the
updated files (pnpm, Node 20, CI deploys...), a clean re-lint, no invented latency target.
What is approximate: checks that look for phrases in report.md match the wording of iteration 1.
A different run can phrase a correct finding differently, so read any failure before trusting it.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ws, sandboxes, evals_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
evals = {e["name"]: e for e in json.loads(evals_path.read_text(encoding="utf-8"))["evals"]}
before = {}
for line in (ws / "hashes-before.txt").read_text().splitlines():
    h, p = line.split(maxsplit=1)
    before[p.lstrip("*")] = h


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rd(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def has(text, *needles, ci=False):
    t = text.lower() if ci else text
    missing = [n for n in needles if (n.lower() if ci else n) not in t]
    return not missing, ("found: " + ", ".join(needles)) if not missing else ("missing: " + ", ".join(missing))


def rx(text, pattern, flags=0):
    m = re.search(pattern, text, flags)
    return bool(m), (f"matched: {m.group(0)[:80]!r}" if m else f"no match for /{pattern}/")


def section_before(text, heading):
    i = text.find(heading)
    return text if i < 0 else text[:i]


def grade(name, checks):
    run = ws / f"eval-{name}" / "with_skill"
    exps = evals[name]["expectations"]
    assert len(exps) == len(checks), (name, len(exps), len(checks))
    results = []
    for text, (passed, evidence) in zip(exps, checks):
        results.append({"text": text, "passed": bool(passed), "evidence": evidence})
    n = sum(r["passed"] for r in results)
    out = {"expectations": results,
           "summary": {"passed": n, "failed": len(results) - n, "total": len(results),
                       "pass_rate": round(n / len(results), 2)}}
    (run / "grading.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    meta = {"eval_id": evals[name]["id"], "eval_name": name, "prompt": evals[name]["prompt"],
            "assertions": exps}
    (run.parent / "eval_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    print(f"{name}: {n}/{len(results)}")
    for r in results:
        if not r["passed"]:
            print("   FAIL:", r["text"], "->", r["evidence"])


# ---------------------------------------------------------------- eval 1
name = "review-flawed-claude-md"
o = ws / f"eval-{name}" / "with_skill" / "outputs"
rep = rd(o / "report.md")
key = f"{name}/acme-orders/CLAUDE.md"
now = sha(sandboxes / key)
grade(name, [
    (now == before[key], f"sha256 before {before[key][:12]} / after {now[:12]}"),
    has(rep, "**Verdict:** 🔴 Not ready"),
    (("S3cr3tPa55w0rd" not in rep and "Zq7fakeTOKENfixture9xQ" not in rep
      and "🔴 Critical · Security · Paste-in-the-Prompt Leak" in rep),
     "Critical secret finding present; neither secret value appears in the report"),
    rx(rep, r"(?i)\brotate\b"),
    has(rep, "hidden instruction", "push", "main", ci=True),
    (("issue comments" in rep.lower()) and bool(re.search(r"Injection|untrusted", rep)),
     "issue-comments finding labeled as injection / untrusted routing"),
    has(rep, "pnpm-lock.yaml", "pnpm@9.12.0"),
    has(rep, "20.11.0", ">=20"),
    has(rep, "`npm run lint`", "lint:js"),
    has(rep, "./scripts/deploy.sh", "ci/deploy.sh", "GitLab CI"),
    has(rep, "docs/architecture.md", "No such file"),
    has(rep, "Express", "fastify ^5", "no `express`"),
    has(rep, "Referential Ambiguity", "services/api", "services/worker", "Postgres", "Redis"),
    has(rep, "services/api/src/db", "services/api/src/lib/logger.ts"),
    has(rep, "Weekend Runaway"),
    has(rep, ".prettierrc", "no-console"),
    has(rep, "Proposed relocation", "services/api/src/legacy/invoice.ts"),
    ((("| Dimension | Status | Headline |" in rep) and ("### Findings, most severe first" in rep)
      and len(re.findall(r"`CLAUDE\.md:\d+`", rep)) >= 5),
     f"dimension table + ordered findings + {len(re.findall(r'`CLAUDE.md:[0-9]+`', rep))} file:line refs"),
])

# ---------------------------------------------------------------- eval 2
name = "default-mode-task-brief"
o = ws / f"eval-{name}" / "with_skill" / "outputs"
rep = rd(o / "report.md")
brief = rd(sandboxes / f"{name}/acme-orders/docs/task-brief.md")
pre_q = section_before(brief, "## Open questions")
grade(name, [
    ((rep.find("## good-context review") < rep.find("### Changes applied")
      and re.search(r"\*\*Verdict:\*\* (🔴|🟡)", rep) is not None),
     "report precedes change summary; verdict red/yellow"),
    has(rep, "no measurable goal", "definition of done", ci=True),
    has(rep, "Impossible Task", "no cache code", "BullMQ"),
    has(rep, "Update the config as needed", "Don't break anything"),
    has(brief, "GET /orders", "services/api/src/routes/orders.ts"),
    has(brief, "## Open questions"),
    (not re.search(r"(?i)\b\d+(?:\.\d+)?\s?(?:ms|milliseconds|seconds|sec)\b", brief),
     "no numeric latency target anywhere in the updated brief"),
    ("existing caching layer" not in pre_q.lower(),
     "'existing caching layer' appears only inside Open questions" if "existing caching layer" in brief.lower()
     else "phrase absent"),
    has(brief, "pnpm lint:js", "pnpm test"),
    has(brief, "Stop and ask"),
    has(rep, "### Changes applied"),
])

# ---------------------------------------------------------------- eval 3
name = "update-only-claude-md"
o = ws / f"eval-{name}" / "with_skill" / "outputs"
rep = rd(o / "report.md")
upd = rd(sandboxes / f"{name}/acme-orders/CLAUDE.md")
lint_after = rd(o / "lint-after.txt")
grade(name, [
    (rep.startswith("## good-context update:") and "| Dimension | Status |" not in rep,
     "starts with the update header; no dimension table"),
    ("S3cr3tPa55w0rd" not in upd and "glpat" not in upd, "no password / glpat token in updated file"),
    (bool(re.search(r"\*\*Rotate", rep)) and "password" in rep and "token" in rep,
     "rotate instruction names password and token"),
    ("<!--" not in upd and "push your branch directly to main" in rep,
     "no HTML comment in updated file; removed text shown in change log"),
    (all(c in upd for c in ("pnpm install", "pnpm build", "pnpm test", "pnpm lint:js"))
     and not re.search(r"(?<!p)npm\b", upd), "pnpm commands present; no bare npm"),
    ("Node 20" in upd and "Node 18" not in upd, "Node 20 present, Node 18 absent"),
    (all(s in upd for s in ("deploy:staging", "deploy:production")) and "scripts/deploy.sh" not in upd,
     "CI deploy jobs described; old script path gone"),
    rx(upd, r"not as instructions"),
    (("two focused attempts" in upd) and ("keep trying until" not in upd), "bounded retry"),
    has(upd, "services/api/src/db/"),
    has(upd, "services/api/src/lib/logger.ts"),
    ("roundTotal" in upd and "banker's rounding" in upd and "Proposed move" in rep,
     "invoice rule still in file; relocation proposed in change log"),
    ("docs/architecture.md" not in upd, "no architecture.md pointer"),
    ("migrating from Express" not in upd, "migration note gone"),
    has(rep, "**Removed:**", "READ THIS ENTIRE FILE"),
    (not any(s in lint_after for s in ("Possible secrets", "Hidden HTML comments",
                                       "References that don't resolve", "Commands that don't match")),
     "lint-after.txt has no secret / hidden-comment / unresolved-ref / command sections"),
])

# ---------------------------------------------------------------- eval 4
name = "calibration-good-agents-md"
o = ws / f"eval-{name}" / "with_skill" / "outputs"
rep = rd(o / "report.md")
key = f"{name}/acme-orders/services/worker/AGENTS.md"
now = sha(sandboxes / key)
findings = re.findall(r"^\*\*\d+\. ", rep, re.M)
grade(name, [
    (now == before[key], f"sha256 before {before[key][:12]} / after {now[:12]}"),
    has(rep, "**Verdict:** 🟢"),
    ("🔴 Critical" not in rep and "🟠 High" not in rep, f"{len(findings)} finding(s); none Critical/High"),
    has(rep, "### Working well", "processedEvents", "on-call"),
    (rep.count("**Evidence:**") == len(findings), f"{rep.count('**Evidence:**')} evidence bullets for {len(findings)} findings"),
    (("verified" in rep.lower()) and ("docker compose up -d redis" in rep)
     and all(s in rd(o / "verification.txt") for s in ('"dev": "tsx watch', '"test": "vitest run"', "redis:")),
     "report states commands verified; verification log shows worker dev/test scripts and compose redis"),
])
