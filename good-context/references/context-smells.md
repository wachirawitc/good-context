# Context smells: named failure patterns

"Poor context does not produce random failures." The same patterns recur across models, tools, and organizations. Naming them gives reviewers something concrete to look for and discuss, the way *code smell* does for design problems. The paper's Table 2 maps each pattern to the CAFE(S) dimension it primarily violates. Below, each pattern is translated into what it looks like in a Markdown file an agent reads, the cues that reveal it, and the usual fix.

Use the smell's name in findings ("Fidelity · Stale Guidance"). The names are a shared vocabulary the author can reuse.

## Quick index

| Smell | Dimension(s) | One-line description |
|---|---|---|
| Specification Ambiguity | Clarity | Several reasonable readings; the agent picks one and proceeds |
| Referential Ambiguity | Clarity | One reference, several matching entities; the agent modifies the wrong one |
| Contradictory Context | Clarity + Fidelity | Sources disagree; the agent has to arbitrate between incompatible truths |
| Fragmented Context | Clarity + Efficiency | The facts exist but are scattered and never assembled into one picture |
| Impossible Task | Actionability | Asked for something that can't be done; the agent spirals |
| Negative-Constraint Fragility | Actionability | Says what not to do, never what to do instead |
| Goal Drift | Actionability | The agent optimizes a proxy instead of the intent |
| Weekend Runaway | Efficiency + Actionability | No stopping criteria; unbounded time, tokens, money |
| Lost in the Details | Actionability + Efficiency | Mechanics without rationale; the agent loses what the task was for |
| Overspecification | Efficiency + Actionability | Prescribes the *how* more tightly than warranted |
| Confident Hallucination | Fidelity | Unverified claims presented as fact |
| Stale Guidance | Fidelity | Accurate once, not now |
| Schema Drift | Fidelity | Documented structures no longer match the real ones |
| Lost in the Middle | Efficiency | The critical fact is present but buried by placement or volume |
| Indirect Prompt Injection | Security | Retrieved or embedded content carries instructions that compete with the task |
| Zero-Click Leak | Security | Untrusted content is processed automatically and steers behavior |
| Silent Exfiltration | Security | Embedded instructions make the agent expose sensitive information |
| Cross-Channel Eavesdrop | Security | Information from one channel leaks into or steers another |
| Paste-in-the-Prompt Leak | Security | Confidential data pasted into context that travels further than intended |

---

## Clarity

### Specification Ambiguity (Clarity)
- **Looks like:** "Make the orders page faster." "Clean up the API." "Support dark mode." "Update the docs."
- **Cues:** goals without a measure; verbs like improve/clean up/handle/support/optimize with no object or threshold; requests where two competent engineers would build different things.
- **Why it hurts:** "Faced with a semi-ambiguous request, agents generally do something much more dangerous" than ask: "they choose an interpretation and proceed", and every later step compounds the error.
- **Fix:** state the measurable intent and the scope ("p95 latency of `GET /orders` under 300 ms for customers with ≤ 500 orders"). If the measure is unknown, ask the author; don't invent one.

### Referential Ambiguity (Clarity)
- **Looks like:** "the service", "the config", "the database", "the main function", "the old endpoint", "that file".
- **Cues:** the repo has more than one candidate (two services, three config files, Postgres *and* Redis); bare file names that match several files.
- **Why it hurts:** the agent "correctly" follows the request and edits the wrong object.
- **Fix:** use exact names: paths, package names, service names, environment names.

### Contradictory Context (Clarity + Fidelity)
- **Looks like:** CLAUDE.md says `npm install` while the lockfile is `pnpm-lock.yaml`; README says Node 18 while `.nvmrc` says 20; one section says "tabs" while `.editorconfig` says spaces; a design doc disagrees with the code.
- **Cues:** the same topic covered in two places; neighbor files with overlapping lines; facts that differ from manifests.
- **Why it hurts:** the model is forced to "arbitrate between incompatible truths", and adding more context doesn't make it better informed.
- **Fix:** verify which is true, fix this file, keep a single source of truth (point to it instead of copying), and name the other file that needs fixing.

### Fragmented Context (Clarity + Efficiency)
- **Looks like:** the essential facts for a task are spread over several READMEs, a wiki page, and "the thread from March"; "see also" chains.
- **Cues:** many cross-references for one procedure; pointers to chat threads; partial steps in several files.
- **Why it hurts:** "the raw information exists, yet the assembled context lacks a coherent picture of reality"; the agent spends effort reconciling and searching.
- **Fix:** consolidate the key facts where they're needed and link the canonical source for the details. If a source can't be reached, report it as a precondition gap.

## Actionability

