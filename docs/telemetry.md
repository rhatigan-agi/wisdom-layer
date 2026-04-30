# Anonymous Usage Telemetry

The Wisdom Layer SDK collects **anonymous, opt-out usage telemetry** on
the Free tier and **opt-in only** on Pro and Enterprise. This page is
the full disclosure of what is sent, when, where, and how to disable it.

> **TL;DR:** Counts only — never content, never PII. One small JSON
> POST per day, per machine. Set `WL_TELEMETRY=0` to disable. Pro and
> Enterprise are silent by default.

---

## Why we collect it

Wisdom Layer is a venture-backed company building durable infrastructure
for agent memory. Investor diligence and product direction both require
honest answers to questions like: *how many people are using the SDK?
how many agents are in the field? how many messages per day?* The
options are (1) make those numbers up, (2) gate them behind sign-up
walls, or (3) collect anonymous counts from the Free tier with prominent
disclosure. We do (3).

Pro and Enterprise customers buy privacy — telemetry is off by default
on those tiers, and the SDK does not phone home for license-shape,
deployment-shape, or any other operational metric beyond license-key
validation.

---

## Defaults by tier

| Tier | Default | Override |
|---|---|---|
| Free (anonymous, no key) | **On** | `WL_TELEMETRY=0` |
| Free (registered key) | **On** | `WL_TELEMETRY=0` |
| Pro | **Off** | `WL_TELEMETRY=1` (opt-in) |
| Enterprise | **Off** | `WL_TELEMETRY=1` (opt-in) |
| Trial (14-day Pro on signup) | **Off** | `WL_TELEMETRY=1` (opt-in) |

The framing: *Free participates in the project; Pro and Enterprise pay
for privacy.*

---

## What is sent

The full payload, exactly as transmitted:

```json
{
  "payload_version": 1,
  "install_id": "550e8400-e29b-41d4-a716-446655440000",
  "ts": "2026-04-29T18:23:51Z",
  "version": "1.1.0",
  "tier": "free",
  "agent_count": 3,
  "memory_count": 1247,
  "msg_count_30d": 412,
  "fact_count": 89,
  "dream_cycles_count": 4,
  "directive_count": 17,
  "os": "linux",
  "python_version": "3.11"
}
```

### Field-by-field

| Field | Type | What it is |
|---|---|---|
| `payload_version` | int | Schema version. Currently `1`. |
| `install_id` | UUIDv4 | Random ID generated once per install at `~/.wisdom_layer/install_id`. **Not** tied to your identity, license key, email, or hardware fingerprint. |
| `ts` | ISO-8601 UTC | When this batch was sent. |
| `version` | string | SDK version (e.g., `1.1.0`). |
| `tier` | enum | `free` / `pro` / `enterprise` / `trial`. |
| `agent_count` | int | Number of active agents at send time. |
| `memory_count` | int | Total memories across all agents on this install. |
| `msg_count_30d` | int | Rolling 30-day message count. |
| `fact_count` | int | Total atomic facts extracted (always `0` on Free, since fact extraction is a Pro feature). |
| `dream_cycles_count` | int | Total dream cycles run since install. |
| `directive_count` | int | Number of active directives. |
| `os` | string | `linux` / `darwin` / `win32`. No version detail. |
| `python_version` | string | Major.minor only (e.g., `3.11`). No patch level. |

### What the payload does **not** carry

- **No memory content.** Not the text, not summaries, not embeddings.
- **No event content.** Not LLM prompts, not LLM responses, not session
  contents.
- **No agent names, directive text, or fact text.**
- **No usernames, hostnames, or file paths.**
- **No IP address.** The receiving server may temporarily see source IP
  for transport-level rate-limiting; it is not retained.
- **No license key or `key_id`.** The `install_id` is generated client-
  side and is not derived from your license.
- **No PII of any kind.**

If you suspect the payload sent from your install differs from this
schema, please report it via [security@wisdomlayer.ai](mailto:security@wisdomlayer.ai)
and we will treat it as a privacy bug.

---

## When and how it's sent

- **Daily batch.** One `POST` per 24-hour period.
- **Endpoint.** `https://api.wisdomlayer.ai/v1/telemetry`. Override
  with `WL_TELEMETRY_ENDPOINT` if you proxy outbound traffic.
- **Method.** `POST application/json`. No auth header.
- **Trigger.** On agent close, or every 24h via a lightweight
  background task — whichever happens first.
- **Cadence math.** Roughly **600 bytes per day** of outbound traffic
  per install. That is ~220 KB per year.
- **Async, fire-and-forget.** Telemetry never blocks any agent
  operation. Endpoint failures are silent — no retries, no warnings, no
  error in agent return paths.

