# Independent Quality Audit

A second-judge audit of the v1.0.1 four-arm benchmark, with criteria
locked before any responses were read. Designed to surface the kind of
fabrication that single-judge specificity-only rubrics can't detect — for
example, a confident invention of a customer's tenure that scores high
on "Groundedness" because it cites a number, even though the cited number
is wrong.

---

## What We're Measuring

Four pre-committed dimensions, each scored 0–10 (integer) by an
independent judge that did not see the primary GEval scores:

1. **Customer-Helpfulness** — does the reply move a real person toward
   resolution? Asking for genuinely-needed info counts as helpful;
   asking for info already in the prompt is unhelpful.
2. **Grounding Honesty** — does the reply use specifics only when
   traceable to retrieved memory? Fabricating plausible-sounding
   specifics scores 0. Acknowledging unknowns scores high.
3. **Production-Realism** — could this reply be sent verbatim? Strategy-doc
   framing or "Key principles:" numbered lists score low. A direct reply
   scores high.
4. **Memory-Use Quality** — when the arm has memory, does the reply
   *visibly* use it (real cases, real numbers, real protocols)? A
   generic answer when memory is rich scores low. The vanilla baseline
   scored N/A on this dimension and is averaged out of its denominator.

**Composite** is the unweighted mean of the per-arm dimension means
(Vanilla averaged across 3 dimensions; the other three arms across 4).

---

## Results: v1.0.1 (April 2026)

| Arm | Customer-Helpfulness | Grounding Honesty | Production-Realism | Memory-Use Quality | **Composite** |
|---|---:|---:|---:|---:|---:|
| Vanilla LLM | 5.00 | 7.67 | 3.83 | — | **5.50** |
| mem0 | 6.83 | 5.50 | 6.50 | 5.17 | **6.00** |
| Basic Memory | 6.83 | 6.83 | 5.33 | 5.67 | **6.17** |
| **Wisdom Layer** | **8.00** | **9.17** | 6.50 | **7.50** | **7.79** |

**Independent ranking: Wisdom Layer > Basic Memory > mem0 > Vanilla.**
The composite ordering inverts versus the primary GEval run, which
ranked mem0 above Wisdom on aggregate Groundedness. Both numbers are
real; they measure different things, and that's the point of running a
second judge.

---

## Why the Two Judges Disagree

- **Grounding Honesty: Wisdom 9.17 vs mem0 5.50.** On the
  loyalty-customer probe, mem0's response asserted the customer
  had been with the company "8 years" — the probe stated five.
  On the wrong-item probe, mem0's response cited billing-issue
  specifics that belong to a different seeded customer. The
  primary GEval judge can't detect this kind of cross-customer
  attribution error; it only verifies that specifics are present
  in the response. A confident response with wrong specifics
  scores high on GEval Groundedness. Locked-criteria human-rubric
  scoring catches the difference.
- **Memory-Use Quality: Wisdom 7.50 (only arm above 5.67).** Wisdom
  is the only arm to cite real seeded order IDs (e.g.
  `ORD-2026-060128`) tied to the correct amounts and dates. The
  primary GEval judge can verify that specifics exist, but not
  whether the ID ↔ amount ↔ date linkage is internally correct.
- **Production-Realism: Wisdom 6.50 — known weakness with a queued
  fix.** Score reflects meta-framing language like "based on the
  pattern from similar situations" leaking into otherwise-correct
  replies. The v1.0.1 customer-voice probe redesign and
  framing-line tightening directly target this.

---

## Audit Methodology

### Pre-Committed Criteria

The four dimensions and their definitions above were written and
committed *before* any responses were read. Same rubric applied
identically to all four arms across all six probes. No per-arm prompts
and no rubric tuning after seeing the data.

### Judge

Claude Opus 4.7. Integer 0–10 scoring. Different judge from the primary
GEval run (which used GPT-4o), so cross-judge agreement is not assumed —
the two judges measure different things by design, and disagreement is
informative rather than disqualifying.

### Probes

The same 24 responses (6 probes × 4 arms) the primary GEval run scored.
No re-generation, no cherry-picking, no probe-set reshuffling between
the two judging passes.

