# Security Policy

The Wisdom Layer SDK is cognitive-architecture middleware that lives inside
customer applications and handles memory, directives, LLM routing, and cost
tracking on behalf of those applications. It is an in-process library, not
a hosted service -- customers choose where it runs, what data it touches,
and which LLM providers it calls.

---

## Supported Versions

| Version | Status | Security fixes |
|---|---|---|
| `1.0.x` | Current | Yes |
| `0.9.x` | Previous | Yes (until `1.1.0` ships) |
| `< 0.9` | Pre-release | No |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue, pull request, or discussion about
a suspected vulnerability.**

### Contact

- **Email:** `security@wisdomlayer.ai`
- **GitHub Security Advisories:** use the "Report a vulnerability" button
  in the repository's Security tab

### What to include

- Description of the vulnerability and the affected component
- SDK version the vulnerability was observed in
- Minimal reproduction (smallest code sample demonstrating the issue)
- Impact assessment (what an attacker could do)
- Any known mitigations or workarounds

### What happens next

1. **Acknowledgement within 72 hours.**
2. **Triage within 7 days.** Severity classified via CVSS 3.1.
3. **Coordinated disclosure.** Default 90-day window from validation.
4. **Fix and release.** Patch release to current supported versions.
5. **Advisory.** GitHub Security Advisory published, CHANGELOG.md updated.

### Out of scope

- Bugs in customer code (e.g., passing unsanitized input to `capture()`)
- Bugs in customer-selected backends (e.g., Postgres with `sslmode=disable`)
- Bugs in customer-supplied LLM adapters (custom `BaseLLMAdapter` subclasses)
- Denial of service via valid API usage (capacity planning, not security)
- Missing security hardening documented as customer responsibility

### In scope

Memory tampering, directive injection, privilege escalation across
`PermissionManager` boundaries, cross-agent data leakage, snapshot/export
integrity violations, SQL injection in first-party backends, deserialization
vulnerabilities in config/snapshot loaders, and any vulnerability that lets
test fixtures escape into production code.

---

## Threat Model Summary

The SDK is a **trusted library** inside an **untrusted deployment**. It
assumes the host application authenticates its own operators, the storage
backend enforces its own access controls, and the LLM provider is an
untrusted external service. Inside those assumptions, the SDK keeps agents
isolated from each other, permissions tight, determinism local, costs
bounded, deletions auditable, and process boundaries honest.

---

## Data Subject Requests (GDPR)

Three idempotent delete primitives for Article 17 (Right to Erasure):

- `memory.delete(memory_id)` -- single-row hard delete
- `memory.delete_session(session_id)` -- session-scoped erasure
- `memory.delete_all()` -- full agent erasure (scoped to this agent)

All emit audit events on the CRITICAL delivery tier. The SDK provides the
primitives; the customer composes them into their compliance workflow.

Subject access (Article 15) and portability (Article 20) are served by
`agent.snapshot()`, `memory.export()`, and `agent.provenance.trace()`.

---

## Secure Defaults

- **No network at import time.** I/O starts at `agent.initialize()`.
- **Telemetry policy.** No memory content, prompts, agent data, or PII
  ever leaves the host. The Free tier sends a small daily anonymous
  count-payload (~600 bytes — install ID, SDK version, agent / memory /
  message counts, OS, Python major.minor) to
  `api.wisdomlayer.ai/v1/telemetry`. Pro and Enterprise are silent by
  default; opt-in via `WL_TELEMETRY=1`. Free disables with
  `WL_TELEMETRY=0`. Endpoint override via `WL_TELEMETRY_ENDPOINT`.
  Full schema, retention, and audit notes:
  [docs/telemetry.md](docs/telemetry.md).
- **No bundled secrets.** All samples use `os.environ[...]` for keys.
- **Deterministic time in tests.** `FrozenClock` by default in test fixtures.
- **PermissionManager is required.** Every mutating primitive checks permissions.
- **Strictest-mode-wins merging.** Conflicting configs resolve to the stricter value.
- **Conservative cost caps.** Dream cycles default to budget limits that err on refusal.

---

## Security Contacts

- **Primary:** `security@wisdomlayer.ai`
- **Fallback:** GitHub Security Advisories on this repository
