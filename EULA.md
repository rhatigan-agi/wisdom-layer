# Wisdom Layer End User License Agreement

> The operative legal terms live in `LICENSE` at the repo root and
> ship in every release wheel. This Markdown version exists so the
> docs site at `wisdomlayer.ai/terms` can render the same text in
> a readable form.

**Copyright (c) 2026 Rhatigan AGI LLC (d/b/a Rhatigan Labs). All rights reserved.**

## 1. Summary

The Wisdom Layer SDK is commercial software. Installing it from PyPI
or any other source means you agree to the terms in this document.
One commercial license governs both the free and paid tiers --
your license key determines which tier of features you can use at
runtime, not whether you agree to the license itself.

## 2. What you can do

- Install Wisdom Layer into your own applications.
- Use it for personal, evaluation, or commercial purposes, within
  the limits of your active tier (Free / Pro / Team / Business /
  Enterprise).
- Ship your own product that integrates Wisdom Layer, provided you
  do not redistribute the Wisdom Layer wheel itself.

## 3. What you cannot do

- Reverse-engineer, decompile, disassemble, or otherwise extract
  source code from the compiled `_internal/` modules.
- Redistribute, sublicense, lease, sell, or host the Wisdom Layer
  wheel (or any derivative) to third parties.
- Remove, disable, or circumvent license-check or tier-enforcement
  code.
- Modify the SDK to misrepresent its tier, version, or origin.

## 4. Tier limits

- **Free Tier.** Runtime limits and capacity caps are documented at
  [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing) and in
  `docs/tiers.md`. The Free tier is licensed for personal projects,
  evaluation, learning, and internal exploration. It is **not licensed
  for commercial production deployment**. The Free tier is "free to
  use", not "free to modify or redistribute".
- **Pro Tier.** Single developer seat. Licensed for **internal tools
  and production systems** your team operates and your team interacts
  with. Customer-facing, multi-tenant, embedded, white-label, or OEM
  deployments require an Enterprise license.
- **Team Tier.** Up to ten (10) named developer seats under one
  organization, with shared billing. Same SDK feature set and same
  use rights as Pro: licensed for internal tools and production
  systems your team operates. Customer-facing, multi-tenant, embedded,
  white-label, or OEM deployments require an Enterprise license.
  License keys are issued per-organization and are scoped to the seat
  count; installing on machines used by more than the licensed seat
  allowance is a breach of these Terms.
- **Business Tier.** Up to fifty (50) named developer seats under one
  organization, with shared billing. Built for engineering
  organizations standardizing on Wisdom Layer across multiple internal
  teams. Same SDK feature set and same use rights as Pro and Team:
  licensed for internal tools and production systems the licensee
  operates. Customer-facing, multi-tenant, embedded, white-label, or
  OEM deployments require an Enterprise license. License keys are
  issued per-organization and are scoped to the seat count; installing
  on machines used by more than the licensed seat allowance is a
  breach of these Terms.
- **Enterprise Tier.** Required whenever an agent serves an end user
  other than the licensee. Licensed for customer-facing products
  (one agent per end user), multi-tenant deployments, embedded /
  white-label / OEM distribution inside another product, and
  regulated environments that require contractual IP, audit, or SLA
  terms. Includes unlimited developer seats, custom storage backends,
  air-gapped operation, custom dream phases, dedicated support, and
  the contractual IP / audit / SLA terms described in your master
  services agreement. Negotiated per contract.
- **14-Day Pro Trial.** Every new Free signup includes a 14-day full
  Pro trial with all Free capacity caps lifted and Pro-tier features
  unlocked. The trial is bounded by signed JWT claims (`trial_ends_at`
  + `tier_at_expiry`); at expiry, the license downgrades to Free
  automatically. No payment information is required to start a trial,
  and no payment is taken at trial expiry. The trial is non-recurring
  and non-extendable; one trial per email address.
- **Pro / Team / Business / Enterprise Tiers.** Governed by your
  subscription agreement (Pro, Team, and Business are billed monthly
  or annually at your election; Enterprise is billed annually per
  contract). Your license key is revoked on non-payment after the
  grace period in that agreement. On voluntary downgrade or
  cancellation, accumulated memories, facts, and directives are
  preserved on disk; paid-tier features (dream cycles, critic, full
  directive lifecycle, Tier 2/3 memory) stop running and Free caps
  re-engage.

## 5. Data handling

Wisdom Layer is an in-process library. **No memory content, LLM
prompts, LLM responses, agent names, directive text, fact text, user
data, or PII** is transmitted to Rhatigan AGI LLC under any tier. The
SDK transmits two things over the network beyond your own LLM calls:

1. **License validation** to the Wisdom Layer licensing service
   (activate, validate, revoke license keys).
2. **Anonymous usage telemetry** — counts only — under the policy
   below.

### 5.1 Telemetry

By default:

- **Free tier:** anonymous usage telemetry is **enabled** (opt-out).
- **Pro, Team, and Business tiers:** telemetry is **disabled** by
  default (opt-in only).
- **Enterprise tier:** telemetry is **disabled** by default and may
  be disabled contractually for fully air-gapped deployments.

The telemetry payload contains: a randomly generated install identifier
(`install_id`, UUIDv4), SDK version, tier, and counts of agents,
memories, messages (rolling 30-day), facts, dream cycles, and
directives, plus the host operating system family (`linux` /
`darwin` / `win32`) and Python major.minor version. **No content. No
PII. No agent or directive text. No license key. No hostname or IP.**
Full schema is published at
[wisdomlayer.ai/docs/telemetry](https://wisdomlayer.ai/docs/telemetry).

Telemetry can be disabled at any time by setting `WL_TELEMETRY=0` in
the process environment, or by running `wisdom-layer telemetry off`,
which adds your `install_id` to a server-side deny-list and queues
existing rows for deletion within thirty (30) days. Setting
`WL_TELEMETRY=1` opts a Pro, Team, Business, or Enterprise install
into telemetry on a goodwill basis; there is no pricing concession
for opting in.

**Retention.** Raw telemetry events are retained for twelve (12)
months after `received_at`, after which raw rows are deleted and
only aggregated daily rollups (counts by tier, version, OS) are
retained indefinitely. Aggregated rollups contain no install-level
identifiers.

By installing or using the Free tier of the SDK, you acknowledge and
consent to the anonymous usage telemetry described in this section
and in the canonical telemetry policy referenced above. To withhold
that consent, set `WL_TELEMETRY=0` before the first SDK invocation
and the SDK will not transmit telemetry from that install.

See `SECURITY.md` for the full secure-defaults posture.

## 6. Termination

This license terminates automatically if you materially breach it,
if you fall behind on payment beyond the grace period in your
subscription, or if we revoke your license key. On termination you
must stop using the SDK and delete all installed copies.

## 7. Warranty disclaimer and liability cap

The SDK is provided **as-is**, without warranty of any kind. Our
total liability to you is capped at the greater of fees you paid in
the prior 12 months or USD $100 -- whichever is higher. We are not
liable for indirect, incidental, or consequential damages.

## 8. Governing law

Delaware, USA. Disputes resolve in state or federal courts there.

## 9. Questions

- Licensing terms: compliance@wisdomlayer.ai
- Security issues: see `SECURITY.md`
- Product documentation: [wisdomlayer.ai/docs](https://wisdomlayer.ai/docs)

---

The authoritative text is `LICENSE` in the repository root and in
the installed wheel. If this Markdown summary and `LICENSE` conflict,
`LICENSE` controls.
