# The Critic

The Critic is the agent's internal values-alignment engine. Before a
response reaches a user, the Critic can evaluate it against the agent's
learned behavioral directives and flag anything that violates them.

Think of it as a cheap, fast values check you run on every LLM output —
not a replacement for output filtering, but a guard that gets smarter
over time because it draws on the agent's own experience.

---

## Basic Usage

```python
review = await agent.critic.evaluate(
    "Here is our return policy. Ship the item back within 14 days.",
    context={"situation": "customer is upset about a broken product"},
)

review["pass_through"]   # True → safe to send; False → flagged
review["risk_level"]     # "low" | "medium" | "high"
review["reasoning"]      # why it was flagged (or why it passed)
review["violations"]     # list of directive IDs that were violated
```

Pass the `context` dict to describe the situation — the Critic uses it
to retrieve only the directives relevant to this specific interaction, so
the evaluation stays focused.

---

## How It Works

1. The Critic retrieves active directives relevant to the context
2. It passes the candidate response and the relevant directives to the LLM
3. The LLM evaluates the response against each directive
4. A risk level and pass/fail decision is returned

Because it uses semantic search to select directives, evaluations are
proportional to the situation — a `risk_level="high"` on a customer
support response means a directive about tone or escalation was violated,
not a generic concern.

---

## When to Use It

**After every AI response before serving it to users** — especially in
customer-facing agents where tone, policy compliance, or escalation
matters.

**Not for:** filtering toxic or harmful content in the general sense.
The Critic evaluates against *your agent's directives* — it's only as
good as the rules the agent has learned. Use a dedicated content filter
for safety-critical moderation.

---

## Risk Levels

| Level | Meaning | Typical action |
|-------|---------|---------------|
| `low` | No directive violations | Serve the response |
| `medium` | Minor violation or soft concern | Log and serve, or revise |
| `high` | Clear directive violation | Revise or escalate |
| `critical` | Severe violation or safety concern | Block and escalate |

`pass_through` is `True` when `risk_level` is `"low"`. Your application
decides what to do with `"medium"` — some use cases serve medium-risk
responses with a log; others treat them as high. `"critical"` should
always be blocked.

---

## The Feedback Loop

The Critic's evaluations feed back into the directive system over time.
When a response is flagged during a dream cycle's failure analysis phase,
the agent can propose a new directive to prevent the same pattern from
recurring. This is how the agent improves its own judgment without you
having to manually author rules.

---

## Grounding Verifier (Beta, opt-in)

When the agent has `enable_fact_extraction=True` and
`critic_verifies_grounding=True` set on `AdminDefaults`, every
`evaluate()` call also extracts atomic claims from the draft response,
looks each one up against the agent's stored facts, and merges a
`grounding` block into the result. A direct contradiction promotes
`risk_level` to `"high"` and forces `pass_through=False`; unknown
claims surface as a soft signal in the audit trail without escalating
risk. Both toggles default off — see
[`agent.critic.verify_grounding`](../api-reference.md#agentcriticverify_groundingoutput--pro-beta-opt-in)
and [`agent.facts`](../api-reference.md#facts--pro-beta-opt-in)
for the call shape.

Each verification runs a two-pass lookup: an exact-attribute scan
followed by a semantic fallback through the embedded facts table when
the exact path misses. The fallback bridges attribute-name drift —
the fact extractor and the claim extractor are independent LLM calls
and routinely invent different attribute names for the same fact. The
per-claim entry in the report carries a `match_source` field
(`"exact"` or `"semantic"`) so the audit trail records which path
confirmed the claim.

---

## Further Reading

- [Directives](directives.md) — the rules the Critic evaluates against
- [Dream Cycles](dream-cycles.md) — how the Critic's judgments feed back
- [API Reference](../api-reference.md) — `agent.critic`
