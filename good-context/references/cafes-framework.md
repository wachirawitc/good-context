# CAFE(S): definitions, review checklists, fix patterns

Source: B. Houck, M. Kanat-Alexander, E. Kalliamvakou, M.-A. Storey, N. Forsgren, "CAFE(S): Your Agent Is Only As Good As Its Context", *ACM Queue*, 24 Sept 2026. Quoted phrases below come from the paper; the checklists and fix patterns turn it into review practice for Markdown files.

## Contents
1. Where CAFE(S) sits
2. What "good context" means
3. Preconditions (outside CAFE(S))
4. Clarity
5. Actionability
6. Fidelity
7. Efficiency
8. Security
9. Classifying findings
10. Calibration

---

## 1. Where CAFE(S) sits

**Intent → Context → Harness → Model.**
- *Intent*: what a person wants to accomplish.
- *Context*: the information that represents the task, its constraints, and the surrounding knowledge.
- *Harness*: orchestration, retrieval, tools, memory, execution logic.
- *Model*: the underlying intelligence.

CAFE(S) evaluates the translation from intent to context: whether the context "faithfully represents what a human is actually trying to accomplish." It is not a model evaluation, a harness design, or a retrieval architecture. It is a quality lens on the *assembled* context, regardless of how that context was built.

Everything an agent reads is context, and any of it can be taken "as instruction or as fact": a prompt, a code comment, an architecture document, a README, a checked-in spec. If it's stale or ambiguous, it can send the agent down a wrong path, and an expensive one.

## 2. What "good context" means

"Good context is defined by what it enables": it lets a human–agent system do its task *correctly, efficiently, and safely*. It gives the agent enough to **reason instead of guess**, grounds it in current and trustworthy information, keeps its attention on what matters, and doesn't expose information it should never have had.

The practical test is the **competent colleague**. Before handing anything to an agent, ask what a capable person would need to do the same task well:
- understand the goal
- have the relevant background
- know the constraints
- have some way to recognize that the work is correct

Now suppose that colleague "could not easily lean over and ask a follow-up question." Whatever they'd need to ask is missing from the context.

## 3. Preconditions (outside CAFE(S))

Before CAFE(S) applies, the information must:
1. be **accessible**, because "the most common context problem today is not that context is low quality but that the agent cannot reach it";
2. be **findable**: the agent can cut through the noise to the relevant slice;
3. **exist**: much knowledge "lives in hallway conversations, unrecorded meetings, and private messages", and "no amount of context engineering can retrieve what was never captured."

In a file review, precondition gaps look like this:
- links to resources agents can't open (private wikis, Slack threads, Google Docs)
- references to unwritten knowledge ("the usual process", "as discussed", "ask Dana")
- a file sitting where its consumer never loads it (wrong filename or casing, wrong directory)

Report these separately as precondition gaps. Don't force them into a dimension.

---

## 4. Clarity: can the agent interpret the request as intended?

**Definition.** Context is "unambiguous for the task at hand and for the party that has to act on it." Clear context "resolves the same way for the author and the agent."

**Scope.** Clarity is required only where it affects the work. "A term the task never touches can stay loose. A term the task turns on is different." If the context doesn't settle which system, environment, or policy is meant, "the agent will settle it for you, plausibly and silently."

**Why it fails.** Ambiguity is "invisible to the author", who already knows what they meant. Teams develop local vocabularies, and "a term that is precise inside one group can admit several readings outside it." Language, domain, and culture shape what counts as obvious, "and an agent shares none of them by default."

**Consequence.** "Avoidable variation": different runs take different readings. With a semi-ambiguous request, agents "choose an interpretation and proceed", and if that first assumption is wrong, every later step compounds the error.

