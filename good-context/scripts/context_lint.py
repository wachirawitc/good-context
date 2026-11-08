#!/usr/bin/env python3
"""context_lint.py - mechanical evidence for a good-context (CAFE(S)) review.

Usage:
    python context_lint.py FILE [--repo-root DIR] [--json] [--max-items N]

Prints leads grouped by CAFE(S) dimension (Clarity, Actionability, Fidelity,
Efficiency, Security). Leads are not verdicts: a "missing" path may be created
at build time, a "secret" may be a documented placeholder, and a risky command
may sit inside a rule that forbids it. Confirm each lead against the file and
the repository before reporting it.

Standard library only (Python 3.8+). Windows, macOS and Linux.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

TODAY = dt.date.today()

# --------------------------------------------------------------------------- tables

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist",
    "build", "out", "target", ".next", ".nuxt", ".svelte-kit", ".cache", "coverage",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "vendor", ".idea", ".gradle",
    ".terraform", "obj", ".turbo", ".parcel-cache", "bower_components", "site-packages",
}
MAX_WALK_FILES = 20000
LOCKFILES = {
    "package-lock.json": "npm", "npm-shrinkwrap.json": "npm", "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm", "bun.lockb": "bun", "bun.lock": "bun",
}
MANIFESTS = {
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "go.mod",
    "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "composer.json",
    "mix.exs", "deno.json", "pnpm-workspace.yaml",
}
CONTEXT_NAMES = {
    "claude.md", "claude.local.md", "agents.md", "gemini.md", "copilot-instructions.md",
    ".cursorrules", ".windsurfrules", ".clinerules", "conventions.md", "skill.md",
}
KNOWN_EXT = (
    "md|mdx|markdown|mdc|txt|rst|adoc|py|pyi|ipynb|js|mjs|cjs|jsx|ts|tsx|mts|cts|vue|svelte|"
    "astro|json|jsonc|json5|yml|yaml|toml|ini|cfg|conf|env|lock|sh|bash|zsh|fish|ps1|psm1|bat|"
    "cmd|go|rs|java|kt|kts|scala|groovy|gradle|rb|php|cs|csproj|sln|fs|cpp|cc|cxx|c|h|hpp|swift|"
    "dart|lua|ex|exs|erl|hs|ml|sql|prisma|graphql|gql|proto|tf|tfvars|hcl|html|htm|css|scss|sass|"
    "less|xml|svg|png|jpg|jpeg|gif|webp|pdf|csv|tsv|tmpl|tpl|j2|jinja|mk|cmake|nix|bzl|pem|crt|"
    "log|example|sample"
)
EXT_RE = re.compile(r"\.(?:%s)$" % KNOWN_EXT, re.I)
KNOWN_BARE = {
    "Makefile", "makefile", "GNUmakefile", "Dockerfile", "Containerfile", "Procfile", "Gemfile",
    "Rakefile", "Justfile", "justfile", "Jenkinsfile", "Vagrantfile", "Brewfile", "Pipfile",
    "LICENSE", "CODEOWNERS", ".nvmrc", ".node-version", ".python-version", ".tool-versions",
    ".gitignore", ".gitattributes", ".editorconfig", ".prettierrc", ".eslintrc", ".npmrc",
    ".dockerignore",
}
GENERATED = {
    ".env", ".env.local", "node_modules", "dist", "build", "out", "coverage", "target",
    ".venv", "venv", "__pycache__", ".next",
}
TECH_NAMES = {
    "node.js", "next.js", "nuxt.js", "vue.js", "react.js", "express.js", "nest.js", "d3.js",
    "three.js", "chart.js", "moment.js", "day.js", "ember.js", "backbone.js", "alpine.js",
    "solid.js", "angular.js", "knockout.js", "p5.js", "anime.js", "video.js", "pdf.js",
    "paper.js", "fabric.js", "matter.js", "phaser.js", "gatsby.js", "remix.js", "redux.js",
    "immer.js", "highlight.js", "prism.js", "mermaid.js", "handlebars.js", "mustache.js",
    "underscore.js", "lodash.js", "jquery.js", "electron.js", "meteor.js", "deno.js", "bun.js",
    "hapi.js", "koa.js", "sails.js", "vite.js", "svelte.js", "preact.js", "lit.js", "htmx.js",
    "docs.rs",
}
SHELL_LANGS = {
    "", "sh", "bash", "shell", "console", "zsh", "fish", "powershell", "ps", "ps1", "pwsh",
    "cmd", "bat", "batch", "terminal", "text", "txt", "shellsession", "sh-session",
}
COMMON_ACRONYMS = set("""
AI API APIS URL URLS URI HTTP HTTPS JSON YAML YML TOML XML HTML CSS SCSS JS TS JSX TSX SQL
NOSQL CLI GUI UI UX CI CD PR MR ID OK TODO TBD FIXME README MD PDF CSV TSV SVG PNG JPG GIF
AWS GCP GCS EC2 IAM VPC SSH SSL TLS DNS TCP UDP IP JWT OAUTH SSO SAML ORM SDK IDE OS CPU GPU
RAM SSD DB RDS MCP LLM GPT NPM PNPM ENV CRUD REST RPC GRPC HTML5 UTF UTF8 ASCII ISO UTC GMT
QA E2E UAT PROD DEV STG MVP POC FAQ RFC ADR SLA SLO SLI KPI OKR HR IT PM EM VP CEO CTO US UK
EU USD EUR GDPR HIPAA PII PCI SOC SOC2 MFA 2FA OTP CORS CSRF XSS CSP CDN SEO WASM VM K8S EKS
GKE AKS DOM SPA SSR SSG ESM CJS CRLF LF EOF BOM PID TTY GIT WIP FYI ETA ASAP NA TBA YES NO
ON OFF AND OR NOT THE IF ALL ANY NEW OLD MUST NEVER ALWAYS IMPORTANT NOTE WARNING CRITICAL
REQUIRED DO DONT ONLY SHOULD MAY NONE NULL TRUE FALSE GET POST PUT PATCH DELETE HEAD OPTIONS
A I MIT BSD GPL APACHE PDF VS JVM JDK JRE NET RSS CMS CRM ERP2 BI ML NLP OCR RAG S3 SQS SNS
EOL TTL LRU FIFO LIFO ANSI BFS DFS AST LSP CLI2 IO GC JIT OOP DSL YAGNI KISS SOLID DRY
PATH HOME CWD STDIN STDOUT STDERR
""".split())

# --------------------------------------------------------------------------- regexes

CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
URL_RE = re.compile(r"\b(?:https?|ftp)://[^\s)<>\]`'\"]+|\bwww\.[^\s)<>\]`'\"]+", re.I)
MD_LINK_RE = re.compile(
    r"(!?)\[([^\]]*)\]\(\s*<?([^)\s>]*)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
REF_DEF_RE = re.compile(r"^\s{0,3}\[([^\]^][^\]]*)\]:\s*<?(\S+?)>?(?:\s+.*)?$")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)
TOKEN_SPLIT_RE = re.compile(r"[\s,;|&()<>\"'`=]+")
IMPORT_RE = re.compile(r"(?<![\w`/@.])@((?:~|\.{1,2})?/?[A-Za-z0-9_.\-/~]+)")
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.I)

VAGUE_TERMS = [
    "properly", "appropriately", "as appropriate", "where appropriate", "as needed",
    "as necessary", "if needed", "if necessary", "when necessary", "when needed", "etc.",
    "and so on", "and so forth", "best practices", "clean code", "good code", "high quality",
    "high-quality", "reasonable", "sensible", "the usual", "as usual", "the standard way",
    "the right way", "make sure it works", "robust", "optimal", "efficiently",
    "user-friendly", "intuitive", "faster", "as fast as possible", "quickly", "somehow",
    "some kind of", "stuff",
]
VAGUE_RE = re.compile(
    r"(?i)(?<![\w-])(" + "|".join(re.escape(t) for t in sorted(VAGUE_TERMS, key=len, reverse=True))
    + r")(?![\w-])")
AMBIG_RE = re.compile(
    r"(?i)\b(?:the|this|that)\s+"
    r"(?:(?!(?:following|same|next|first|last|above|below|previous|whole|entire|other|given"
    r"|specific|relevant|appropriate|codespan|quoted|a|an|the|is|are|was|be)\b)[a-z][\w-]*\s+)?("
    r"(?:old|new)\s+(?:way|api|system|version|endpoints?|service|flow)"
    r"|config(?:uration)?(?:\s+file)?|caching\s+layer|server|service|database|db|api|app"
    r"|application|backend|frontend|client|script|cluster|environment|env|pipeline|queue"
    r"|bucket|table|module|package|component|endpoint|function|model|team|tool|branch|job"
    r"|worker|schema|migration|cache|dashboard|page|form)\b(?!\s+(?:variables?|vars?|sizes?)\b)")
CODE_OBJECTS = {
    "console", "res", "req", "window", "document", "process", "math", "json", "os", "sys", "self",
    "this", "response", "request", "ctx", "logger", "logging", "np", "pd", "fs", "path", "util",
    "object", "array", "string", "number", "promise", "date", "error", "app", "module", "exports",
}
ACRONYM_RE = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]{1,6})s?(?![\w-])(?!\.[A-Za-z])")
SHOUTED_WORDS = set("""IS IN IT ON AT TO OF BY AS BE OR IF SO UP NO WE US AN AM DO GO MY
BOTH SAME EACH EVERY BEFORE AFTER WITH WITHOUT FROM INTO THEN THAN THIS THAT THESE THOSE
WHEN WHERE WHAT WHICH WHO WHY HOW HAS HAVE HAD WAS WERE ARE CAN WILL WOULD COULD MUST SHOULD
NEVER ALWAYS ONLY NOT AND BUT ALL ANY NONE SOME MORE MOST LESS LEAST VERY EVEN JUST ALSO
STILL AGAIN ONCE TWICE HERE THERE NOW YET STOP READ RUN USE SEE ASK KEEP MAKE DONT EXACTLY
FIRST LAST NEXT NEW OLD SKILL FILE FILES CODE DATA TEST TESTS NOTE IMPORTANT REQUIRED
CRITICAL WARNING ENTIRE WHOLE CAREFULLY ANYTHING EVERYTHING NOTHING""".split())
POSITIVE_RE = re.compile(
    r"(?i)\b(use|run|call|prefer|put|write|add|ask|keep|choose|rely on|go through|instead|apply"
    r"|create|send|pass|return|stop|leave|follow|print|show|tell|report|warn|log|continue"
    r"|proceed|retry|wait|check|read|fix|update|move|mention|flag|raise|open|let|skim|relocate"
    r"|delegate|consult|verify|confirm|cite|inline|extract|escalate|edit|enable|install|replace"
    r"|define|query|import)\b")
DATE_CTX_RE = re.compile(
    r"(?i)(?:\b(?:in|since|as of|from|until|till|before|after|during|by|circa|early|mid|late"
    r"|end of|spring|summer|fall|autumn|winter|q[1-4]|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?"
    r"|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?"
    r"|dec(?:ember)?)\s+(19[89]\d|20\d\d)\b|\b(19[89]\d|20\d\d)-[01]\d(?:-[0-3]\d)?\b)")
STRONG_ROUTE_RE = re.compile(
    r"(?i)\bfollow (?:any|all|the|their|its|those|these)?\s*(?:instructions?|directions?|steps"
    r"|requests?)\b|\binstructions? (?:you find|found|left|given|written) (?:in|there)\b"
    r"|\bdo (?:what|whatever)\s+(?:[\w'-]+\s+){1,4}?(?:says?|asks?|requests?|tells? you|wants?)\b"
    r"|\b(?:execute|run) (?:any|all|the)?\s*(?:commands?|code|scripts?) (?:in|from|found|they)\b"
    r"|\b(?:apply|implement|accept) (?:any|all|every) (?:suggestions?|changes?|instructions?"
    r"|requests?)\b|\btrust (?:the|any|all) (?:content|input|instructions?|comments?)\b")

NEG_RE = re.compile(
    r"(?i)\b(never|don'?t|do not|must not|mustn'?t|should not|shouldn'?t|avoid|no longer"
    r"|not allowed|forbidden|prohibited)\b")
# Prohibitive wherever they appear ("Secrets must not be committed", "Force-push is forbidden").
STRONG_NEG_RE = re.compile(
    r"(?i)^(must not|mustn'?t|should not|shouldn'?t|not allowed|forbidden|prohibited)$")
# "never" / "don't" / "avoid" are rules only in imperative position ("Never X", "you must never
# X"); elsewhere they describe ("paths that don't resolve", "personal files don't need polish").
IMPERATIVE_SUBJECT_RE = re.compile(
    r"(?i)(?:^|\byou\s*(?:must|should|shall|may|will|can)?"
    r"|\b(?:we|agents?|claude|codex|copilot|assistants?|models?)\s+(?:must|should|shall|may|will|can)"
    r"|\b(?:must|should|shall))\s*$")
ALT_RE = re.compile(
    r"(?i)\b(instead|rather than|in favou?r of|prefer|replace[d]? (?:it |them )?with"
    r"|switch to|unless|except|without|use\b.{1,60}\binstead"
    r"|only (?:through|via|with|in|from|by|on|inside|within))\b|→|->|=>")
WHY_RE = re.compile(
    r"(?i)\b(because|since|so that|otherwise|to avoid|to prevent|to keep|due to|reason"
    r"|which (?:would|will|can|could|breaks?|causes?))\b")
RUNAWAY_RE = re.compile(
    r"(?i)\b(until (?:it|they|everything|all(?: the)?(?: tests)?|the tests?|tests?)\s+"
    r"(?:works?|pass(?:es)?|succeeds?|is (?:done|perfect|green)|are green)"
    r"|keep (?:trying|going|iterating|retrying|fixing)|as many (?:times|iterations|attempts) as"
    r"|don'?t stop|do not stop|never give up|whatever it takes|no matter (?:what|how long)"
    r"|fix (?:all|every|any) (?:issues?|errors?|bugs?|warnings?|problems?))\b")
GOAL_RE = re.compile(
    r"(?i)\b(goal|objective|purpose|we want|so that|in order to|why|outcome|problem"
    r"|background|context)\b")
DONE_RE = re.compile(
    r"(?i)\b(done when|definition of done|acceptance criteria|success criteria"
    r"|success looks like|expected (?:result|outcome|behaviou?r)|test plan"
    r"|(?:ready|complete|finished|done) when|must pass|verify (?:by|that|with)|how to verify"
    r"|you(?:'re| are) done)\b")
ESCALATE_RE = re.compile(
    r"(?i)\b(ask (?:me|us|the user|first|before)|check with|confirm with|stop and"
    r"|escalate|come back|reach out|if (?:you(?:'re| are)? )?(?:unsure|blocked|stuck|in doubt)"
    r"|open questions?)\b")

GENERIC_RES = [
    re.compile(r"(?i)\byou are an? (?:expert|senior|world[- ]class|experienced|helpful|skilled)\b"),
    re.compile(r"(?i)\b(?:write|keep|produce)\s+(?:\w+,?\s+){0,3}?(?:clean|readable|maintainable"
               r"|high[- ]quality|good)(?:,?\s+(?:and\s+)?(?:clean|readable|maintainable))*\s+code\b"),
    re.compile(r"(?i)\bfollow(?:ing)? (?:the )?best practices\b"),
    re.compile(r"(?i)\b(?:use|choose|pick) (?:meaningful|descriptive|clear|good) "
               r"(?:variable |function )?names\b"),
    re.compile(r"(?i)\bkeep (?:functions|methods|code|classes) (?:small|short|simple|clean)\b"),
    re.compile(r"(?i)\bthink step[- ]by[- ]step\b"),
    re.compile(r"(?i)\bbe (?:careful|thorough|precise|concise)\b"),
    re.compile(r"(?i)\b(?:handle|catch) errors? (?:properly|appropriately|gracefully|correctly)\b"),
    re.compile(r"(?i)\bfollow (?:the )?SOLID\b"),
    re.compile(r"(?i)\bdouble[- ]check your work\b"),
    re.compile(r"(?i)\bread this (?:entire |whole )?file\b"),
]
EMPH_RE = re.compile(
    r"\b(MUST(?: NOT)?|NEVER|ALWAYS|IMPORTANT|CRITICAL|REQUIRED|MANDATORY|WARNING|DO NOT"
    r"|DON'T|ONLY)\b")
BANG_RE = re.compile(r"!{2,}")

STALE_RE = re.compile(
    r"(?i)\b(currently|at the moment|for now|right now|recently|temporar(?:y|ily)|soon"
    r"|upcoming|in progress|being migrated|migrating|we are moving|will be (?:removed|replaced"
    r"|deprecated|migrated)|deprecated|outdated|no longer)\b")
MARKER_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX|WIP|HACK)\b")
VERSION_CLAIM_RE = re.compile(
    r"(?i)(?<![\w.-])(node(?:\.?js)?|python|golang|go|java|jdk|ruby|php|rust|deno|bun"
    r"|typescript|react|next(?:\.?js)?|vue|angular|django|flask|fastapi|rails|express|fastify"
    r"|nestjs|postgres(?:ql)?|mysql|redis|pnpm|yarn|npm)(?:\s+version)?(?:\s*(?:v|@)\s*|\s+)"
    r"(\d+(?:\.\d+){0,2})(?:\.x|\+)?(?![\w.])")
CI_MENTION_RE = re.compile(
    r"(?i)\b(github actions|gitlab[- ]ci|gitlab pipelines?|jenkins|circleci|circle ci"
    r"|azure pipelines|bitbucket pipelines|travis(?: ci)?|buildkite)\b")

SECRET_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("GitLab token", re.compile(
        r"\bgl(?:pat|dt|ptt|rt|cbt|imt|oas|soat|ffct|agent)-[A-Za-z0-9_\-]{20,}")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("Slack webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Stripe key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("credentials in URL", re.compile(
        r"\b[a-z][a-z0-9+.\-]*://([^\s:/@'\"`]+):([^\s@/'\"`]{3,})@([^\s/'\"`:]+)", re.I)),
    ("secret-looking assignment", re.compile(
        r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|apikey|access[_-]?key|access[_-]?token"
        r"|auth[_-]?token|client[_-]?secret|private[_-]?key|token)\b[\"']?\s*[:=]\s*[\"']?"
        r"([^\s\"'`,;]{6,})")),
]
PLACEHOLDER_RE = re.compile(
    r"(?i)^(?:x{3,}.*|\*{3,}|<[^>]*>|\$\{?[A-Za-z0-9_]+\}?|%[A-Za-z0-9_]+%|\{\{.*\}\}"
    r"|your[-_ ]?\w*|example\w*|changeme|change[-_]me|placeholder|dummy|redacted|replace[-_]?me"
    r"|todo|tbd|none|null|secret|password|passw0rd|pass|test|\.{3,}|…)$")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}

RISKY_PATTERNS = [
    ("prompt-injection phrasing", re.compile(
        r"(?i)\bignore (?:all |any )?(?:the )?(?:previous|prior|above|earlier|preceding) "
        r"(?:instructions|rules|prompts?|directions)\b|\bdisregard (?:all |any |the )?"
        r"(?:previous|prior|above|earlier) \w+|\byou are now\b|\bnew instructions\s*:"
        r"|\bdo not (?:tell|inform|mention (?:this )?to) the user\b"
        r"|\bwithout (?:telling|informing|notifying) the user\b")),
    ("skips a safety check", re.compile(
        r"(?i)--no-verify\b|--dangerously-skip-permissions\b|--yolo\b"
        r"|\bskip (?:the )?(?:tests|hooks|ci|checks|review)\b"
        r"|\bdisable (?:the )?(?:ssl|tls|certificate|cert|verification|auth\w*|2fa|mfa|tests?"
        r"|lint\w*|hooks?|ci|security|sandbox)\b|\bverify\s*=\s*False\b"
        r"|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|--insecure\b|StrictHostKeyChecking=no")),
    ("destructive or irreversible command", re.compile(
        r"(?i)\brm\s+-[a-z]*(?:rf|fr)[a-z]*\b|\bgit\s+push\b[^\n`]*(?:--force\b|\s-f\b)"
        r"|\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-[a-z]*f|\bdrop\s+(?:table|database|schema)\b"
        r"|\btruncate\s+table\b|\bchmod\s+(?:-R\s+)?777\b|\bmkfs\b")),
    ("pipes a remote script into a shell", re.compile(
        r"(?i)\b(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n|`]*\|\s*"
        r"(?:sudo\s+)?(?:ba|z|da)?sh\b|\|\s*iex\b")),
    ("bypasses review", re.compile(
        r"(?i)\b(?:push|commit|merge)\w*\b[^\n`]{0,40}\b(?:directly )?(?:to|into|on) "
        r"(?:main|master|prod(?:uction)?|release)\b|\bauto-?(?:merge|approve|accept)\b"
        r"|\bwithout (?:review|approval|asking)\b")),
    ("sends data to an external destination", re.compile(
        r"(?i)\b(?:send|post|upload|forward|share|exfiltrate|transmit)\w*\b[^\n]{0,60}"
        r"\b(?:to|with)\b[^\n]{0,30}(?:https?://|webhook|pastebin|gist|external|third[- ]party"
        r"|discord|telegram)")),
    ("markdown image with templated URL (exfiltration vector)", re.compile(
        r"!\[[^\]]*\]\(\s*https?://[^)\s]*(?:\{|\$|%7[Bb])")),
]
UNTRUSTED_SRC_RE = re.compile(
    r"(?i)\b(issues?|tickets?|pr|prs|pull requests?|merge requests?|comments?|emails?|e-mails?"
    r"|inbox|messages?|slack|discord|chat|web ?pages?|websites?|search results?|tool output"
    r"|logs?|user input|customers?|fetched|retrieved|external|third[- ]party|readmes? of)\b")
NEGATION_CTX_RE = re.compile(
    r"(?i)\b(never|don'?t|do not|must not|mustn'?t|should not|shouldn'?t|avoid|not|without"
    r"|forbid\w*|prohibit\w*|disallow\w*|no)\b")
CLAUSE_SPLIT_RE = re.compile(r"[.;:!?,](?:\s|$)|\s[-–—]\s")
CLAUSE_NEG_RE = re.compile(
    r"(?i)\b(never|don'?t|do not|must not|mustn'?t|should not|shouldn'?t|may not|cannot|can'?t"
    r"|avoid|forbid\w*|prohibit\w*|disallow\w*)\b")
QUOTE_RE = re.compile(r'"[^"\n]{1,160}"|“[^”\n]{1,160}”')
BENIGN_COMMENT_RE = re.compile(
    r"(?i)^\s*(?:markdownlint|prettier|eslint|cspell|spell-?checker|vale|textlint|toc|end ?toc"
    r"|begin|end|start|stop|auto-?generated|generated|do not edit|region|endregion|lint"
    r"|@formatter|omit in toc|fmt:|all-contributors)")
AGENT_ADDRESSED_RE = re.compile(
    r"(?i)\b(?:ai|agents?|assistants?|claude|copilot|cursor|codex|gemini|llms?|models?|bots?)\b"
    r"|\b(?:ignore|disregard|instruction|you must|you should|always|never|do not tell)\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
BENIGN_EMAIL_DOMAINS = ("example.com", "example.org", "example.net", "users.noreply.github.com",
                        "noreply.github.com", "localhost", "test.com")

INVISIBLE_CPS = {
    0x200B, 0x200C, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0xFEFF, 0x00AD, 0x034F, 0x115F,
    0x1160, 0x180E, 0x3164, 0xFFA0, 0x2800,
}
BIDI_CPS = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}

NPM_SCRIPT_ALIASES = {"test": "test", "t": "test", "tst": "test", "start": "start",
                      "stop": "stop", "restart": "restart"}
YARN_BUILTINS = set("""install add remove upgrade up init info why workspaces global link unlink
login logout publish pack cache config dlx exec set plugin version help audit outdated create
node constraints npm patch patch-commit rebuild unplug import licenses list owner tag team check
autoclean generate-lock-entry policies bin explain search stage""".split())
PNPM_BUILTINS = set("""install i add remove rm uninstall un update up upgrade link ln unlink import
rebuild rb prune fetch dlx exec x create init publish pack audit outdated list ls why store env
setup server root bin config c licenses patch patch-commit deploy recursive help version doctor
approve-builds catalog self-update""".split())
BUN_BUILTINS = set("""install i add a remove rm update upgrade x create init link unlink pm build
test publish outdated patch why audit info repl exec""".split())


# --------------------------------------------------------------------------- utilities

def short(s: str, n: int = 100) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def estimate_tokens(s: str) -> int:
    ascii_n = sum(1 for ch in s if ord(ch) < 128)
    return int(round(ascii_n / 4.0 + (len(s) - ascii_n) / 1.5))


def relpath(p: Path, base: Path | None) -> str:
    if base is not None:
        try:
            r = p.relative_to(base).as_posix()
            return r if r else "."
        except ValueError:
            pass
    try:
        return "~/" + p.relative_to(Path.home()).as_posix()
    except ValueError:
        return p.as_posix()


def read_text(p: Path) -> str | None:
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode("utf-8", errors="replace")


def load_json(p: Path):
    t = read_text(p)
    if t is None:
        return None
    try:
        return json.loads(t)
    except ValueError:
        return None


def run_git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


_LISTDIR: dict = {}


def listdir_cached(p: Path):
    key = str(p)
    if key not in _LISTDIR:
        try:
            _LISTDIR[key] = os.listdir(p)
        except OSError:
            _LISTDIR[key] = None
    return _LISTDIR[key]


def resolve_case(base: Path, rel: str):
    """Resolve rel under base one segment at a time, independent of the OS's case rules.
    Returns (path or None, exact_case)."""
    cur, exact = base, True
    for part in rel.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            cur = cur.parent
            continue
        entries = listdir_cached(cur)
        if entries is None:
            return None, False
        if part in entries:
            cur = cur / part
            continue
        alt = next((e for e in entries if e.lower() == part.lower()), None)
        if alt is None:
            return None, False
        exact, cur = False, cur / alt
    return cur, exact


def gh_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    s = text.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def norm_line(s: str) -> str:
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?", "", s)
    s = re.sub(r"[*_`~>#]+", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s.rstrip(".:;,!")


def negated_before(line: str, start: int) -> bool:
    return bool(NEGATION_CTX_RE.search(line[max(0, start - 80):start]))


def find_prohibition(s: str):
    """First negation in `s` that reads as a rule rather than a description, or None."""
    for m in NEG_RE.finditer(s):
        word = m.group(1).lower()
        if word == "no longer":
            continue
        if STRONG_NEG_RE.match(word):
            if re.search(r"(?i)\b(?:should|must)\s+(?:and|or)\s*$", s[:m.start()]):
                continue  # "what it should and shouldn't contain" describes, doesn't forbid
            return m
        clause = CLAUSE_SPLIT_RE.split(s[:m.start()])[-1]
        clause = re.sub(r"^\s*(?:>\s*)*(?:[-*+]|\d+[.)])?\s", " ", clause)
        clause = re.sub(r"[*_`\"'“”‘’()\[\]]", " ", clause)
        clause = re.sub(r"(?i)^\s*(?:(?:and|but|or|then|so|also|please|just|simply|otherwise)\s+)*",
                        "", clause).strip()
        if IMPERATIVE_SUBJECT_RE.search(clause):
            return m
    return None


def negated_in_clause(line: str, start: int) -> bool:
    """True when a prohibition word occurs in the same clause, before position `start`."""
    clause = CLAUSE_SPLIT_RE.split(line[max(0, start - 120):start])[-1]
    return bool(CLAUSE_NEG_RE.search(clause))


# --------------------------------------------------------------------------- repository

def find_root(target: Path, override: str | None):
    """Returns (root, is_git, shallow)."""
    if override:
        root = Path(os.path.expanduser(override)).resolve()
        return root, (root / ".git").exists(), False
    for cand in [target.parent, *target.parent.parents]:
        if (cand / ".git").exists():
            return cand, True, False
    markers = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml",
               "build.gradle", ".gitlab-ci.yml", "composer.json", "Gemfile", "pnpm-workspace.yaml")
    home, best = Path.home(), None
    for cand in [target.parent, *target.parent.parents]:
        if cand == home or cand == cand.parent:
            break
        if any((cand / m).exists() for m in markers):
            best = cand
    if best is not None:
        return best, False, False
    return target.parent, False, True


def walk(root: Path, shallow: bool):
    files, truncated = [], False
    depth0 = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if shallow and len(Path(dirpath).parts) - depth0 >= 1:
            dirnames[:] = []
        for f in filenames:
            files.append(Path(dirpath) / f)
        if len(files) >= MAX_WALK_FILES:
            truncated = True
            break
    return files, truncated


def parse_compose(text: str):
    services, images = [], []
    in_services, svc_indent = False, None
    for line in text.splitlines():
        if re.match(r"^services\s*:\s*$", line):
            in_services, svc_indent = True, None
            continue
        if in_services and re.match(r"^\S", line):
            in_services = False
        if in_services:
            m = re.match(r"^(\s+)([A-Za-z0-9_.-]+)\s*:\s*$", line)
            if m:
                ind = len(m.group(1))
                if svc_indent is None:
                    svc_indent = ind
                if ind == svc_indent:
                    services.append(m.group(2))
        m = re.match(r"^\s+image\s*:\s*['\"]?([\w./-]+)(?::([\w.-]+))?", line)
        if m:
            images.append((m.group(1), m.group(2) or "latest"))
    return services, images


GITLAB_RESERVED = {"stages", "variables", "default", "include", "workflow", "image", "services",
                   "before_script", "after_script", "cache", "spec"}


def parse_gitlab_jobs(text: str):
    jobs = []
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z0-9_\"'][^#]*?):\s*(?:#.*)?$", line)
        if m:
            k = m.group(1).strip().strip("\"'")
            if k and not k.startswith(".") and k not in GITLAB_RESERVED:
                jobs.append(k)
    return jobs


def build_inventory(root: Path, files):
    inv = {"packages": [], "lockfiles": [], "ci": [], "ci_jobs": [], "compose_services": [],
           "compose_images": [], "manifests": [], "top_dirs": [], "makefiles": [],
           "justfiles": [], "basenames": {}, "context_files": []}
    for p in files:
        name, low = p.name, p.name.lower()
        inv["basenames"].setdefault(name, []).append(p)
        if name == "package.json":
            data = load_json(p)
            if isinstance(data, dict):
                def as_dict(v):
                    return v if isinstance(v, dict) else {}
                inv["packages"].append({
                    "path": p, "dir": p.parent, "name": data.get("name") or "",
                    "scripts": as_dict(data.get("scripts")),
                    "deps": {**as_dict(data.get("dependencies")),
                             **as_dict(data.get("devDependencies"))},
                    "engines": as_dict(data.get("engines")),
                    "packageManager": data.get("packageManager") or "",
                    "volta": as_dict(data.get("volta")),
                })
        if name in LOCKFILES:
            inv["lockfiles"].append(p)
        if name in ("Makefile", "makefile", "GNUmakefile"):
            inv["makefiles"].append(p)
        if low in ("justfile", ".justfile"):
            inv["justfiles"].append(p)
        if low in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            s, imgs = parse_compose(read_text(p) or "")
            inv["compose_services"] += s
            inv["compose_images"] += imgs
        if p.parent == root and name in MANIFESTS:
            inv["manifests"].append(name)
        parts_low = [x.lower() for x in p.parts]
        if (low in CONTEXT_NAMES or low.endswith(".md.sample") and low[:-7] in CONTEXT_NAMES
                or (low.endswith(".instructions.md") and ".github" in parts_low)
                or (low.endswith(".mdc") and "rules" in parts_low)
                or (low in ("readme.md", "architecture.md", "contributing.md") and p.parent == root)):
            inv["context_files"].append(p)
    gl = root / ".gitlab-ci.yml"
    if gl.is_file():
        inv["ci"].append("GitLab CI")
        inv["ci_jobs"] += parse_gitlab_jobs(read_text(gl) or "")
    wf = root / ".github" / "workflows"
    if wf.is_dir():
        names = sorted(f.name for f in wf.iterdir() if f.suffix in (".yml", ".yaml"))
        if names:
            inv["ci"].append("GitHub Actions")
            inv["ci_jobs"] += ["workflow " + n for n in names]
    for fname, label in (("Jenkinsfile", "Jenkins"), (".circleci/config.yml", "CircleCI"),
                         ("azure-pipelines.yml", "Azure Pipelines"),
                         ("bitbucket-pipelines.yml", "Bitbucket Pipelines"),
                         (".travis.yml", "Travis CI"), (".buildkite", "Buildkite")):
        if (root / fname).exists():
            inv["ci"].append(label)
    try:
        inv["top_dirs"] = sorted(d.name for d in root.iterdir()
                                 if d.is_dir() and d.name not in SKIP_DIRS
                                 and not d.name.startswith(".git"))[:30]
    except OSError:
        pass
    return inv


def version_consistent(claim: str, declared: str):
    """Does a claimed version ("18", "3.11") agree with a declared value or range
    ("20.11.0", ">=20", "^5.0.0", ">=3.9,<4", "16-alpine")? True / False, or None when the
    declaration can't be interpreted ("lts/*", "latest", "a || b")."""
    d = declared.strip()
    if "||" in d:
        return None
    try:
        c = tuple(int(x) for x in claim.split("."))
    except ValueError:
        return None
    checks = re.findall(r"(>=|<=|>|<|\^|~|=)?\s*v?(\d+(?:\.\d+){0,2})", d)
    if not checks:
        return None
    for op, ver in checks:
        dv = tuple(int(x) for x in ver.split("."))
        n = min(len(c), len(dv))
        a, b = c[:n], dv[:n]
        if op in (">=", ">"):
            if a < b:
                return False
        elif op in ("<", "<="):
            if a > b or (op == "<" and a == b and len(c) >= len(dv)):
                return False
        elif op == "^":
            if c[0] != dv[0] or a < b:
                return False
        elif op == "~":
            k = min(n, 2)
            if c[:k] != dv[:k] or a < b:
                return False
        elif a != b:
            return False
    return True