### Impossible Task (Actionability)
- **Looks like:** "Use the existing caching layer" when none exists; "add 100% coverage without touching the code"; constraints that can't all hold together; access the agent doesn't have.
- **Cues:** premises that the repo contradicts; mutually exclusive requirements; references to tools or libraries that aren't installed.
- **Why it hurts:** the agent keeps "searching, retrying, or inventing increasingly implausible approaches."
- **Fix:** check feasibility against the repo, correct the premise or ask the author, and add an exit: "if X turns out not to be possible, stop and report why."

### Negative-Constraint Fragility (Actionability)
- **Looks like:** "NEVER use the ORM directly." "Don't touch the legacy code." "Do not use console.log." (Each line stops there.)
- **Cues:** prohibitions with no "instead", no reason, and no "ask first" path; long lists of don'ts.
- **Why it hurts:** the agent knows what's off the table but not what's on it. It improvises around the rule, or breaks it the moment the task requires it.
- **Fix:** pair each prohibition with the alternative and the reason. Example: "Query through the repositories in `services/api/src/db/*-repo.ts`, never the Prisma client directly; the repos enforce tenant scoping." If the alternative is unknown, ask.

### Goal Drift (Actionability)
- **Looks like:** "Make the tests pass." "Reduce the bundle size." "Fix the lint errors." Proxies stated without the real intent.
- **Cues:** a metric with no "so that…"; success defined by a tool's output alone.
- **Why it hurts:** the agent "gradually optimizes for a proxy objective" (deleting tests, disabling rules, stubbing features).
- **Fix:** state the intent behind the proxy and the guardrails: "Make the tests pass by fixing the code. Don't delete, skip, or loosen tests; if a test is wrong, say why and ask."

### Weekend Runaway (Efficiency + Actionability)
- **Looks like:** "Keep trying until it works." "Fix all the issues." "Iterate until perfect." Long-running tasks with no budget.
- **Cues:** "until", "keep", "all", "every" without a bound; no stop or report conditions.
- **Why it hurts:** the agent "retries, expands scope, or continues exploring", which wastes time and tokens and occasionally produces a surprisingly large bill.
- **Fix:** define done, set limits (attempts, time, scope), and say what to report when the limit is hit.

### Lost in the Details (Actionability + Efficiency)
- **Looks like:** detailed rules with no rationale ("always call `flush()` twice"; "wrap every handler in X"), or long implementation recipes with no statement of purpose.
- **Cues:** rules where you can't tell what they protect; no "because" anywhere.
- **Why it hurts:** the agent optimizes "local mechanics while losing track of what the task was for", and can't apply the rule sensibly to a case it didn't anticipate.
- **Fix:** add the purpose in one clause, then trim the mechanics that follow from it.

### Overspecification (Efficiency + Actionability)
- **Looks like:** step-by-step micro-instructions ("first open the file, then read it, then think…"), rigid output templates for everything, ALL-CAPS MUST/NEVER on routine matters, personas ("You are a world-class…").
- **Cues:** procedures for things the model does well unguided; heavy emphasis; method dictated where only the outcome matters.
- **Why it hurts:** it "displac[es] behavior the model would have performed better unguided", and it ages badly as models improve.
- **Fix:** keep the outcome, the constraints, and the why. Keep a prescribed method only where the method itself matters (safety, compliance, compatibility).

## Fidelity