### Tested Configurations

So the "you used the wrong configuration" question is settled up front:

- **Wisdom Layer** — v1.0.1 SDK, default `WisdomAgent` with
  `compose_system_prompt(role=…)` (the public quickstart pattern),
  Haiku 4.5 answer model, `search_insight_ratio=0.30`.
- **Basic Memory** — same Haiku 4.5 answer model, vector retrieval
  over the same seed corpus, no directives, no insight tier — i.e.
  a fair "memory-only" baseline.
- **mem0** — `mem0ai==2.0.1`, default `Memory` class (not graph
  mode, not hierarchical mode), `gpt-4o-mini` as the extractor LLM,
  OpenAI default embeddings, Chroma vector store. Same Haiku 4.5
  answer model used for the reply itself, so the only variable is
  what context the memory layer surfaces. The extractor LLM is
  pinned to `gpt-4o-mini` because mem0's library default has
  drifted to a newer model that requires `max_completion_tokens`
  rather than `max_tokens` and silently 400-errors on every
  extraction; pinning to mem0's documented quickstart model is the
  configuration most developers actually run.
- **Vanilla LLM** — Haiku 4.5, no memory, no retrieval, no
  directives. The pure-base-model floor.

All four arms answered identical prompts. The only across-arm
variable is the memory/retrieval layer.

### Limitations of This Audit

- **Sample size.** n = 24 responses across 6 probes. Large enough to
  see the cross-customer-conflation pattern reliably, small enough
  that broader generalisations require larger probe sets. We do not
  claim "mem0 fabricates 5.50 / 10 of the time in production" —
  we claim "on this probe set, on this run, mem0's responses scored
  5.50 on Grounding Honesty against the locked rubric."
- **Single judge run.** One Opus 4.7 pass. Future audits target
  three-pass majority vote with inter-judge agreement reported.
- **Version-bound.** This audit reflects the v1.0.1 build of
  Wisdom Layer and `mem0ai 2.0.1`. Future versions of either system
  may produce different results.
- **Probe-design caveat.** A subset of v1.0.1 probes used
  agent-voice framing that interacts with the audit's
  Production-Realism dimension. The v1.0.1 customer-voice probe
  redesign is queued for exactly this reason.

### What the Audit Disclosed

- **It's a quality validation, not a replacement for the primary
  GEval result.** Both runs are part of the v1.0.1 record. The
  point of the second judge is to give an honest second opinion when
  the primary table prompts the obvious question.
- **Cross-judge disagreement is the methodology, not a bug.** A single
  judge that ranked the same arms identically across two runs would be
  a weaker signal than two judges that disagree in informative ways.
- **The vanilla arm is averaged across three dimensions** (it has no
  memory to use, so Memory-Use Quality is N/A). All other arms are
  averaged across all four.

---

## Reproducing the Audit

The 24 raw response transcripts, the locked criteria as scored, and
the per-dimension scores will be released in this repository in a
follow-up alongside the v1.0.1 benchmark dataset. The summary
table on [wisdomlayer.ai/benchmarks](https://wisdomlayer.ai/benchmarks)
references the audit composite directly.

For the broader v1.0.1 methodology — the four primary metrics, the
GEval rubrics, mode-aware judging — see
[`fabrication_eval.md`](./fabrication_eval.md) and the public
benchmark page.

Questions about the methodology, configuration, or scoring? Open an
issue on this repository or email `jeff@rhatigan.ai`.

---

## What This Audit Does Not Measure

- **Latency or cost.** Reported separately on the benchmark page; not
  factored into the audit composite.
- **Subjective tone or brand fit.** A reply that's grounded and
  helpful but corporate-sounding still scores well here. Voice is a
  separate concern.
- **Long-horizon behavioural outcomes.** This audit is a single-turn
  response audit. The longitudinal "does the agent get better over
  time" question is the atomic-fact recall + dream-cycle metrics on
  the primary benchmark page.

The audit is one piece of the v1.0.1 record. We publish it because
the second-judge result disagrees with the primary GEval result in a
specific, explainable way — and the disagreement is exactly the kind
of signal a serious buyer should want to see before believing any
single benchmark headline.