def repo_versions(root: Path, inv) -> dict:
    v: dict = {}

    def add(key, src, val):
        if val:
            v.setdefault(key, []).append(f"{src}={str(val).strip()}")

    for fname in (".nvmrc", ".node-version"):
        t = read_text(root / fname)
        if t and t.strip():
            add("node", fname, t.strip().splitlines()[0])
    t = read_text(root / ".tool-versions")
    for line in (t or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            key = {"nodejs": "node", "golang": "go"}.get(parts[0], parts[0])
            add(key, ".tool-versions", parts[1])
    t = read_text(root / ".python-version")
    if t and t.strip():
        add("python", ".python-version", t.strip().splitlines()[0])
    t = read_text(root / "pyproject.toml") or ""
    m = re.search(r"(?m)^requires-python\s*=\s*[\"']([^\"']+)", t)
    if m:
        add("python", "pyproject requires-python", m.group(1))
    m = re.search(r"(?m)^python\s*=\s*[\"']([^\"']+)", t)
    if m:
        add("python", "pyproject (poetry) python", m.group(1))
    t = read_text(root / "go.mod") or ""
    m = re.search(r"(?m)^go\s+(\S+)", t)
    if m:
        add("go", "go.mod", m.group(1))
    dep_keys = {"typescript": "typescript", "react": "react", "next": "next", "vue": "vue",
                "@angular/core": "angular", "express": "express", "fastify": "fastify",
                "@nestjs/core": "nestjs"}
    for pkg in inv["packages"]:
        where = relpath(pkg["path"], root)
        add("node", f"{where} engines.node", pkg["engines"].get("node"))
        add("node", f"{where} volta.node", pkg["volta"].get("node"))
        pm = pkg["packageManager"]
        if isinstance(pm, str) and "@" in pm:
            name, ver = pm.split("@", 1)
            add(name, f"{where} packageManager", ver.split("+")[0])
        for dep, key in dep_keys.items():
            if dep in pkg["deps"]:
                add(key, f"{where} {dep}", pkg["deps"][dep])
    for image, tag in inv["compose_images"]:
        base = image.split("/")[-1]
        if base in ("postgres", "mysql", "redis", "node", "python", "mongo"):
            add({"mongo": "mongodb"}.get(base, base), f"compose image {image}", tag)
    return v


# --------------------------------------------------------------------------- markdown

def parse_markdown(lines):
    n = len(lines)
    kinds, langs, blocks, headings = ["prose"] * n, [""] * n, [], []
    fm_end = -1
    if n and lines[0].strip() == "---":
        for i in range(1, min(n, 300)):
            if lines[i].strip() in ("---", "..."):
                fm_end = i
                break
        for i in range(0, fm_end + 1):
            kinds[i] = "frontmatter"
    in_fence, fch, flen, flang, fstart = False, "", 0, "", 0
    for i in range(fm_end + 1, n):
        m = FENCE_RE.match(lines[i])
        if not in_fence and m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            in_fence, fch, flen, fstart = True, m.group(1)[0], len(m.group(1)), i
            flang = (m.group(2).strip().split() or [""])[0].lower()
            kinds[i] = "fence"
            continue
        if in_fence:
            if m and m.group(1)[0] == fch and len(m.group(1)) >= flen and not m.group(2).strip():
                in_fence = False
                kinds[i] = "fence"
                blocks.append((fstart, i, flang))
                continue
            kinds[i], langs[i] = "code", flang
            continue
        hm = HEADING_RE.match(lines[i])
        if hm:
            headings.append((i, len(hm.group(1)), hm.group(2).strip()))
    if in_fence:
        blocks.append((fstart, n - 1, flang))
    return kinds, langs, blocks, headings, fm_end


def section_outline(lines, headings):
    out = []
    if headings and headings[0][0] > 0:
        pre = "\n".join(lines[: headings[0][0]])
        if pre.strip():
            out.append({"line": 1, "level": 0, "title": "(before first heading)",
                        "tokens": estimate_tokens(pre)})
    for idx, (i, lvl, title) in enumerate(headings):
        end = len(lines)
        for j, l2, _ in headings[idx + 1:]:
            if l2 <= lvl:
                end = j
                break
        out.append({"line": i + 1, "level": lvl, "title": title,
                    "tokens": estimate_tokens("\n".join(lines[i:end]))})
    return out


def clean_token(raw: str):
    t = raw.strip().lstrip("*[{").rstrip(".,:;!?*)]}")
    t = re.sub(r":\d+(?::\d+)?$", "", t)
    if len(t) < 3 or len(t) > 180:
        return None
    low = t.lower()
    if "://" in t or low.startswith(("www.", "mailto:", "#", "$", "%", "-", "@", "+", "/")):
        return None
    if re.search(r"[*?<>{}|$%^\[\]=…]", t) or "..." in t or re.match(r"^[A-Za-z]:[\\/]", t):
        return None
    if any(p in low for p in ("path/to", "your-", "your_", "/your", "example.com", "foo/", "/foo",
                              "foo.", "bar.", "xxx", "placeholder")):
        return None
    if low in TECH_NAMES or re.fullmatch(r"v?\d+(?:\.\d+)+[\w.-]*", t):
        return None
    if re.fullmatch(r"[\w.+-]+@[\w.-]+\.\w+", t):
        return None
    t = t.replace("\\", "/") if re.fullmatch(r"[\w.-]+(?:\\[\w.-]+)+", t) else t
    base = t.rstrip("/").split("/")[-1]
    if base in GENERATED or t.rstrip("/") in GENERATED:
        return None
    starts_rel = t.startswith(("./", "../", "~/"))
    has_slash = "/" in t.strip("/") or t.endswith("/")
    has_ext = bool(EXT_RE.search(base))
    if has_ext and not has_slash and not starts_rel:
        stem = base.rsplit(".", 1)[0]
        if not stem or stem.isdigit() or not re.search(r"[A-Za-z]", stem):
            return None
    if has_ext or base in KNOWN_BARE or starts_rel or has_slash:
        return t
    return None


def path_tokens(text: str):
    for raw in TOKEN_SPLIT_RE.split(text):
        t = clean_token(raw)
        if t:
            yield t


def check_ref(tok: str, file_dir: Path, root: Path, inv, link: bool = False,
              internal_only: bool = False):
    """Returns (status, detail): ok | missing | case | ambiguous | skip | anchor.
    internal_only: the file mostly talks about paths in someone else's workspace (skills,
    commands, user-level instructions), so only paths that claim to live next to the file
    itself are checked."""
    t = tok.replace("\\", "/")
    anchor = None
    if link and "#" in t:
        t, anchor = t.split("#", 1)
    t = unquote(t)
    if not t:
        return "anchor", anchor
    if t.startswith("~/"):
        bases, rel = [Path.home()], t[2:]
    elif t.startswith("/"):
        if not link:
            return "skip", None
        bases, rel = [root], t.lstrip("/")
    else:
        bases = [file_dir] if file_dir == root else [file_dir, root]
        rel = t
    for b in bases:
        found, exact = resolve_case(b, rel)
        if found is not None:
            if not exact:
                return "case", relpath(found, root)
            return "ok", relpath(found, root)
    base = rel.rstrip("/").split("/")[-1]
    single = "/" not in rel.strip("/")
    if internal_only and not link:
        if rel.startswith("./"):
            return "skip", None  # in skills and commands, ./ means the user's working directory
        first = rel.split("/")[0]
        if single or first in ("..", "~") or resolve_case(file_dir, first)[0] is None:
            return "skip", None
    if single and not link:
        matches = inv["basenames"].get(base, [])
        if len(matches) == 1:
            return "ok", relpath(matches[0], root)
        if len(matches) > 1:
            return "ambiguous", [relpath(m, root) for m in matches[:5]]
        if base.split(".")[0].lower() in CODE_OBJECTS:
            return "skip", None  # console.log, res.json ... - code, not a file
    elif not single and not (link or t.startswith(("./", "../", "~/"))
                             or EXT_RE.search(base) or base in KNOWN_BARE):
        first = rel.split("/")[0]
        if not any(resolve_case(b, first)[0] is not None for b in bases):
            return "skip", None
    hints = [relpath(m, root) for m in inv["basenames"].get(base, [])][:3]
    return "missing", hints


# --------------------------------------------------------------------------- commands

def nearest_package(start: Path, root: Path, inv):
    by_dir = {str(p["dir"]): p for p in inv["packages"]}
    cur = start
    while True:
        if str(cur) in by_dir:
            return by_dir[str(cur)]
        if cur == root or cur == cur.parent:
            break
        cur = cur.parent
    return by_dir.get(str(root))


def packages_for_filter(flt: str, inv, root: Path):
    f = flt.strip("'\"")
    out = []
    for p in inv["packages"]:
        name, d = p["name"], p["dir"]
        rp = relpath(d, root)
        if f in (name, d.name, rp, "./" + rp) or (name and name.endswith("/" + f)):
            out.append(p)
    if not out and "*" in f:
        rx = re.compile("^" + re.escape(f).replace(r"\*", ".*") + "$")
        out = [p for p in inv["packages"] if rx.match(p["name"]) or rx.match(relpath(p["dir"], root))
               or rx.match("./" + relpath(p["dir"], root))]
    return out


def parse_pm_command(pm: str, toks):
    value_flags = {"--filter", "-F", "--prefix", "-C", "--dir", "--cwd", "--workspace"}
    if pm == "npm":
        value_flags.add("-w")
    flt = cwd = None
    recursive = False
    sub, args, i = None, [], 0
    while i < len(toks):
        t = toks[i]
        if t in value_flags and i + 1 < len(toks):
            if t in ("--filter", "-F", "--workspace", "-w"):
                flt = toks[i + 1]
            else:
                cwd = toks[i + 1]
            i += 2
            continue
        if t.startswith(("--filter=", "--workspace=")):
            flt = t.split("=", 1)[1]
        elif t.startswith(("--prefix=", "--dir=", "--cwd=")):
            cwd = t.split("=", 1)[1]
        elif t in ("-r", "--recursive", "--workspaces", "-ws", "--all"):
            recursive = True
        elif t.startswith("-"):
            pass
        elif sub is None:
            sub = t
        else:
            args.append(t)
        i += 1
    if sub is None:
        return None
    script = None
    if pm == "npm":
        if sub in ("run", "run-script", "rum", "urn"):
            script = next((a for a in args if not a.startswith("-")), None)
        elif sub in NPM_SCRIPT_ALIASES:
            script = NPM_SCRIPT_ALIASES[sub]
        else:
            return None
    elif pm == "yarn":
        if sub == "workspace" and len(args) >= 2:
            flt = args[0]
            script = args[2] if args[1] == "run" and len(args) > 2 else args[1]
        elif sub == "run":
            script = args[0] if args else None
        elif sub in YARN_BUILTINS:
            return None
        else:
            script = sub
    elif pm == "pnpm":
        if sub == "run":
            script = args[0] if args else None
        elif sub in ("test", "t", "start"):
            script = "test" if sub == "t" else sub
        elif sub in PNPM_BUILTINS:
            return None
        else:
            script = sub
    elif pm == "bun":
        if sub == "run":
            script = args[0] if args else None
        elif sub in BUN_BUILTINS:
            return None
        else:
            script = sub
    if not script or not re.match(r"^[\w:.@/-]+$", script):
        return None
    return {"script": script, "filter": flt, "cwd": cwd, "recursive": recursive}


def split_rest(text: str):
    rest = re.split(r"&&|\|\||[|;\n`]", text)[0]
    toks = []
    for tok in rest.split():
        if tok in ("npm", "pnpm", "yarn", "bun", "npx", "pnpx", "bunx", "then", "and", "or",
                   "make", "just"):
            break
        end = tok.endswith((".", ","))
        tok = tok.rstrip(".,:;)")
        if tok:
            toks.append(tok)
        if end:
            break
    return toks


def make_targets(p: Path):
    targets = set()
    for line in (read_text(p) or "").splitlines():
        if line.startswith(("\t", " ", "#")):
            continue
        m2 = re.match(r"^\.PHONY\s*:\s*(.*)$", line)
        if m2:
            targets.update(m2.group(1).split())
            continue
        m = re.match(r"^([A-Za-z0-9_./%-][A-Za-z0-9_./% -]*?)\s*::?(?!=)", line)
        if m:
            for t in m.group(1).split():
                if "%" not in t and not t.startswith("."):
                    targets.add(t)
    return targets


def just_recipes(p: Path):
    out = set()
    for line in (read_text(p) or "").splitlines():
        m = re.match(r"^@?([A-Za-z0-9_-]+)(?:\s+[^:=\n]*)?:(?!=)", line)
        if m:
            out.add(m.group(1))
    return out


def nearest_file(start: Path, root: Path, names):
    cur = start
    while True:
        for n in names:
            if (cur / n).is_file():
                return cur / n
        if cur == root or cur == cur.parent:
            return None
        cur = cur.parent


def in_command_position(before: str) -> bool:
    s = before.rstrip()
    if not s:
        return True
    if s.endswith(("&&", "||", ";", "|", "(", "$", ">", "then", "do")):
        return True
    last = s.split()[-1]
    if last in ("sudo", "time", "env", "exec", "nohup", "-c", "run:", "-"):
        return True
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=\S*", last):
        return in_command_position(s[: len(s) - len(last)])
    return False


def check_commands(text: str, line_no: int, file_dir: Path, root: Path, inv, out, mentioned):
    text = re.sub(r"(?:^|\s)#\s.*$", "", text)  # drop shell comments
    for m in re.finditer(r"(?<![\w./@-])(npm|pnpm|yarn|bun)(?![\w-])", text):
        if not in_command_position(text[:m.start()]):
            continue
        pm = m.group(1)
        toks = split_rest(text[m.end():])
        mentioned.add(pm)
        parsed = parse_pm_command(pm, toks)
        if not parsed:
            continue
        cmd = short(pm + " " + " ".join(toks), 60)
        script = parsed["script"]
        cd = re.search(r"\bcd\s+(\S+)\s*&&\s*$", text[:m.start()])
        cwd = parsed["cwd"] or (cd.group(1) if cd else None)
        if not inv["packages"]:
            out.append({"line": line_no, "command": cmd,
                        "issue": "no package.json anywhere in the repo"})
            continue
        if parsed["recursive"]:
            pkgs = inv["packages"]
        elif parsed["filter"]:
            pkgs = packages_for_filter(parsed["filter"], inv, root)
            if not pkgs:
                out.append({"line": line_no, "command": cmd,
                            "issue": f'no workspace package matches "{parsed["filter"]}"'})
                continue
        elif cwd:
            pk = None
            for b in (file_dir, root):
                d, _ = resolve_case(b, cwd)
                if d is not None and (d / "package.json").is_file():
                    pk = next((p for p in inv["packages"] if p["dir"] == d), None)
                    break
            pkgs = [pk] if pk else []
            if not pkgs:
                out.append({"line": line_no, "command": cmd,
                            "issue": f"no package.json in {cwd}"})
                continue
        else:
            pk = nearest_package(file_dir, root, inv)
            pkgs = [pk] if pk else []
        if any(script in p["scripts"] for p in pkgs):
            continue
        if script == "start" and any((p["dir"] / "server.js").exists() for p in pkgs):
            continue
        if pm == "bun" and any((p["dir"] / script).exists() for p in pkgs):
            continue
        elsewhere = [p for p in inv["packages"] if script in p["scripts"]
                     and all(p is not q for q in pkgs)]
        avail = sorted({s for p in pkgs for s in p["scripts"]})
        where = ", ".join(relpath(p["path"], root) for p in pkgs) or "the nearest package.json"
        msg = f'no "{script}" script in {where}'
        close = difflib.get_close_matches(script, avail, n=2, cutoff=0.5)
        if close:
            msg += "; closest: " + ", ".join(close)
        if elsewhere:
            msg += ("; defined only in " + ", ".join(relpath(p["path"], root) for p in elsewhere[:3])
                    + " (say where to run it)")
        elif avail:
            msg += "; available: " + ", ".join(avail[:12])
        out.append({"line": line_no, "command": cmd, "issue": msg})

    for tool in ("make", "just"):
        for m in re.finditer(r"(?<![\w./-])%s(?![\w-])" % tool, text):
            if not in_command_position(text[:m.start()]):
                continue
            toks = split_rest(text[m.end():])
            d, target, custom, i = None, None, False, 0
            while i < len(toks):
                t = toks[i]
                if t in ("-C", "--directory", "-d", "--working-directory") and i + 1 < len(toks):
                    d = toks[i + 1]
                    i += 2
                    continue
                if t in ("-f", "--file", "--makefile", "--justfile"):
                    custom = True
                    break
                if t.startswith("-") or "=" in t:
                    i += 1
                    continue
                target = t
                break
            if custom or not target or not re.match(r"^[\w./-]+$", target):
                continue
            names = ("Makefile", "makefile", "GNUmakefile") if tool == "make" else (
                "justfile", "Justfile", ".justfile")
            start = file_dir
            if d:
                found, _ = resolve_case(file_dir, d)
                if found is None:
                    found, _ = resolve_case(root, d)
                start = found or file_dir
            mf = nearest_file(start, root, names)
            cmd = short(tool + " " + " ".join(toks), 60)
            if mf is None:
                out.append({"line": line_no, "command": cmd, "issue": f"no {names[0]} found"})
                continue
            known = make_targets(mf) if tool == "make" else just_recipes(mf)
            if target not in known:
                close = difflib.get_close_matches(target, sorted(known), n=2, cutoff=0.5)
                msg = f'no "{target}" target in {relpath(mf, root)}'
                if close:
                    msg += "; closest: " + ", ".join(close)
                out.append({"line": line_no, "command": cmd, "issue": msg})


# --------------------------------------------------------------------------- role

def detect_role(target: Path, root: Path, is_git: bool):
    name = target.name
    low = name.lower()
    if low.endswith(".sample"):
        low = low[:-7]
    parts = [p.lower() for p in target.parts]
    home_claude = Path.home() / ".claude"
    try:
        sub = target.parent.relative_to(root).as_posix()
    except ValueError:
        sub = target.parent.as_posix()
    at_root = target.parent == root or (target.parent.name == ".claude" and target.parent.parent == root)

    def r(kind, reach, bar):
        return {"kind": kind, "reach": reach, "bar": bar}

    if low in ("claude.md", "claude.local.md"):
        if target.parent == home_claude:
            return r("always-loaded instructions (user-level CLAUDE.md)",
                     "every Claude Code session, in every project", "strict")
        if low == "claude.local.md":
            return r("always-loaded personal instructions (CLAUDE.local.md)",
                     "every session of this user in this project", "strict")
        if at_root:
            return r("always-loaded project instructions (CLAUDE.md)",
                     "every Claude Code session in this repo", "strict")
        return r("scoped instructions (nested CLAUDE.md)",
                 f"sessions that work on files under {sub}/", "strict")
    if low in ("agents.md", "gemini.md"):
        tool = "AGENTS.md-aware agents (Codex and others)" if low == "agents.md" else "Gemini CLI"
        if at_root:
            return r(f"always-loaded project instructions ({name})",
                     f"every session of {tool} in this repo", "strict")
        return r(f"scoped instructions (nested {name})",
                 f"sessions of {tool} that work under {sub}/", "strict")
    if low == "copilot-instructions.md":
        return r("always-loaded instructions (GitHub Copilot)", "every Copilot request in this repo",
                 "strict")
    if low.endswith(".instructions.md") and ".github" in parts:
        return r("scoped instructions (Copilot, applyTo)", "Copilot requests on matching files",
                 "strict")
    if low in (".cursorrules", ".windsurfrules", ".clinerules", "conventions.md"):
        return r(f"always-loaded instructions ({name})", "every session of that tool in this repo",
                 "strict")
    if low.endswith(".mdc") and "rules" in parts:
        return r("Cursor rule (check alwaysApply/globs in frontmatter)",
                 "every request, or requests matching its globs", "strict")
    if low == "skill.md":
        return r("skill (SKILL.md)",
                 "name+description: every session; body: when the skill triggers; "
                 "references: on demand", "strict for frontmatter, standard for body")
    if any((anc / "SKILL.md").is_file() for anc in list(target.parents)[:3]):
        return r("skill reference file", "read when the skill's instructions point to it",
                 "standard")
    if ".claude" in parts and "commands" in parts:
        return r("slash command", "loaded when the command is invoked", "standard")
    if ".claude" in parts and "agents" in parts:
        return r("subagent definition", "loaded when the subagent runs", "standard")
    if low == "memory.md" or "memory" in parts:
        return r("memory / notes", "index usually loaded every session; entries on demand",
                 "standard")
    if low.startswith("readme"):
        return r("reference doc (README)", "read on demand; often the first file an agent opens",
                 "standard")
    if (low.startswith(("architecture", "design")) or "adr" in parts or "adrs" in parts
            or "decisions" in parts):
        return r("reference doc (architecture / decision record)", "read on demand", "standard")
    if low.startswith(("runbook", "playbook")) or "runbooks" in parts:
        return r("runbook", "read on demand, often under pressure", "standard")
    if low.startswith("contributing"):
        return r("reference doc (CONTRIBUTING)", "read on demand", "standard")
    if any(k in low for k in ("spec", "prd", "brief", "task", "plan", "prompt", "issue",
                              "requirement", "story", "ticket", "rfc")):
        return r("task brief / spec / prompt", "handed to an agent for a specific task",
                 "standard (strict on actionability)")
    return r("general Markdown (role unclear - infer it from content)", "unknown", "standard")


# --------------------------------------------------------------------------- analysis

def analyze(target: Path, root: Path, is_git: bool, shallow: bool) -> dict:
    text = read_text(target) or ""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    kinds, langs, blocks, headings, fm_end = parse_markdown(lines)
    files, truncated = walk(root, shallow)
    inv = build_inventory(root, files)
    role = detect_role(target, root, is_git)
    file_dir = target.parent
    is_claude = target.name.lower().split(".sample")[0] in ("claude.md", "claude.local.md")
    always_loaded = role["bar"].startswith("strict") and "skill" not in role["kind"]
    internal_only = shallow or role["kind"].startswith(("skill", "slash command", "subagent")) \
        or "user-level" in role["kind"]
    heading_text = " ".join(t for _, _, t in headings)

    fid = {"unresolved_refs": [], "case_mismatch": [], "broken_anchors": [], "imports": [],
           "commands": [], "version_claims": [], "pm_mismatch": None, "ci_mismatch": [],
           "staleness": [], "markers": [], "old_years": [], "git": {}, "drift": []}
    sec = {"secrets": [], "hidden_comments": [], "invisible": [], "risky": [],
           "untrusted_routing": [], "emails": []}
    cla = {"vague": {}, "ambiguous_refs": {}, "ambiguous_files": [], "acronyms": {}}
    act = {"prohibitions": [], "runaway": [], "missing": [], "verification_commands": []}
    eff = {"outline": section_outline(lines, headings), "duplicates": [], "generic": [],
           "emphasis": {"count": 0, "lines": []}, "large_blocks": [], "imports_tokens": 0,
           "neighbor_overlap": []}

    slugs = set()
    seen_slug: dict = {}
    for _, _, title in headings:
        s = gh_slug(title)
        if s in seen_slug:
            seen_slug[s] += 1
            slugs.add(f"{s}-{seen_slug[s]}")
        else:
            seen_slug[s] = 0
        slugs.add(s)

    refs_seen: dict = {}
    resolved_refs = []
    mentioned_pms: set = set()
    acr_defined: set = set()
    acr_hits: dict = {}
    norm_counts: dict = {}
    all_prose_norm = []

    def record_ref(tok, line_no, link=False):
        key = (tok, link)
        if key in refs_seen:
            refs_seen[key]["count"] += 1
            return
        status, detail = check_ref(tok, file_dir, root, inv, link=link, internal_only=internal_only)
        entry = {"line": line_no, "ref": tok, "count": 1}
        refs_seen[key] = entry
        if status == "missing":
            entry["hint"] = ("a file with this name exists at: " + ", ".join(detail)) if detail else ""
            fid["unresolved_refs"].append(entry)
        elif status == "case":
            entry["actual"] = detail
            fid["case_mismatch"].append(entry)
        elif status == "ambiguous":
            entry["matches"] = detail
            cla["ambiguous_files"].append(entry)
        elif status == "anchor":
            if detail and detail.lower() not in slugs:
                fid["broken_anchors"].append({"line": line_no, "ref": "#" + detail})
        elif status == "ok" and isinstance(detail, str) and not detail.startswith("~"):
            resolved_refs.append(detail)

    for i, line in enumerate(lines):
        ln = i + 1
        kind = kinds[i]
        # ---------- security: every line, whatever its kind
        scan_secrets_line(line, ln, sec["secrets"])
        for label, rx in RISKY_PATTERNS:
            for m in rx.finditer(line):
                if (label == "bypasses review" and m.group(0).lower().startswith("without")
                        and negated_in_clause(line, m.start())):
                    continue  # "don't merge without review" is a safeguard, not a bypass
                neg = negated_in_clause(line, m.start())
                sec["risky"].append({"line": ln, "kind": label, "text": short(m.group(0), 70),
                                     "note": "inside a prohibition - probably intended" if neg else ""})
                break
        if kind in ("prose", "frontmatter"):
            rm = STRONG_ROUTE_RE.search(line)
            if rm and UNTRUSTED_SRC_RE.search(line) and not negated_before(line, rm.start()):
                sec["untrusted_routing"].append({"line": ln, "text": short(line, 110)})
            for m in EMAIL_RE.finditer(re.sub(r"\b[a-z][a-z0-9+.\-]*://\S+", " ", line, flags=re.I)):
                if not m.group(1).lower().endswith(BENIGN_EMAIL_DOMAINS):
                    sec["emails"].append({"line": ln, "text": m.group(0)})

        if kind == "code":
            if langs[i] in SHELL_LANGS:
                check_commands(line, ln, file_dir, root, inv, fid["commands"], mentioned_pms)
                for tok in path_tokens(line):
                    record_ref(tok, ln)
            continue
        if kind == "fence":
            continue

        # ---------- prose and frontmatter
        spans = [m.group(2) for m in CODE_SPAN_RE.finditer(line)]
        for sp in spans:
            check_commands(sp, ln, file_dir, root, inv, fid["commands"], mentioned_pms)
            for tok in path_tokens(sp):
                record_ref(tok, ln)
        no_code = CODE_SPAN_RE.sub(" codespan ", line)
        for m in MD_LINK_RE.finditer(no_code):
            tgt = m.group(3)
            if tgt and not SCHEME_RE.match(tgt):
                record_ref(tgt, ln, link=True)
        rd = REF_DEF_RE.match(no_code)
        if rd and not SCHEME_RE.match(rd.group(2)):
            record_ref(rd.group(2), ln, link=True)
        prose = URL_RE.sub(" ", MD_LINK_RE.sub(lambda m: " " + m.group(2) + " ", no_code))
        prose_nc = COMMENT_RE.sub(" ", prose)
        for tok in path_tokens(prose_nc):
            record_ref(tok, ln)
        if is_claude:
            for m in IMPORT_RE.finditer(prose_nc):
                tok = m.group(1).rstrip(".,:;)")
                if not (EXT_RE.search(tok) or tok.startswith(("./", "../", "~/", "/"))):
                    continue
                p = Path(os.path.expanduser(tok)) if tok.startswith("~") else (file_dir / tok)
                if p.is_file():
                    toks = estimate_tokens(read_text(p) or "")
                    eff["imports_tokens"] += toks
                    fid["imports"].append({"line": ln, "ref": "@" + tok, "status": "ok",
                                           "tokens": toks})
                else:
                    fid["imports"].append({"line": ln, "ref": "@" + tok, "status": "missing"})

        # clarity (text in double quotes is being quoted or discussed, not used: skip it)
        prose_q = QUOTE_RE.sub(" quoted ", prose_nc)
        for m in VAGUE_RE.finditer(prose_q):
            cla["vague"].setdefault(m.group(1).lower(), []).append(ln)
        for m in AMBIG_RE.finditer(prose_q):
            phrase = re.sub(r"\s+", " ", m.group(0).lower())
            cla["ambiguous_refs"].setdefault(phrase, []).append(ln)
        letters = [c for c in prose_nc if c.isalpha()]
        shouting = letters and sum(c.isupper() for c in letters) / len(letters) > 0.5
        if not shouting:
            for m in ACRONYM_RE.finditer(prose_nc):
                a = m.group(1)
                if a in COMMON_ACRONYMS or a in SHOUTED_WORDS or a.isdigit():
                    continue
                tail = prose_nc[m.end():m.end() + 3]
                head = prose_nc[max(0, m.start() - 2):m.start()]
                if tail.startswith((" (", "(")) or head.endswith("(") or re.match(
                        r"^\s*(?:[-*]\s*)?\**%s\**\s*[:=\-–—]" % re.escape(a), prose_nc):
                    acr_defined.add(a)
                acr_hits.setdefault(a, []).append(ln)

        # actionability (quoted text is an example or a literal string, not a rule)
        neg = find_prohibition(prose_q)
        is_item = bool(re.match(r"^\s*(?:[-*+]|\d+[.)])\s", line))
        if neg and kind == "prose" and (is_item or len(prose_q) < 200):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            cont = nxt if re.match(r"^\s{2,}\S", nxt) and not re.match(r"^\s*[-*+]\s", nxt) else ""
            both = prose_q + " " + cont
            # Drop the clause that carries the prohibition; a positive instruction anywhere
            # else on the line counts as the alternative.
            s0 = max(prose_q.rfind(sep, 0, neg.start())
                     for sep in (". ", "; ", ", ", " - ", " — ", " – "))
            s0 = 0 if s0 < 0 else s0 + 1
            mend = re.search(r"[.!?;](?:\s|$)|\s[-—–]\s", prose_q[neg.end():])
            s1 = len(prose_q) if not mend else neg.end() + mend.end()
            rest = prose_q[:s0] + " " + prose_q[s1:] + " " + cont
            if not (ALT_RE.search(both) or WHY_RE.search(both) or POSITIVE_RE.search(rest)):
                act["prohibitions"].append({"line": ln, "text": short(line, 100)})
        for m in RUNAWAY_RE.finditer(prose_q):
            act["runaway"].append({"line": ln, "text": short(m.group(0), 60)})

        # efficiency
        for rx in GENERIC_RES:
            m = rx.search(prose_q)
            if m:
                eff["generic"].append({"line": ln, "text": short(m.group(0), 60)})
        e = len(EMPH_RE.findall(prose_q)) + len(BANG_RE.findall(prose_q))
        if e:
            eff["emphasis"]["count"] += e
            eff["emphasis"]["lines"].append(ln)
        if kind == "prose" and not HEADING_RE.match(line):
            nl = norm_line(line)
            if len(nl) >= 20:
                norm_counts.setdefault(nl, []).append(ln)
            if len(nl) >= 30:
                all_prose_norm.append((nl, ln))

        # fidelity: staleness signals
        sm = STALE_RE.findall(prose_q)
        if sm:
            fid["staleness"].append({"line": ln, "words": sorted({w.lower() for w in sm}),
                                     "text": short(line, 90)})
        mm = MARKER_RE.findall(QUOTE_RE.sub(" ", prose))
        if mm:
            fid["markers"].append({"line": ln, "text": short(line, 90)})
        if not re.search(r"(?i)copyright|©|\(c\)|licen[cs]e", prose_nc):
            for m in DATE_CTX_RE.finditer(prose_nc):
                year = m.group(1) or m.group(2)
                if int(year) <= TODAY.year - 1:
                    fid["old_years"].append({"line": ln, "year": year, "text": short(line, 90)})
                    break

    # Skills, user-level files, and shallow scans describe commands for other repos: keep real
    # mismatches against manifests that exist here, drop "nothing here to check against".
    if internal_only:
        fid["commands"] = [c for c in fid["commands"]
                           if not re.match(r"no package\.json anywhere|no \S+ found$", c["issue"])]

    # undefined acronyms
    for a, lns in acr_hits.items():
        if a not in acr_defined and not re.search(r"\b%s\b" % re.escape(a), heading_text):
            cla["acronyms"][a] = lns

    # duplicates within the file
    for nl, lns in norm_counts.items():
        if len(lns) > 1:
            eff["duplicates"].append({"lines": lns, "text": short(nl, 80)})

    # large code blocks (matter most in always-loaded files)
    for s, e_, lang in blocks:
        if e_ - s - 1 > 25:
            eff["large_blocks"].append({"line": s + 1, "length": e_ - s - 1, "lang": lang or "-"})

    # task-brief / instruction-file expectations
    body = "\n".join(l for l, k in zip(lines, kinds) if k in ("prose", "frontmatter"))
    if role["kind"].startswith("task brief"):
        if not GOAL_RE.search(body):
            act["missing"].append("no explicit goal / why")
        if not DONE_RE.search(body):
            act["missing"].append("no explicit definition of done / acceptance criteria")
        if not ESCALATE_RE.search(body):
            act["missing"].append("no 'when to stop and ask' guidance")
    verif_rx = re.compile(r"(?i)\b(test|tests|lint|check|verify|typecheck|type-check|build|ci)\b")
    tool_rx = re.compile(
        r"(?i)^\s*(?:\$\s*)?(?:[A-Za-z_]\w*=\S*\s+)*(?:npm|pnpm|yarn|bun|npx|make|just|pytest|go"
        r"|cargo|mvn|gradle|\./gradlew|tox|nox|uv|poetry|python3?|dotnet|rake|bundle|composer"
        r"|deno|ruff|mypy|tsc|eslint|vitest|jest|phpunit|swift|flutter|dart|mix|sbt)\b")

    def is_verification(cmd: str) -> bool:
        cmd = re.sub(r"(?:^|\s)#\s.*$", "", cmd)
        return bool(verif_rx.search(cmd) and tool_rx.search(cmd))

    for m in re.finditer(r"`([^`\n]+)`", text):
        if is_verification(m.group(1)):
            act["verification_commands"].append(short(m.group(1), 50))
    for s, e_, lang in blocks:
        if lang in SHELL_LANGS:
            for l in lines[s + 1:e_]:
                if is_verification(l):
                    act["verification_commands"].append(short(l.strip().lstrip("$ "), 50))
    act["verification_commands"] = sorted(set(act["verification_commands"]))[:8]
    if always_loaded and not act["verification_commands"] and "user-level" not in role["kind"]:
        act["missing"].append("no build/test/lint command an agent could run to check its work")

    # version claims vs repo declarations
    versions = repo_versions(root, inv)
    key_map = {"nodejs": "node", "node.js": "node", "golang": "go", "nextjs": "next",
               "next.js": "next", "postgresql": "postgres"}
    for i, line in enumerate(lines):
        if kinds[i] in ("fence",):
            continue
        for m in VERSION_CLAIM_RE.finditer(line):
            tech = m.group(1).lower().replace(" ", "")
            key = key_map.get(tech, tech)
            if key in versions:
                verdicts = [version_consistent(m.group(2), d.split("=", 1)[1])
                            for d in versions[key]]
                # Report disagreements, and claims nothing in the repo can confirm.
                if any(v is False for v in verdicts) or all(v is None for v in verdicts):
                    fid["version_claims"].append({"line": i + 1, "claim": m.group(0).strip(),
                                                  "repo": versions[key]})

    # package-manager consistency
    lock_pms = {LOCKFILES[p.name] for p in inv["lockfiles"]}
    for pkg in inv["packages"]:
        pm = pkg["packageManager"]
        if isinstance(pm, str) and "@" in pm and pkg["dir"] == root:
            lock_pms.add(pm.split("@", 1)[0])
    if lock_pms and mentioned_pms - lock_pms:
        fid["pm_mismatch"] = {"file_uses": sorted(mentioned_pms),
                              "repo_declares": sorted(lock_pms),
                              "evidence": sorted({relpath(p, root) for p in inv["lockfiles"]})}

    # CI consistency
    mentioned_ci = {m.group(1).lower() for m in CI_MENTION_RE.finditer(text)}
    present = {c.lower() for c in inv["ci"]}
    for c in sorted(mentioned_ci):
        canon = {"gitlab-ci": "gitlab ci", "gitlab pipeline": "gitlab ci",
                 "gitlab pipelines": "gitlab ci", "circle ci": "circleci", "travis": "travis ci"
                 }.get(c, c)
        if present and canon not in present:
            fid["ci_mismatch"].append({"mentioned": c, "repo_has": sorted(inv["ci"])})

    # git freshness and drift
    if is_git:
        relt = relpath(target, root)
        last = run_git(root, "log", "-1", "--format=%H|%ct|%cs", "--", relt)
        status = run_git(root, "status", "--porcelain", "--", relt)
        g = {"tracked": bool(last), "status": status or "clean"}
        if last:
            h, ts, ds = last.split("|")
            g["last_commit"] = ds
            g["commits_since"] = run_git(root, "rev-list", "--count", f"{h}..HEAD")
            seen = set()
            if status:
                # Uncommitted edits (e.g. the update this skill just made): the last commit
                # date no longer describes the working copy, so drift would be noise.
                g["drift_skipped"] = True
            for ref in ([] if status else resolved_refs):
                if ref in seen or len(seen) >= 25:
                    continue
                seen.add(ref)
                rl = run_git(root, "log", "-1", "--format=%ct|%cs", "--", ref)
                if rl and int(rl.split("|")[0]) > int(ts):
                    fid["drift"].append({"ref": ref, "changed": rl.split("|")[1]})
        fid["git"] = g

    # hidden content
    for m in COMMENT_RE.finditer(text):
        ln = text.count("\n", 0, m.start()) + 1
        if ln - 1 < len(kinds) and kinds[ln - 1] == "code":
            continue
        body_c = m.group(1)
        label = "tool directive / marker (likely benign)" if BENIGN_COMMENT_RE.match(body_c) else (
            "addressed to agents - invisible to anyone reading the rendered file"
            if AGENT_ADDRESSED_RE.search(body_c) else "hidden comment")
        sec["hidden_comments"].append({"line": ln, "kind": label, "text": short(body_c, 110)})
    scan_invisible(lines, sec["invisible"])

    # neighbors and overlap
    neighbors = [p for p in inv["context_files"] if p.resolve() != target]
    user_claude = Path.home() / ".claude" / "CLAUDE.md"
    if user_claude.is_file() and user_claude.resolve() != target and not shallow:
        neighbors.append(user_claude)
    target_norm = {}
    for nl, ln in all_prose_norm:
        target_norm.setdefault(nl, ln)
    for nb in neighbors[:15]:
        try:
            if nb.stat().st_size > 300_000:
                continue
        except OSError:
            continue
        shared = []
        for l in (read_text(nb) or "").splitlines():
            nl = norm_line(l)
            if len(nl) >= 30 and nl in target_norm:
                shared.append(target_norm[nl])
        if shared:
            eff["neighbor_overlap"].append({"file": relpath(nb, root),
                                            "lines": sorted(set(shared))})

    words = len(re.findall(r"\S+", text))
    return {
        "file": relpath(target, root) if not shallow else target.as_posix(),
        "role": role,
        "size": {"lines": len(lines), "words": words, "tokens": estimate_tokens(text)},
        "repo": {
            "root": root.as_posix(), "git": is_git, "shallow_scan": shallow,
            "walk_truncated": truncated,
            "packages": [{"name": p["name"], "path": relpath(p["path"], root),
                          "scripts": sorted(p["scripts"])} for p in inv["packages"]][:15],
            "lockfiles": sorted({relpath(p, root) for p in inv["lockfiles"]}),
            "ci": inv["ci"], "ci_jobs": inv["ci_jobs"][:15],
            "compose_services": inv["compose_services"][:15],
            "manifests": sorted(set(inv["manifests"])), "top_dirs": inv["top_dirs"],
            "versions": versions,
        },
        "fidelity": fid, "security": sec, "clarity": cla, "actionability": act,
        "efficiency": eff,
        "neighbors": [relpath(p, root) for p in neighbors][:20],
    }


def mask(s: str) -> str:
    s = s.strip()
    return (s[:4] if len(s) > 8 else s[:1]) + f"… ({len(s)} chars)"


def scan_secrets_line(line: str, ln: int, out):
    spans = []
    for label, rx in SECRET_PATTERNS:
        for m in rx.finditer(line):
            a, b = m.span()
            if any(a < y and x < b for x, y in spans):
                continue
            note = ""
            if label == "secret-looking assignment":
                val = m.group(2)
                if PLACEHOLDER_RE.match(val) or val.startswith(("$", "%", "{", "<", "process.env",
                                                                 "os.environ", "env(")):
                    continue
                shown = f"{m.group(1)}={mask(val)}"
            elif label == "credentials in URL":
                pw, host = m.group(2), m.group(3)
                if PLACEHOLDER_RE.match(pw) or pw.startswith(("$", "{", "<", "%")):
                    continue
                shown = m.group(0).replace(":" + pw + "@", ":****@", 1)
                if host.lower() in LOCAL_HOSTS:
                    note = "local dev URL - confirm it is not a real credential"
            else:
                shown = mask(m.group(0))
            spans.append((a, b))
            out.append({"line": ln, "kind": label, "shown": short(shown, 90), "note": note})


def scan_invisible(lines, out):
    for i, line in enumerate(lines):
        found, decoded, j, n = {}, "", 0, len(line)
        while j < n:
            cp = ord(line[j])
            if 0xE0000 <= cp <= 0xE007F:
                k = j
                while k < n and 0xE0000 <= ord(line[k]) <= 0xE007F:
                    k += 1
                is_flag = j > 0 and ord(line[j - 1]) == 0x1F3F4
                if not is_flag:
                    found["TAG characters (can smuggle hidden ASCII text)"] = \
                        found.get("TAG characters (can smuggle hidden ASCII text)", 0) + (k - j)
                    decoded += "".join(chr(ord(c) - 0xE0000) for c in line[j:k]
                                       if 0xE0020 <= ord(c) <= 0xE007E)
                j = k
                continue
            if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
                k = j
                while k < n and (0xFE00 <= ord(line[k]) <= 0xFE0F or 0xE0100 <= ord(line[k]) <= 0xE01EF):
                    k += 1
                if k - j >= 2:
                    key = "run of variation selectors (can smuggle hidden data)"
                    found[key] = found.get(key, 0) + (k - j)
                j = k
                continue
            if cp == 0x200D:
                prev_c = line[j - 1] if j > 0 else " "
                next_c = line[j + 1] if j + 1 < n else " "
                if ord(prev_c) < 128 and ord(next_c) < 128:
                    found["ZERO WIDTH JOINER between plain characters"] = \
                        found.get("ZERO WIDTH JOINER between plain characters", 0) + 1
            elif cp in INVISIBLE_CPS and not (cp == 0xFEFF and i == 0 and j == 0):
                key = unicodedata.name(line[j], f"U+{cp:04X}")
                found[key] = found.get(key, 0) + 1
            elif cp in BIDI_CPS:
                key = "bidi control " + unicodedata.name(line[j], f"U+{cp:04X}") + \
                      " (legitimate only in right-to-left text)"
                found[key] = found.get(key, 0) + 1
            j += 1
        if found:
            out.append({"line": i + 1,
                        "chars": [f"{k} x{v}" for k, v in found.items()],
                        "decoded": short(decoded, 120) if decoded else ""})


# --------------------------------------------------------------------------- output

def render(r: dict, max_items: int) -> str:
    cap = max_items if max_items > 0 else 10 ** 9
    out = []
    w = out.append

    def lst(title, items, fmt):
        if not items:
            return
        w(f"  {title}")
        for it in items[:cap]:
            w("    " + fmt(it))
        if len(items) > cap:
            w(f"    ... +{len(items) - cap} more")

    def lines_str(lns, k=6):
        uniq = sorted(set(lns))
        s = ", ".join(f"L{x}" for x in uniq[:k])
        return s + (f" +{len(uniq) - k}" if len(uniq) > k else "")

    role, size, repo = r["role"], r["size"], r["repo"]
    w(f"good-context lint: {r['file']}")
    w(f"Role (guessed from name/location): {role['kind']}")
    w(f"Reach: {role['reach']}  |  review bar: {role['bar']}")
    w(f"Size: {size['lines']} lines, {size['words']} words, ~{size['tokens']} tokens (rough)")
    g = r["fidelity"]["git"]
    scope = "git repo" if repo["git"] else ("no git; shallow scan" if repo["shallow_scan"]
                                            else "no git")
    gline = f"Repo root: {repo['root']} ({scope})"
    if g:
        if g.get("tracked"):
            gline += (f"  |  file last committed {g['last_commit']}; "
                      f"repo commits since then: {g.get('commits_since', '?')}")
        else:
            gline += "  |  file not committed yet"
        if g.get("status") and g["status"] != "clean":
            gline += f"  |  working tree: {g['status'].split()[0]}"
    w(gline)
    if repo["walk_truncated"]:
        w(f"Note: repo walk stopped at {MAX_WALK_FILES} files; repo-wide checks are partial.")
    inv_bits = []
    if repo["packages"]:
        inv_bits.append("packages: " + ", ".join(
            f"{p['name'] or '(unnamed)'} ({p['path']})" for p in repo["packages"][:8]))
    if repo["lockfiles"]:
        inv_bits.append("lockfiles: " + ", ".join(repo["lockfiles"][:4]))
    if repo["ci"]:
        inv_bits.append("CI: " + ", ".join(repo["ci"]) + (
            f" (jobs: {', '.join(repo['ci_jobs'][:8])})" if repo["ci_jobs"] else ""))
    if repo["compose_services"]:
        inv_bits.append("compose services: " + ", ".join(repo["compose_services"]))
    if repo["top_dirs"]:
        inv_bits.append("top-level dirs: " + ", ".join(repo["top_dirs"][:15]))
    if inv_bits:
        w("Repo inventory: " + " | ".join(inv_bits))

    f = r["fidelity"]
    w("")
    w("FIDELITY - is it true today?")
    lst("References that don't resolve (stale? moved? generated?):", f["unresolved_refs"],
        lambda e: f"L{e['line']}  {e['ref']}" + (f" (x{e['count']})" if e["count"] > 1 else "")
        + (f"  - {e['hint']}" if e.get("hint") else ""))
    lst("Case mismatch (works on Windows/macOS, breaks on Linux and cloud agents):",
        f["case_mismatch"], lambda e: f"L{e['line']}  {e['ref']} -> on disk: {e['actual']}")
    lst("Broken in-file anchors:", f["broken_anchors"], lambda e: f"L{e['line']}  {e['ref']}")
    lst("@imports (loaded eagerly into every session):", f["imports"],
        lambda e: f"L{e['line']}  {e['ref']}  " + (f"~{e['tokens']} tokens" if e["status"] == "ok"
                                                    else "MISSING - import fails silently"))
    lst("Commands that don't match the repo:", f["commands"],
        lambda e: f"L{e['line']}  `{e['command']}` - {e['issue']}")
    if f["pm_mismatch"]:
        pmm = f["pm_mismatch"]
        w(f"  Package manager: file uses {', '.join(pmm['file_uses'])}; repo declares "
          f"{', '.join(pmm['repo_declares'])} ({', '.join(pmm['evidence']) or 'packageManager field'})")
    lst("Version claims vs what the repo declares:", f["version_claims"],
        lambda e: f"L{e['line']}  \"{e['claim']}\"  - repo: {'; '.join(e['repo'][:4])}")
    lst("CI named in the file but not found in the repo:", f["ci_mismatch"],
        lambda e: f"\"{e['mentioned']}\" - repo has: {', '.join(e['repo_has'])}")
    lst("Staleness wording (still true?):", f["staleness"],
        lambda e: f"L{e['line']}  [{', '.join(e['words'])}] {e['text']}")
    lst("Dated statements:", f["old_years"], lambda e: f"L{e['line']}  ({e['year']}) {e['text']}")
    lst("Open markers (TODO/TBD/FIXME):", f["markers"], lambda e: f"L{e['line']}  {e['text']}")
    lst("Referenced paths changed after this file's last commit (may have drifted):", f["drift"],
        lambda e: f"{e['ref']} (changed {e['changed']})")
    if g.get("drift_skipped"):
        w("  Drift check skipped: the file has uncommitted changes.")

    s = r["security"]
    w("")
    w("SECURITY - should the agent have this at all?")
    lst("Possible secrets (masked):", s["secrets"],
        lambda e: f"L{e['line']}  {e['kind']}: {e['shown']}" + (f"  [{e['note']}]" if e["note"] else ""))
    lst("Hidden HTML comments:", s["hidden_comments"],
        lambda e: f"L{e['line']}  {e['kind']}: \"{e['text']}\"")
    lst("Invisible / control characters:", s["invisible"],
        lambda e: f"L{e['line']}  {'; '.join(e['chars'])}"
        + (f"  decoded hidden text: \"{e['decoded']}\"" if e["decoded"] else ""))
    lst("Untrusted content routed into instructions:", s["untrusted_routing"],
        lambda e: f"L{e['line']}  {e['text']}")
    lst("Risky instructions (check the context):", s["risky"],
        lambda e: f"L{e['line']}  {e['kind']}: \"{e['text']}\"" + (f"  [{e['note']}]" if e["note"] else ""))
    lst("Email addresses (needed here?):", s["emails"], lambda e: f"L{e['line']}  {e['text']}")

    c = r["clarity"]
    w("")
    w("CLARITY - can it be read only one way?")
    amb = sorted(c["ambiguous_refs"].items(), key=lambda kv: -len(kv[1]))
    lst("References that may match more than one thing (check the repo):", amb,
        lambda kv: f"\"{kv[0]}\" x{len(kv[1])} ({lines_str(kv[1])})")
    lst("Bare file names that match several files:", c["ambiguous_files"],
        lambda e: f"L{e['line']}  {e['ref']} -> {', '.join(e['matches'])}")
    vag = sorted(c["vague"].items(), key=lambda kv: -len(kv[1]))
    lst("Vague wording (matters only where the task turns on it):", vag,
        lambda kv: f"\"{kv[0]}\" x{len(kv[1])} ({lines_str(kv[1])})")
    acr = sorted(c["acronyms"].items(), key=lambda kv: -len(kv[1]))
    lst("Terms an outsider may not know (undefined acronyms):", acr,
        lambda kv: f"{kv[0]} x{len(kv[1])} ({lines_str(kv[1], 3)})")

    a = r["actionability"]
    w("")
    w("ACTIONABILITY - can it proceed and know when it's done?")
    lst("Missing for this kind of file:", a["missing"], lambda e: e)
    lst("Prohibitions with no alternative and no reason:", a["prohibitions"],
        lambda e: f"L{e['line']}  {e['text']}")
    lst("Open-ended loops (no stop condition or budget):", a["runaway"],
        lambda e: f"L{e['line']}  \"{e['text']}\"")
    if a["verification_commands"]:
        w("  Verification commands found: " + "; ".join(a["verification_commands"]))

    e = r["efficiency"]
    w("")
    w("EFFICIENCY - can it focus on what matters?")
    if e["outline"]:
        w("  Outline (~tokens per section):")
        for o in e["outline"][:40]:
            indent = "  " * max(0, o["level"] - 1)
            w(f"    L{o['line']:<4} {indent}{'#' * o['level']} {short(o['title'], 60)}  ~{o['tokens']}")
        if len(e["outline"]) > 40:
            w(f"    ... +{len(e['outline']) - 40} more headings")
    if e["imports_tokens"]:
        w(f"  @imports add ~{e['imports_tokens']} tokens to every session that loads this file")
    lst("Duplicate lines:", e["duplicates"], lambda d: f"{lines_str(d['lines'])}  \"{d['text']}\"")
    lst("Generic advice the agent follows anyway (costs tokens, adds nothing):", e["generic"],
        lambda d: f"L{d['line']}  \"{d['text']}\"")
    if e["emphasis"]["count"]:
        w(f"  Emphasis: {e['emphasis']['count']} ALL-CAPS imperatives / '!!' "
          f"({lines_str(e['emphasis']['lines'], 8)}) - when everything is urgent, nothing is")
    lst("Large code blocks:", e["large_blocks"],
        lambda d: f"L{d['line']}  {d['length']} lines ({d['lang']})")
    lst("Lines duplicated in neighbor files (two copies drift apart):", e["neighbor_overlap"],
        lambda d: f"{d['file']}: {lines_str(d['lines'])}")

    if r["neighbors"]:
        w("")
        w("NEIGHBORS - other context files that may load alongside or overlap:")
        w("  " + ", ".join(r["neighbors"][:20]))
    w("")
    w("Leads, not verdicts: confirm each one in the file and the repo before reporting it.")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mechanical evidence for a CAFE(S) context review.")
    ap.add_argument("file", help="Markdown (or other text) file that agents read")
    ap.add_argument("--repo-root", help="repository the file describes (default: auto-detect)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--max-items", type=int, default=12,
                    help="max items per category in text output (0 = no limit)")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    raw = args.file.strip().strip("\"'")
    if raw.startswith("@"):
        raw = raw[1:]
    target = Path(os.path.expanduser(raw))
    if not target.is_file():
        print(f"error: not a file: {target}", file=sys.stderr)
        return 2
    target = target.resolve()
    root, is_git, shallow = find_root(target, args.repo_root)
    report = analyze(target, root, is_git, shallow)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print(render(report, args.max_items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
