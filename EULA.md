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
  the limits of your active tier (Free / Pro / Enterprise).
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

- **Free Tier.** Runtime limits are documented at
  [wisdomlayer.ai/pricing](https://wisdomlayer.ai/pricing). The free
  tier is "free to use", not "free to modify or redistribute".
- **Pro / Enterprise Tiers.** Governed by your subscription agreement.
  Your license key is revoked on non-payment after the grace period
  in that agreement.

## 5. Data handling

Wisdom Layer is an in-process library. It does not transmit your
application data, your users' data, or the memories and directives
your agents accumulate back to Rhatigan AGI LLC. The SDK talks to
the Wisdom Layer licensing service only to activate, validate, or
revoke license keys. See `SECURITY.md` for the full secure-defaults
posture.

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

- Licensing terms: jeff@rhatigan.ai
- Security issues: see `SECURITY.md`
- Product documentation: [wisdomlayer.ai/docs](https://wisdomlayer.ai/docs)

---

The authoritative text is `LICENSE` in the repository root and in
the installed wheel. If this Markdown summary and `LICENSE` conflict,
`LICENSE` controls.
