# Fabrication & Grounding Evaluation

How we measure whether agents with Wisdom Layer memory produce fewer
fabricated claims than vanilla (memoryless) agents and competing memory
layers.

This is the methodology document for the **Hallucinations / ungrounded
outputs** row published on
[wisdomlayer.ai/benchmarks](https://wisdomlayer.ai/benchmarks). The
companion document [`independent_audit.md`](./independent_audit.md)
covers the second-judge quality audit run on the same probe set.

---

## What We're Measuring

A fabrication (also "hallucination" or "confabulation") is a response
that asserts a specific claim — an order ID, a dollar amount, a date,
a customer attribute — that contradicts the agent's memory or has no
backing in retrieved context.

A memory-augmented agent should fabricate less, because it can retrieve
verified prior interactions instead of generating from scratch. That's
the testable hypothesis.

We measure **Groundedness** (also called "Faithfulness" in DeepEval's
GEval framework): a 0.0–1.0 score for whether each claim in the
response is supported by retrieved memory. The pass threshold is 0.7.

---

## Results: v1.0.1 (April 2026)

### Headline — 2-arm Faithfulness, vanilla baseline

Same 5 probes, same Haiku 4.5 answer-LLM, identical conditions except
presence of memory.

| Arm | Mean Groundedness | Pass rate (≥ 0.7) |
|---|---:|---:|
| Vanilla LLM | 0.346 | 0 / 5 |
| **Wisdom Layer** | **0.916** | **5 / 5** |

**Headline: 2.65× lift over vanilla.**

What Vanilla does: refuses ("I don't have access to specific records")
or invents plausible-sounding details with no backing.
What Wisdom Layer does: cites real order numbers, dollar amounts, dates,
and reference codes pulled from memory — each verifiable against the
seeded conversation corpus.

### 4-arm Groundedness — contested, published anyway

The same 6 probes scored across four arms. Wisdom Layer wins per-probe
on the three probes where the customer is identifiable, loses on three
meta-voice probes where it correctly refuses to invent a customer.

| Arm | Mean Groundedness (4-arm, n=6) |
|---|---:|
| Vanilla LLM | 0.41 |
| mem0 | 0.71 |
| Basic Memory | 0.80 |
| Wisdom Layer | 0.62 |

This is a real number and we publish it. The interpretation isn't
"Wisdom Layer is less grounded than Basic Memory in production" — it's
"on three of the six probes, the prompt was a generic agent-voice
question with no customer identity, and Wisdom Layer's
`compose_system_prompt()` correctly told the agent to ask for specifics
rather than invent them. The judge counted the refusal as ungrounded.
The independent audit (different judge, locked rubric) catches the
distinction — see [`independent_audit.md`](./independent_audit.md)."

We won't patch the SDK to lift the chart. Fabrication-resistance is an
architectural commitment, not a tunable knob.

---

## Methodology

### Setup

| | Value |
|---|---|
| Run date | 2026-04-26 |
| Run label | v1.0.1 |
| Model under test | `claude-haiku-4-5-20251001` (held constant across all arms) |
| GEval judge model | `gpt-4o`, `temperature=0.0` |
| Embedding | `bge-base-en-v1.5` (local, 768-dim) |
| Seed corpus | 20 customer-support conversations + 1 dream cycle, identical across all four arms |
| Eval framework | [DeepEval](https://github.com/confident-ai/deepeval) (GEval) |

### 1. Corpus Construction

A fixed corpus of 20 customer-support conversations is fed to all four
arms. The corpus covers:

- Factual recall ("What did the user say about X?")
- Preference recall ("Does the user prefer A or B?")
- Temporal reasoning ("When did the user last mention Y?")
- Contradiction detection ("The user previously said Z — is this consistent?")
- Multi-hop reasoning ("Given the user's role and preference, what should we recommend?")

Probes are sampled from this corpus. Each arm answers the same probe
with the same answer-LLM; the only across-arm variable is the memory /
retrieval layer.

### 2. The Four Arms

So the "you used the wrong configuration" question is settled up front:

- **Wisdom Layer** — v1.0.1 SDK, default `WisdomAgent` with
  `compose_system_prompt(role=…)` (the public quickstart pattern),
  Haiku 4.5 answer model, `search_insight_ratio=0.30`.
- **Basic Memory** — same Haiku 4.5 answer model, vector retrieval
  over the same seed corpus, no directives, no insight tier — i.e.
  a fair "memory-only" baseline.
- **mem0** — `mem0ai==2.0.1`, default `Memory` class (not graph mode,
  not hierarchical mode), `gpt-4o-mini` as the extractor LLM, OpenAI
  default embeddings, Chroma vector store. Same Haiku 4.5 answer model
  used for the reply itself, so the only variable is what context the
  memory layer surfaces. The extractor LLM is pinned to `gpt-4o-mini`
  because mem0's library default has drifted to a newer model that
  silently 400-errors on every extraction.
- **Vanilla LLM** — Haiku 4.5, no memory, no retrieval, no directives.
  The pure-base-model floor.

### 3. Scoring (GEval Faithfulness)

Each response is scored on a 0.0–1.0 Faithfulness scale by the GEval
judge. The criterion (paraphrased): "for each specific claim in the
response, is the claim verifiable against the retrieved evidence
provided to the agent?"

Pass threshold: 0.7. A response that hedges or asks for clarification
when no customer is identifiable scores well; a response that invents
specifics scores poorly.

### 4. The Format-Neutrality Clause

GEval's default Groundedness criterion penalised dialogue-format
retrieval ~0.4 vs the same content as bullet-style summaries — a
purely cosmetic difference the judge couldn't see past. We added an
explicit format-neutrality clause to the criterion: "past Agent turns
asserting facts, policies, or actions count as valid grounding equal
to declarative summaries."

After the fix, Basic Memory's Groundedness lifted from 0.08 → 0.59 on
this corpus and the cross-arm ranking became coherent. Every published
v1.0.1 number uses the format-neutral criterion.

### 5. Statistical Rigor

The v1.0.1 results above are run on n = 5 probes (2-arm headline) /
n = 6 probes (4-arm extended). This is a deliberately small,
high-quality probe set; we report what's reproducible from it and don't
extrapolate.

The roadmap to broader rigor:

- Three independent judge runs per probe (majority vote)
- Inter-judge agreement reported (Cohen's kappa)
- Diversified corpora across multiple domains (security, medical, legal)
- Multiple base models (Haiku, Sonnet, GPT-4o, open-weight)

We do not claim "Wisdom Layer reduces fabrication 2.65× in production."
We claim "on this probe set, on this run, with this answer-LLM, the
Faithfulness score lifted from 0.346 to 0.916." Generalisation is the
buyer's call — we publish the methodology and the dataset so that call
is informed.

---

## Key Design Decisions

### Format Neutrality

Past Agent turns and dialogue-format retrieval count as grounding equal
to bullet summaries. Without this clause, judge bias against
conversational memory format silently invalidates cross-arm comparisons
where one arm stores summaries and another stores transcripts.

### Integer 0–10 Criterion Phrasing

Earlier internal runs phrased GEval criteria in fractional 0.0–1.0
language. This collided with the judge's tokenizer logprob path and
silently deflated scores by ~10×. Rewriting to integer 0–10 lifted
absolute scores ~21pp on Groundedness across the board without
changing relative rankings. Every v1.0.1 number above uses the
integer-phrased criteria.

### What We Don't Measure Here

- **LLM-inherent hallucination.** If the base model fabricates a fact
  about the real world that has nothing to do with memory, that's an
  LLM quality issue. We score only claims that relate to the agent's
  own retrieved context.
- **Subjective answer quality.** A grounded but unhelpful response
  counts as grounded. The independent audit
  ([`independent_audit.md`](./independent_audit.md)) covers helpfulness,
  production-realism, and memory-use quality on a separate locked
  rubric.
- **Latency or cost.** Reported separately; not factored into the
  Groundedness score.

---

## Reproducing the Evaluation

The probe set, the GEval criteria as scored, raw transcripts, and the
per-arm scores will be released alongside the v1.0.1 benchmark
dataset in a follow-up. The summary numbers above and on
[wisdomlayer.ai/benchmarks](https://wisdomlayer.ai/benchmarks)
reference this same run.

To run your own version of this evaluation today:

1. Build a corpus of N customer-support interactions and seed it
   identically to all arms under test
2. Define probes that require recalling specific seeded facts
3. Run each arm with the *same* answer-LLM — only the retrieval layer
   should vary
4. Score with GEval Faithfulness, integer 0–10 phrasing, with a format-
   neutrality clause in the criterion
5. Publish the losing probes alongside the winning ones; if the system
   only "wins" because the probe set was selected for it, the result
   isn't informative

The full v1.0.1 benchmark suite (four primary metrics — fabrication,
longitudinal recall, self-correction, drift) is published on the
benchmark page above; this document covers fabrication / grounding
specifically.

Questions about the methodology, configuration, or scoring? Open an
issue on this repository or email `jeff@rhatigan.ai`.