**Review checklist**
- Does every term the task turns on resolve one way? That includes systems, services, environments ("prod", "staging"), files, policies, teams, and people.
- Referential ambiguity: "the service", "the config", "the database", "the API", "the script", "the old endpoint", "the main file". Does the repo contain more than one candidate?
- Team-local vocabulary, codenames, and acronyms used without a definition.
- Vague qualifiers on things that matter: "fast", "small", "properly", "as needed", "appropriate", "etc.".
- Quantifiers: "all", "every", "the whole codebase". Is that literal?
- Conditions with fuzzy triggers: "for big changes…" (how big?), "if it's risky…" (by what measure?).
- Unclear subject: is a sentence a rule for the agent, or a description of what humans do?
- Contradictions inside the file (also a Fidelity issue).

**Fix patterns**
- Name the thing exactly: path, package name, service name, environment, ticket ID.
- Define a local term once, at first use or in a short glossary.
- Replace a vague qualifier with a threshold or an example ("p95 under 300 ms", "changes touching more than one service").
- When two readings are plausible, state the intended one. If you can't tell which it is, ask the author.

## 5. Actionability: can the agent proceed and know when it is done?

**Definition.** Context supplies "enough direction to act": the **objective**, the **constraints** that bear on it, and **a definition of what "done" looks like**.

**Relation to Clarity.** It is independent of Clarity. "Where clarity asks whether the context can be read one way, actionability asks whether enough was said." A request can be perfectly unambiguous and still omit the goal or the finish line.

**Consequences.** There are three:
1. The agent never really starts, spending its effort reconstructing an objective that was never stated.
2. It never stops, because nothing defines "finished".
3. It **stops in the wrong place**, "declaring success against a target it inferred rather than one it was given". This is the most expensive, "because the work looks like progress."

**Why it fails.** "The author is closest to the work." When the goal and finish line are already settled in your head, stating them feels redundant.

