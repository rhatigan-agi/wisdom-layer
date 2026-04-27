# Confabulation Reduction Evaluation

How we measure whether agents with Wisdom Layer memory produce fewer
fabricated claims than vanilla (memoryless) agents.

---

## What We're Measuring

"Confabulation" (also called "hallucination" or "fabrication") is when
an agent states something as fact that contradicts its own prior knowledge
or the grounded context. A memory-augmented agent should confabulate less
because it can retrieve verified prior interactions instead of generating
from scratch.

We measure **confabulation rate**: the percentage of agent responses
containing at least one verifiably false claim relative to the agent's
own memory corpus.

---

## Results: v1.0.0 (April 2026)

| Agent | Confabulation rate |
|---|---|
| Vanilla (memoryless baseline) | **22%** |
| Wisdom Layer agent | **2%** |

**Setup:**
- n = 45 evaluation pairs
- Single corpus
- Base model: Claude Haiku
- Mode-aware judging (separate judge prompts for vanilla vs. wisdom agent)

**Caveats.** This is a single-corpus, single-base-model result on a sample
size below our target rigor (see [Statistical Rigor](#4-statistical-rigor)).
We're publishing it because the effect size is large and the methodology
is reproducible — not because we consider this a definitive benchmark.
Future evaluations will broaden corpus diversity, base-model coverage, and
sample size.

---

## Methodology

### 1. Corpus Construction

A fixed set of interactions is fed to both a **wisdom agent** (with
Wisdom Layer memory, directives, and dream cycles) and a **vanilla agent**
(same LLM, no memory). The corpus covers:

- Factual recall ("What did the user say about X?")
- Preference recall ("Does the user prefer A or B?")
- Temporal reasoning ("When did the user last mention Y?")
- Contradiction detection ("The user previously said Z -- is this consistent?")
- Multi-hop reasoning ("Given the user's role and preference, what should we recommend?")

### 2. Evaluation Protocol

Each response is evaluated by a **mode-aware judge** -- a separate LLM
call that scores the response against the ground-truth corpus. The judge
operates in two modes:

- **Recall mode** (for the wisdom agent): "Given these memories, is the
  response consistent with what the agent should know?"
- **Baseline mode** (for the vanilla agent): "Without memory, is the
  response reasonable given only the current prompt?"

Mode-aware judging is critical. A single judge that scores both agents
identically will penalize the wisdom agent for attempting (and sometimes
failing) recall, while giving the vanilla agent credit for vague but
non-committal answers.

### 3. Scoring

Each response receives one of three labels:

| Label | Definition |
|---|---|
| **Grounded** | All claims are consistent with the memory corpus or current prompt |
| **Fabricated** | At least one claim contradicts the memory corpus or asserts unverifiable facts |
| **Hedged** | Agent explicitly states uncertainty rather than asserting |

**Confabulation rate** = `fabricated / (grounded + fabricated)`.
Hedged responses are excluded from the denominator because hedging is
a legitimate strategy, not a failure mode.

### 4. Statistical Rigor

The v1.0.0 results above were run on n = 45 evaluation pairs. Future
evaluations target a minimum of 100 pairs per run, plus:

- Three independent judge runs per evaluation pair (majority vote)
- Results reported as mean +/- standard error across runs
- Cohen's kappa for inter-judge agreement
- Diversified corpora across multiple domains
- Multiple base models (Haiku, Sonnet, GPT-4o, open-weight)

---

## Key Design Decisions

### Mode-Aware Judging

Early evaluations used a single judge prompt for both agents. This
produced a systematic bias: the vanilla agent scored better because it
gave vague, non-committal answers that were technically "not wrong,"
while the wisdom agent attempted specific recall and was penalized for
any imprecision.

The fix: separate judge prompts that set different expectations. The
wisdom agent is evaluated on whether it used its memory correctly. The
vanilla agent is evaluated on whether it was appropriately uncertain
without memory.

### What We Don't Measure

- **LLM-inherent hallucination**: if the base model fabricates something
  that has nothing to do with memory (e.g., wrong facts about the real
  world), that's an LLM quality issue, not a Wisdom Layer issue. We filter
  these out by only scoring claims that relate to the agent's own
  interaction history.
- **Subjective quality**: we don't measure whether the response is
  "good" or "helpful." A grounded but unhelpful response counts as
  grounded. Quality evaluation is a separate concern.
- **Latency**: memory recall adds latency. We report it but don't factor
  it into the confabulation score.

### Corpus Refresh

The evaluation corpus is refreshed with each major SDK release to cover
new features (e.g., provenance-backed recall in v0.5, cross-session
context in v0.6). Older corpus versions are archived for longitudinal
comparison.

---

## Running the Evaluation

The corpus and evaluation harness used to produce the single-corpus
results above will be released in this repository in a follow-up.

Beyond this initial fabrication eval, the v1.0 Beta benchmark suite
(four metrics, [DeepEval](https://github.com/confident-ai/deepeval) /
GEval) is published at [wisdomlayer.ai/benchmarks](https://wisdomlayer.ai/benchmarks);
the eval harness for those runs ships alongside.

If you want to run your own evaluation today:

1. Build a corpus of N interactions and feed them to your agent
2. Extract Q questions that require recalling those interactions
3. Run both a wisdom-augmented and vanilla agent against the questions
4. Use a mode-aware judge to score each response
5. Compute confabulation rate for both agents

The key insight is simple: **memory reduces fabrication when the agent
can retrieve instead of generate.** The evaluation framework exists to
quantify that reduction rigorously.
