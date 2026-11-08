# good-context

A Claude Code skill that reviews and repairs the Markdown files AI agents read: `CLAUDE.md`, `AGENTS.md`, `SKILL.md`, Copilot/Cursor rules, prompts, task briefs, specs, READMEs, architecture docs and runbooks.

It applies the **CAFE(S)** context-quality framework from *CAFE(S): Your Agent Is Only As Good As Its Context* (Houck, Kanat-Alexander, Kalliamvakou, Storey & Forsgren, *ACM Queue*, 2026): <https://queue.acm.org/doi/10.1145/3847288>.

| Property | The question it asks |
|---|---|
| **Clarity** | Can the agent interpret it as intended? |
| **Actionability** | Can the agent proceed, and know when it is done? |
| **Fidelity** | Can the agent trust that it is true? |
| **Efficiency** | Can the agent focus on what matters? |
| **(S)ecurity** | Should the agent have this at all? |

## Install

Claude Code loads personal skills from `~/.claude/skills/`. Clone the repo and copy the skill directory there:

```sh
git clone https://github.com/wachirawitc/good-context.git
cd good-context
mkdir -p ~/.claude/skills
cp -r good-context ~/.claude/skills/
```

On Windows PowerShell, the copy step is:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse good-context "$env:USERPROFILE\.claude\skills\"
```

To make the skill available only inside one project, copy it to that project's `.claude/skills/` instead.

The installed skill is a copy, so re-run the copy after pulling updates or editing anything under `good-context/`. Start a new Claude Code session afterwards so the skill is picked up.

## Usage

| Invocation | Mode | Output |
|---|---|---|
| `/good-context @path/to/file.md` | review + update | review report, then the fixes, then a change summary |
| `/good-context --review @path/to/file.md` | review only | review report; no file is modified |
| `/good-context --update @path/to/file.md` | update only | the fixes and a compact change log |

The skill also triggers on plain requests such as "audit my CLAUDE.md" or "why does the agent keep ignoring this rule?".

### Linter

The skill runs a bundled linter that collects mechanical evidence (unresolved paths, unknown commands, version drift, possible secrets, hidden text, vague wording, duplication). It needs Python 3.8+ and only the standard library, and can be run on its own:

```sh
python good-context/scripts/context_lint.py path/to/CLAUDE.md [--repo-root DIR] [--json] [--max-items N]
```

Its output is a list of leads to confirm, not verdicts.

## Repository layout

```
good-context/
  SKILL.md                    skill definition and workflow
  references/
    cafes-framework.md        definitions, checklists, fix patterns, severity
    context-smells.md         named failure patterns with detection cues and fixes
    file-types.md             what each kind of agent-facing file should contain
  scripts/context_lint.py     mechanical checks
  evals/                      evaluation suite (see below)
```

## Evals

`good-context/evals/evals.json` defines four evals that run the skill against `evals/files/acme-orders`, a small fixture repo with deliberately flawed instruction files:

- `review-flawed-claude-md`: `--review` on a flawed `CLAUDE.md`
- `default-mode-task-brief`: default mode on `docs/task-brief.md`
- `update-only-claude-md`: `--update` on the flawed `CLAUDE.md`
- `calibration-good-agents-md`: `--review` on a healthy `AGENTS.md`, to check the skill does not invent findings

Each eval needs a fresh sandbox:

```sh
python good-context/evals/setup_sandbox.py <dir>   # creates <dir>/acme-orders
```

`setup_sandbox.py` renames the `*.sample` files to `CLAUDE.md`/`AGENTS.md`, injects a fake token at runtime and builds a git history with old instruction files and newer code. The fixtures are stored as `.sample` so agents working in this repo don't load them, and no secret-shaped string is committed.

`good-context/evals/grade_iteration.py` grades a run in skill-creator's `grading.json` format; its docstring describes the expected workspace layout. Run output goes in `good-context-workspace/`, which is git-ignored.