If the endpoint is unreachable for an extended period, the daily batch
is dropped and the next batch reflects current state. Missing batches
do not accumulate to disk; the SDK does not persist queued telemetry.

---

## How to disable

### Environment variable (recommended)

```bash
export WL_TELEMETRY=0
```

Setting `WL_TELEMETRY=0` in your shell, container env, or process
launcher disables telemetry for that process. The SDK reads this every
run; there is no cached state.

For a system-wide opt-out on a developer workstation, add the export to
your `~/.bashrc` / `~/.zshrc` / equivalent.

### Container / production

Add `WL_TELEMETRY=0` to your container env:

```dockerfile
ENV WL_TELEMETRY=0
```

```yaml
# docker-compose.yml
services:
  app:
    environment:
      WL_TELEMETRY: "0"
```

```yaml
# kubernetes
env:
  - name: WL_TELEMETRY
    value: "0"
```

### Endpoint override (proxy / air-gap)

If your environment forbids outbound HTTPS to `api.wisdomlayer.ai` but
you want telemetry to keep working through an internal forward proxy,
set:

```bash
export WL_TELEMETRY_ENDPOINT=https://your-proxy.internal/wisdom-telemetry
```

In fully air-gapped deployments, simply set `WL_TELEMETRY=0`.

---

## First-run disclosure

On the **first run** of the SDK on a machine — the first time
`WisdomAgent` is constructed and a new `install_id` is generated — the
SDK logs once at `INFO`:

```
[wisdom_layer] First run — anonymous usage telemetry enabled (counts
              only, no content, no PII).
              Disable: WL_TELEMETRY=0
              Details: https://wisdomlayer.ai/docs/telemetry
```

This message is structurally coupled to `install_id` creation — it
cannot be silently skipped. Subsequent runs do not re-emit the
disclosure.

If your application captures Python `INFO` logs into a structured log
sink, this entry will appear once per machine and never again.

---

## Data retention

- **Raw telemetry records.** Retained for **12 months** after
  `received_at`, then deleted.
- **Aggregated rollups** (daily / weekly counts, no per-install rows).
  Retained indefinitely; used for headline metrics and historical
  trend lines.
- **Opt-out wipe.** If you want all records associated with your
  `install_id` deleted, email
  [privacy@wisdomlayer.ai](mailto:privacy@wisdomlayer.ai) with the ID
  (the contents of `~/.wisdom_layer/install_id`). Records are deleted
  within 30 days. Because `install_id` is not normally tied to your
  identity, this requires you to surface the ID yourself.

---

## What changes if Pro / Enterprise opts in

Setting `WL_TELEMETRY=1` on a Pro or Enterprise license sends the same
payload schema described above — same fields, same endpoint, same
cadence. The `tier` field reflects `pro` or `enterprise` so we can
filter Pro/Enterprise payloads out of headline aggregate metrics by
default.

This is uncommon and considered a goodwill gesture from the customer.
There is no pricing discount for opting in.

---

## Security review notes

For enterprise security review:

- **Outbound destination.** Single endpoint, `api.wisdomlayer.ai/v1/telemetry`,
  TLS only. Override with `WL_TELEMETRY_ENDPOINT`.
- **Outbound volume.** ~600 bytes/day per install.
- **Payload contents.** See [What is sent](#what-is-sent). Schema is
  versioned via `payload_version`.
- **Off by default on Pro/Enterprise.** See [Defaults by tier](#defaults-by-tier).
- **Disable.** `WL_TELEMETRY=0`. No restart required beyond the next
  process spawn.
- **Audit.** The relevant code lives in `wisdom_layer/_telemetry.py`
  in the installed wheel and is not Cython-compiled. You can inspect it
  directly:
  ```bash
  python -c "import wisdom_layer._telemetry; print(wisdom_layer._telemetry.__file__)"
  ```

If your security review requires a sworn statement of contents or a
DPA, contact [jeff@rhatigan.ai](mailto:jeff@rhatigan.ai).

---

## Changes to this policy

Material changes to telemetry — new fields, changed cadence, new
endpoint — will:

1. Bump `payload_version` so older clients are visibly distinguishable.
2. Land in a minor or major SDK version, never in a patch release.
3. Be called out in the [CHANGELOG](../CHANGELOG.md) under a `### Telemetry`
   subsection.
4. Trigger a new first-run disclosure log line.

We do not retroactively change what existing payloads carry.

---

## Cross-references

- [Tier matrix](tiers.md) — what Free / Pro / Enterprise include.
- [Quickstart](quickstart.md) — getting started, including the
  `WL_TELEMETRY=0` flag.
- [Configuration](config.md) — full env-var reference.
- [SECURITY.md](../SECURITY.md) — broader secure-defaults posture.
- [EULA.md](../EULA.md) — legal terms covering telemetry and tier
  acceptance.
