# File types: what belongs where

Context quality is relative to location. The paper's example: a sentence that is noise in a root AGENTS.md becomes exactly right as a comment in the file it describes. "Nothing about the words changed; only their location did." So before judging content, settle what kind of file this is, who loads it, and how often. Then judge each line against *that* reader.

Contents:
1. Always-loaded instructions
2. Scoped instructions (nested and path-scoped)
3. Skills, commands, and subagents
4. Task briefs, specs, and prompts
5. Reference docs (README, architecture, ADRs, runbooks, glossaries)
6. Memory and notes
7. Where misplaced content belongs (relocation guide)
8. Several tools, one repo
9. Ownership and review

If the name doesn't reveal the role, infer it from content and from who references the file. Grep the repo for the file name: an `@import` from CLAUDE.md makes it always-loaded; a reference from application code makes it a production prompt; a link from a README makes it a reference doc.

Tool loading rules change between versions. When a finding depends on exactly how a tool loads a file, say which behavior you're assuming.

---

## 1. Always-loaded instructions

**Examples:** project `CLAUDE.md` (root or `.claude/CLAUDE.md`), personal project files such as `CLAUDE.local.md`, user-level `~/.claude/CLAUDE.md`, root `AGENTS.md`, root `GEMINI.md`, `.github/copilot-instructions.md`, `.cursorrules` and Cursor rules with `alwaysApply: true`, `.windsurfrules`, rules files with no path scope, anything pulled in by an `@import` from these.

**Reach:** every session. A user-level file reaches every session in *every* project. Every line is paid for in every session, and every line competes for attention with the task at hand. This is the strictest bar for Efficiency and Fidelity: a false line here misleads every session, not one.

**Belongs:**
- What the project is, in a line or two, if the repo doesn't make it obvious.
- A map of only the non-obvious parts: where the API, worker, and shared code live; generated directories not to edit.
- Verified build, test, lint, and typecheck commands, especially per-package ones and anything that differs from the default (`pnpm --filter @acme/api test`, not "run the tests").
- What to run before declaring a task done.
- Conventions that *aren't* enforced by a tool and that the agent would plausibly get wrong, each with its reason.
- Hard constraints and off-limits areas, each with what to do instead and why.
- Gotchas that have bitten people repeatedly.
- Pointers to deeper docs, by path, with when to read each one ("before changing the schema, read `docs/data-model.md`").

**Doesn't belong:**
- Generic advice ("write clean code", "handle errors properly") and personas ("You are an expert…").
- Style rules a formatter or linter already enforces; point to the tool instead.
- Descriptions of every directory or file, which the agent can discover by listing.
- Rules for one file or one subtree (move them to section 2 or a code comment).
- Rarely needed procedures such as releases, migrations, or incident handling (move them to a skill or runbook, with a pointer).
- History, changelogs, and finished migrations.
- Secrets, real customer data, internal hostnames with credentials.
- Personal preferences in a shared file (move them to a personal file).
- Long code samples and copies of the README (point to them instead).
- `@imports` used to "move content out". Imports load eagerly at startup, so they cost the same tokens. An import is fine only when the imported content is needed every session anyway, for example CLAUDE.md importing AGENTS.md to keep a single source of truth.