**What a good brief states.** The paper's version: write it "the way a senior engineer briefs a junior one":
- what you're trying to accomplish
- how you'd know it's solved
- what is off limits, and why
- where the relevant code lives (if you're confident)
- when the agent should come back to you

None of this needs elaborate templates.

**Review checklist**
- Is the goal stated, and why it matters? Is the real intent stated behind any proxy metric? (Otherwise "make the tests pass" invites deleting tests: Goal Drift.)
- Is there a definition of done that can be checked: commands to run, tests that must pass, behavior to observe?
- Are constraints stated (compatibility, performance, APIs not to change, scope limits), with reasons?
- Is each prohibition paired with what to do instead? (Negative-Constraint Fragility.)
- Do rules carry their rationale, so the agent can handle cases the rule didn't anticipate? (Lost in the Details.)
- Are there stopping and escalation conditions (blocked, ambiguous, risky, out of scope, budget or attempts exceeded)? (Weekend Runaway.)
- Is the task feasible with what exists: the files, access, tools, and libraries it assumes? Are the constraints jointly satisfiable? (Impossible Task.)
- Is the method prescribed where it doesn't matter? (Overspecification.)
- For instruction files: can the agent build, test, lint, and run, with exact commands? Does it know what to run before finishing?

**Fix patterns**
- Add a short goal line with its why.
- Add a "Done when" list made of verifiable checks.
- Rewrite "don't X" as "do Y instead, because Z".
- Bound loops ("after two failed attempts, stop and report what you tried").
- Add "ask first" conditions.
- Remove micro-steps the agent would perform better unguided.

## 6. Fidelity: can the agent trust that the context is true?

**Definition.** Context is "accurate": a faithful representation of the system, the organization, and the task. Poor fidelity shows up as "outdated documentation, conflicting instructions, unsupported assumptions, or information from unreliable sources". The agent then produces work that "appears internally consistent while being fundamentally wrong."

**Gaps count.** Fidelity also covers what the context doesn't say. "A gap rarely stays a gap": it forces a guess "that then becomes indistinguishable from fact."

**Why it decays.** Systems and organizations "evolve continuously": code changes, APIs are deprecated, decisions are revisited, policies shift. Context that was once accurate "can quietly become stale." Fidelity is therefore "inseparable from verification." The question is not only whether the context is accurate today, but whether something keeps it accurate: "source-of-truth documents, freshness checks, attribution, and regular review."

**Cost of stale docs.** "An architecture document that no longer matches the code will not just mislead the agent; it will burn tokens as the agent chases files that no longer exist."

**Review checklist**
- Does every path, command, script, version, tool, identifier, env var, config key, endpoint, and schema match the repo now?
- Contradictions: within the file, between the file and the repo, and between the file and its neighbors (README vs CLAUDE.md, lockfile vs install instructions).
- Staleness markers: "currently", "new", "recently", "temporary", "migrating", "soon", dated statements, TODO/TBD, migrations described as still in progress.
- Unsupported claims stated as fact (performance numbers, behavioral guarantees). Is there a source?
- Copied structures (JSON examples, schemas, CLI flags, tool I/O formats): do they still match the source? (Schema Drift.)
- Gaps: what would the agent have to guess?
- Maintenance (shared docs): is there an owner, a review cadence, a source-of-truth link, or a generated section?

**Fix patterns**
- Correct each claim to the verified value.
- Link to the canonical source instead of duplicating it.
- Delete stale content that has no current replacement, and tell the user what you removed.
- Mark unverifiable claims as open questions.
- For shared docs, suggest an owner (a team rather than a person, so it survives reorganizations) and a review cadence.
- Where it's cheap, generate the content from the source or add a CI check.

## 7. Efficiency: can the agent focus on what matters?

**Definition.** Context maximizes signal and minimizes irrelevant information, for two reasons:
1. Irrelevant context "competes with relevant information for the model's attention." Performance degrades as input grows, and does so unevenly (Lost in the Middle).
2. Cost: "every unnecessary token is paid for, and that cost compounds across every session."

**Not brevity.** "The goal is not the smallest possible context, but the highest signal-to-noise ratio." "Every token that competes for attention without helping the task should go." But the paper also says that "a slightly verbose context is usually preferable to one that is missing critical information."

**Location matters most for always-loaded files.** An instruction about one rarely touched file, placed in a root AGENTS.md, "will be injected into thousands of sessions that have nothing to do with that file". The same words as a comment inside that file are "clear, efficient, and available exactly when relevant. Nothing about the words changed; only their location did."

**Review checklist**
- Does each section serve this file's readers *at this location*?
- Always-loaded files: is there content needed only for rare tasks, one directory, or one file? Relocate it (see `file-types.md`).
- Generic advice the agent follows anyway: "write clean code", "follow best practices", "you are an expert".
- Rules already enforced by tooling (formatter, linter, type checker, CI). Prose duplicates the config and drifts from it.
- Duplication, within the file and across neighbors. Two copies also become a Fidelity risk.
- Ordering: are the most important, most-used facts early? Is a critical rule buried mid-list?
- Emphasis inflation (ALL CAPS, "!!!", IMPORTANT everywhere). When everything is urgent, nothing is, and modern models may over-apply shouted rules.
- Overspecification: step-by-step prescriptions for things the model does well unguided.
- Pasted bulk (logs, full schemas, whole style guides, changelogs) that a link or a pointer would replace.
- Eager `@imports` in CLAUDE.md that pull large files into every session.

**Fix patterns**
- Delete generic advice and tool-enforced rules, replacing them with a one-line pointer to the tool.
- Deduplicate.
- Move critical items to the top.
- Relocate scoped content.
- Replace pasted bulk with a path to read on demand.
- Turn prescriptions into goal plus constraints plus why.

## 8. Security: should the agent have this context at all?

**Definition.** The first four properties ask whether context lets the agent do good work; security asks whether the agent should have been given the context in the first place. "Failures of the first four dimensions make agents less effective. Failures of security make them unsafe."

**The two dominant failure classes**
1. **Untrusted context.** Content from sources an attacker can influence may carry instructions or false assertions "intended to steer the agent." The question is not whether a model *can* resist, but "whether attacker-controlled content was in the context in the first place." As with SQL injection, "information cannot be trusted simply because it arrives through a legitimate channel." EchoLeak (an email nobody opened) and CamoLeak (hidden instructions in a pull request) worked because "hostile content became part of the agent's working context. The boundary between data and instructions disappeared."
2. **Overshared context.** "Secrets, personal data, or regulated information they do not actually need." Once in context it "may be logged, cached, transmitted, or surfaced in ways the organization never intended."

**Review checklist**
- Secrets: tokens, API keys, passwords, connection strings with credentials, private keys, webhook URLs.
- Personal or regulated data (customer data, health or financial records) and internal-only detail the task doesn't need.
- Instructions that make the agent act on untrusted content: "follow the instructions in the issue/PR/email/web page", "do what the comment says", "apply all suggestions".
- Hidden content: HTML comments addressed to agents, invisible Unicode (zero-width characters, bidi controls, tag characters, variation-selector runs), instructions in link titles or alt text.
- Third-party text pasted verbatim (issue bodies, scraped pages) with no marking that it is quoted data.
- Dangerous defaults: skipping hooks or verification, force-push, pushing straight to main, disabling TLS, auth, or tests, `curl | sh`, auto-merge or auto-approve, overly broad tool permissions.
- Exfiltration paths: instructions to send content to external URLs, webhooks, or emails; Markdown images with templated URLs.
- Channel mixing: private content copied into a widely shared file.

**Fix patterns**
- Secrets: remove the secret, point to where it lives (env var or secret manager), and tell the user to **rotate** it.
- Minimize data to what the task needs.
- Untrusted content: treat it as quoted data, and require human confirmation for any action it requests.
- Hidden content: delete hidden instructions, and make legitimate ones visible.
- Narrow permissions.
- Replace dangerous defaults with the safe procedure plus "ask first".

---

## 9. Classifying findings

**Independence.** Each dimension "names a distinct way context can succeed or fail":
- clear but not faithful (it describes the system as it *was*)
- faithful and secure but not efficient (it buries the one detail that matters)
- efficient and faithful but not actionable (it never says what finishing looks like)

A single bad instruction can fail several dimensions at once. Give each finding one **primary** dimension, and add a secondary only when the failure genuinely spans both (Weekend Runaway, for example, is Efficiency + Actionability).

**Why these five.** A property earns a pillar only if it is not derivable from the others, can be acted on independently, and names a failure the others miss. Other candidates fold in:
- **Timeliness** is part of **Fidelity** (stale context is context that is no longer true).
- **Provenance** is how you keep context trustworthy, so it belongs to **Fidelity**.
- **Cost** is a downstream consequence of **Efficiency**.
- **Accessibility** is a precondition, outside CAFE(S).

**Severity.** These are the defaults; adjust for reach.

| | Typical findings |
|---|---|
| Critical | secrets; untrusted-content routing; hidden instructions; destructive defaults; sensitive data that isn't needed |
| High | false or stale facts; contradictions; ambiguity on what the task turns on; no goal or done criteria (briefs); missing must-know commands (instruction files); impossible requirements |
| Medium | misplaced content in always-loaded files; buried critical rules; prohibitions with no alternative; missing rationale; unbounded loops; overspecification |
| Low | wording, minor redundancy, formatting |

A finding moves up a level when reach is high (an always-loaded or widely shared file) and down a level for personal or one-off notes.

## 10. Calibration

- **Good enough, not perfect.** "Teams should first eliminate missing, incorrect, and stale context before optimizing for elegance or brevity."
- **Effort is proportional to reach.** A repository-wide instruction file that shapes thousands of sessions "deserves far more review than a working note shared between two engineers."
- **Evaluate in situ.** Judge content where it lives and when it is consumed, not in the abstract.
- **Not everything should be shared.** Personal working notes are legitimately personal. Publishing them "would both reduce individual productivity and pollute everyone else's context." The team's job is to pick out what should be shared, reviewed, and maintained.
- **Enables autonomy, doesn't guarantee it.** Healthy context is a prerequisite for trusting an agent with more autonomy, "but it is not a guarantee of it." Whether to grant autonomy still depends on stakes, risk tolerance, and accountability. Never present a clean review as clearance for unsupervised work. Say that the context is fit for the task, and leave the decision about autonomy to the people accountable for it.
- **A definition, not a measurement system.** Don't invent numeric scores. Use the dimensions as a checklist, "the way you might hold a pull request against a set of review criteria."