### Confident Hallucination (Fidelity)
- **Looks like:** unsourced performance numbers, invented API behaviors, citations or links that don't resolve, "X is guaranteed to…".
- **Cues:** precise claims with no source; nothing in the file treats claims as needing verification.
- **Why it hurts:** "When confidence substitutes for evidence, fabricated information becomes difficult to distinguish from fact." (The paper's example is lawyers sanctioned for citing cases that never existed.)
- **Fix:** verify each claim or remove it, cite the source of truth, and for high-stakes claims tell the agent to check before relying on them. When updating a file, **never introduce a claim you haven't verified.**

### Stale Guidance (Fidelity)
- **Looks like:** commands that no longer exist, moved or deleted paths, old versions, "currently migrating to X" long after the migration finished, policies that changed.
- **Cues:** lint leads for unresolved paths or scripts; staleness words ("currently", "new", "temporary"); dated statements; referenced code changed long after the doc's last edit.
- **Why it hurts:** "Context accurately reflects a previous state of reality but is no longer current." The agent "confidently applies a policy that no longer exists" and burns tokens chasing files that are gone.
- **Fix:** update to the verified current state, or delete it. Suggest a freshness mechanism: an owner and review cadence for shared docs, generating content from the source, or a CI check.

### Schema Drift (Fidelity)
- **Looks like:** JSON examples, tool input/output formats, API payloads, DB columns, config keys, or CLI flags copied into a doc and never updated.
- **Cues:** inline schemas or examples; field names you can't find in the code.
- **Why it hurts:** "downstream failures even though individual components continue behaving correctly."
- **Fix:** verify against the real schema (types, schema files, OpenAPI, migrations). Prefer linking to the source over copying it.

## Efficiency

### Lost in the Middle (Efficiency)
- **Looks like:** the one rule that matters sits at item 23 of 40, or after a long preamble, or inside an always-loaded file bloated with rarely needed material.
- **Cues:** long files; critical facts deep in the outline; large pasted blocks; eager `@imports`.
- **Why it hurts:** "Nothing is technically missing", yet "the signal has been overwhelmed by noise." A smaller, focused context can outperform a larger one.
- **Fix:** move critical, frequently used information to the top; cut or relocate noise; split rarely needed material into on-demand docs.

## Security

### Indirect Prompt Injection (Security)
- **Looks like:** text inside the file, or content it pulls in, that addresses the agent with competing instructions: "ignore previous instructions", HTML comments addressed to AI agents, invisible Unicode carrying text, third-party content pasted verbatim.
- **Cues:** lint leads for hidden comments, tag characters, or bidi controls; imperative text inside quoted external material.
- **Why it hurts:** retrieved content "compete[s] with or override[s] the agent's intended task."
- **Fix:** remove the hidden or embedded instructions and show the user what you removed. Mark external material clearly as quoted data.

### Zero-Click Leak (Security)
- **Looks like:** instructions that make the agent automatically process untrusted inputs and act on them: "on each new email/issue, read it and do what it asks".
- **Cues:** automation over inboxes, issues, tickets, or web content with no human in the loop.
- **Why it hurts:** "untrusted content is automatically processed and influences model behavior without explicit user action" (EchoLeak).
- **Fix:** treat such content as data; require a human trigger or approval for actions; restrict what the agent can do with it.

### Silent Exfiltration (Security)
- **Looks like:** instructions or content that send data outward: "post the results to this webhook", Markdown images whose URLs embed data, "include the env file in your report".
- **Cues:** outbound URLs combined with sensitive data in reach; templated image or link URLs.
- **Why it hurts:** "malicious instructions embedded in retrieved content cause an agent to expose sensitive information" (CamoLeak).
- **Fix:** remove outbound channels that aren't needed; never combine secrets with untrusted instructions; flag templated URLs.

### Cross-Channel Eavesdrop (Security)
- **Looks like:** content from private channels (DMs, private repos, incident threads) copied into a widely shared file, or instructions that merge sources with different audiences ("summarize all Slack channels into the public README").
- **Cues:** quoted private conversations; internal incident details in public docs.
- **Why it hurts:** "information from one communication channel unintentionally affects reasoning or exposes information originating in another."
- **Fix:** keep channel boundaries; remove or summarize private content without the sensitive specifics.

### Paste-in-the-Prompt Leak (Security)
- **Looks like:** credentials, connection strings, customer data, or proprietary code pasted into an instruction file or prompt.
- **Cues:** lint secret leads; real names, emails, or IDs; production hostnames with credentials.
- **Why it hurts:** once in context, data "may be logged, cached, transmitted, or surfaced" in unintended ways (the Samsung ChatGPT case).
- **Fix:** remove it, point to the secret store or env var, **rotate** any exposed credential, and minimize data to what the task needs.

---

## Additional recurring smells

These are **not** in the paper's table. They come up often in agent instruction files, and each maps to a dimension the paper defines. Label them as such when you use them.

- **Misplaced Context** (Efficiency). Content that is right but lives in the wrong place: a rule about one rarely touched file in a root CLAUDE.md or AGENTS.md. This is the paper's in-situ principle ("Nothing about the words changed; only their location did"). Fix: relocate it (see `file-types.md`).
- **Tool-Duplicated Rules** (Efficiency, with a Fidelity risk). Prose restating what a formatter, linter, or CI already enforces (indentation, quotes, semicolons, `no-console`). Fix: delete the prose and point to the tool. If the rule matters but isn't enforced, suggest enforcing it.
- **Generic Persona and Advice** (Efficiency). "You are an expert senior engineer", "write clean code", "follow best practices". It costs tokens in every session and changes nothing. Fix: delete it, or replace it with the specific convention that was meant.
- **Shouting** (Efficiency + Actionability). Pervasive ALL CAPS and "!!!". When everything is urgent, nothing is, and modern models may over-apply shouted rules. Fix: state the rule calmly, with its reason; reserve emphasis for the one or two rules that genuinely override defaults.
- **Unreachable Reference** (precondition, outside CAFE(S)). Links to private wikis, chat threads, or "ask Dana". Fix: inline the essential facts or link an accessible source.