**Extra checks:**
- Run every command against the manifests, scripts, Makefile, and CI.
- Check every path.
- Check consistency with neighbor files (README, nested instruction files, other tools' instruction files).
- Measure size. There's no universal limit; ask of each line, "would an agent make a mistake without this?"
- Check the order: the rules that matter most should come first, not at item 23.

**User-level files** (`~/.claude/CLAUDE.md` and equivalents) should hold only cross-project personal preferences. Anything that mentions a specific repo, path, or stack belongs in that project. Treat organization-managed policy files as review-only: report the findings and propose changes to their owners.

## 2. Scoped instructions (nested and path-scoped)

**Examples:**
- `services/api/CLAUDE.md` and nested `AGENTS.md` / `GEMINI.md`
- Claude Code rules with a `paths:` scope
- Copilot `.github/instructions/*.instructions.md` with `applyTo:`
- Cursor rules with `globs:` (auto-attached) or a `description:` (agent-requested)
- Windsurf rules with glob activation

**Reach:** sessions that touch the matching files. Depending on the tool, these load in addition to the root file (nested files are often read when the agent first touches that subtree). For AGENTS.md, the nearest file in the tree takes precedence.

**Belongs:** subtree-specific commands (`cd services/worker && pnpm test`), local conventions, local gotchas, the local map.

**Doesn't belong:** repeats of root-level content (duplicates drift into contradictions), and rules for code outside this scope.

**Extra checks:**
- Make sure the scope actually matches files. A glob or `applyTo` pattern that matches nothing is dead context; one that matches everything is an always-loaded file in disguise.
- Check for contradictions with the root file. When a subtree truly differs, say so explicitly ("unlike the rest of the repo, this package uses Jest").
- Check that the content fits the location.

## 3. Skills, commands, and subagents

**Examples:** `SKILL.md` (plus its `references/`, `scripts/`, `assets/`), custom slash commands (`.claude/commands/*.md`, Copilot `.prompt.md` files), subagent definitions (`.claude/agents/*.md`).

**Reach is split, and the review bar follows the split:**
- The **name and description** (frontmatter) of skills and subagents are in context in every session, because they're how the agent decides whether to use them. Give them the always-loaded bar: precise, compact, true.
- The **body** loads only when the skill triggers, the command runs, or the subagent starts. Review it like a brief that gets reused: strict on Actionability, moderate on Efficiency.
- **Bundled references** load on demand. They can be long, provided the body says when to read each one.

**Belongs:**
- A description that says what the skill does *and when to use it*, in the words users actually say.
- In the body: the workflow, the decision points and the reasoning behind them, what "done" looks like, output formats when something downstream depends on them, and pointers to bundled files with when to read each.

**Doesn't belong:**
- Descriptions so broad they trigger on everything, or so narrow they never trigger.
- Content duplicated between the body and its references.
- Generic instructions the model follows anyway.
- Sprawling procedures that should be a bundled script. Deterministic steps belong in code the agent runs, not prose it re-derives.

**Extra checks:**
- Bundled paths resolve relative to the skill directory. Paths the skill *creates* at runtime (output folders, generated files) aren't broken references.
- Frontmatter is valid for the tool, and the description doesn't overlap with other installed skills (overlap is a Clarity problem: the agent can't tell which to use).
- Commands use their argument placeholders (`$ARGUMENTS`) correctly.
- **Least privilege** (Security): tool allowlists (`allowed-tools`, a subagent's `tools:`) grant no more than the job needs.
- **Subagents start cold.** A subagent doesn't see the main conversation, so its body plus the delegation message is *all* of its context. Check that it states the goal, the done criteria, and the shape of what to return.

## 4. Task briefs, specs, and prompts

**Examples:**
- task briefs and specs: `docs/task-*.md`, `spec.md` / `plan.md` / `tasks.md` in spec-driven workflows, PRDs
- prompts and issue bodies handed to an agent
- prompt files that application code sends to a model in production

**Reach:** one task (or one prompt template used many times). The reader often can't ask: background and async agents run unattended, and even interactive ones fill gaps rather than ask. Use the strictest bar for Actionability and Clarity and a lighter one for Efficiency.

**Belongs:** the senior-engineer brief.
1. The goal, and why it matters.
2. How you'd know it's solved: a checkable definition of done.
3. What's off limits, and why.
4. Where the relevant code lives: exact paths, verified.
5. When to stop and come back: budgets, ambiguity, risky actions.

Add known pitfalls and examples of expected input and output where they help. Add an **Open questions** section when the author still has to decide something. The brief isn't ready until those are answered, and an agent that sees them will ask instead of guessing.

**Doesn't belong:**
- Repo-wide conventions (the instruction files already carry them).
- Micro-steps for things the agent does well unguided (Overspecification).
- Pasted secrets and more customer data than the task needs.

**Extra checks:**
- Is any premise false? "Use the existing caching layer" when none exists is an Impossible Task.
- Is the goal a proxy without its intent (Goal Drift)?
- Does long-running work have a budget (Weekend Runaway)?

**Production prompts:**
- Strict output formats are justified when code parses the output; that's not Overspecification.
- Security dominates. Keep instructions clearly separated from user-supplied or retrieved content. Never place secrets in a prompt (assume a prompt can be extracted). Tell the model what to do with instructions that appear inside data.

## 5. Reference docs

**Examples:** `README.md`, `CONTRIBUTING.md`, architecture and design docs, ADRs (architecture decision records), runbooks and playbooks, glossaries, API docs, onboarding guides.

**Reach:** read on demand, by people *and* agents. An agent often opens the README first. Efficiency is judged for all readers. Don't strip onboarding content humans need just because an agent could infer it.

**Belongs:** accurate, current facts, the "why" behind structure and decisions, and pointers to the source of truth (schemas, configs, code) rather than copies of it.

**Doesn't belong:** stale "currently…" statements, copies of configs that drift, secrets, and agent-only instructions (they belong in an instruction file or skill).

**Type-specific notes:**
- **ADRs are history by design.** An accepted ADR records what was decided then. Don't "fix" its staleness by rewriting the decision; mark it *Superseded by ADR-NNN* and point to the current one. The same applies to changelogs, release notes, and meeting notes. Staleness findings apply only to text that claims to describe the present.
- **Runbooks** are read under pressure, and their steps get executed.
  - Verify every command.
  - Name the environment explicitly at every step; "the database" in a runbook is Referential Ambiguity with a production blast radius.
  - Put explicit confirmations before destructive steps, and never include credentials.
- **Glossaries** are the right home for team-local terms (ERP names, internal acronyms) that would otherwise be redefined in every instruction file.
- **Architecture docs:** spot-check the claims against the code; a confident but outdated diagram is Stale Guidance at its most persuasive.

## 6. Memory and notes

**Examples:**
- auto-memory directories (a `MEMORY.md` index plus topic files)
- session handoff notes such as `NOTES.md` and `progress.md`
- personal scratch notes

**Reach:** usually one person. But memory indexes are often loaded every session (sometimes truncated after a fixed length), and memories are replayed later as trusted context. A wrong memory is a hallucination that persists.

**Belongs:** durable facts, preferences, and decisions, with absolute dates. Things that *aren't* derivable from the repo.

**Doesn't belong:** relative dates ("last week"), things the repo or git history already records, secrets, and one-off details that only mattered in one conversation.

**Extra checks:**
- Do the files, flags, and functions a memory names still exist?
- Do any entries contradict each other?
- Is the index terse, one line per entry, with details in topic files?

Personal notes need less polish, but Fidelity and Security apply in full.

## 7. Where misplaced content belongs (relocation guide)

| Content | Better home | Why |
|---|---|---|
| A rule about one file or function ("rounding in `invoice.ts` must stay banker's rounding") | A comment at the top of that file or function | Read exactly when someone edits it |
| Conventions for one package or subtree | A nested CLAUDE.md or AGENTS.md, or a path-scoped rule | Loaded only when that code is touched |
| A rarely needed procedure (release, migration, incident) | A skill or a runbook, plus a one-line pointer | Costs nothing until it's needed |
| Team-local terms and acronyms | A glossary, or a definition where they're used most | Defined once |
| Background, history, rationale | An ADR or architecture doc | Keeps instruction files about the present |
| Personal preferences | `~/.claude/CLAUDE.md` or a gitignored local file | Doesn't impose on teammates |
| Formatting and style rules | Formatter or linter config | Enforced instead of hoped for |
| Secrets | A secret manager or env var, referenced by *name* | Never belongs in context |
| Details of one task | The task brief or issue | Keeps instruction files task-agnostic |
| Facts the agent can discover in a second (file listings, dependency lists) | Nowhere: delete | Pure noise |

**What a good pointer looks like:** "Release process: see `docs/release.md` (read before tagging a release)." It names the path and says when to read it. A pointer without the "when" is half a pointer: the agent can reach the document but can't tell when it should.

Remember the rule from SKILL.md: only the target file is yours to edit without asking. Propose each relocation with its destination and exact text, and carry it out only after the user agrees.

## 8. Several tools, one repo

Many repos carry several instruction files for different tools, such as CLAUDE.md, AGENTS.md, `.github/copilot-instructions.md`, and Cursor rules. They tend to start as copies and then drift into Contradictory Context, so different agents learn different "facts" about the same repo. When you find overlapping files:
- report the contradictions between them
- suggest a single source of truth, such as AGENTS.md, that the others reference. CLAUDE.md can `@AGENTS.md`, which is an appropriate import because the content is needed every session anyway. Symlinks also work.
- keep tool-specific additions short and in the tool's own file

## 9. Ownership and review

Shared context decays unless someone owns it. For shared reference docs and instruction files, suggest:
- **An owner:** a team, not one person, so ownership survives reorganizations.
- **A review cadence** matched to how fast the subject changes: runbooks after every incident that used them, architecture docs whenever the architecture changes, instruction files whenever the toolchain changes.
- **A "Last reviewed" date** for reference docs, or code-owner review for instruction files. Instruction files steer every agent session. A pull request that quietly edits AGENTS.md changes the behavior of every agent in the repo, so it deserves the same review as code (that's Security as well as Fidelity).
- **Automation where possible:** generate copied facts from their source, or add a CI check that the commands in the instruction file still exist.

Scale the effort to reach: a personal scratch note doesn't need an ownership model.
