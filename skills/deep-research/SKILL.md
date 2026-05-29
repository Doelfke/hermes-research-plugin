---
name: deep-research
description: >
  Conduct thorough multi-angle web research on any topic and synthesize a
  comprehensive report. Handles everything from "best toaster" product comparisons
  to complex personal decisions like "what car should I buy based on my needs."
version: 1.0.0
metadata:
  hermes:
    tags: [research, web, analysis, synthesis, shopping, comparison]
    category: research
---

# Deep Research

## When to Use

Load this skill when the user asks you to research something thoroughly — product
comparisons, purchase decisions, topic investigations, "best X" questions, or
any query that benefits from gathering and synthesizing multiple sources.

**Trigger phrases:**
- "Research …", "Look into …", "Find the best …"
- "What should I buy for …", "Compare X vs Y"
- "What are my options for …", "Help me decide …"
- "Investigate …", "Give me a thorough breakdown of …"

**Example topics:**
- "What's the best toaster for home use under $100?"
- "What car should I buy based on my needs?"
- "Compare noise-cancelling headphones under $300"
- "Should I use React or Vue for my next project?"
- "What are the pros and cons of moving to Austin, TX?"
- "Latest advances in battery technology 2025"

## Procedure

### 1. Clarify First (for personal decisions)

For recommendations that depend on the user's situation (cars, major purchases,
life decisions), ask **1–2 targeted clarifying questions** before researching:

- Budget or price range
- Primary use case / who it's for
- Must-have features or hard deal-breakers
- Any preferences already known (brand, size, style)

**Skip clarification** when the question is already specific enough, or when the
user explicitly asks you to "just research" without extra questions.

### 2. Call `deep_research`

Use the `deep_research` tool with:

| Parameter | When to set |
|-----------|-------------|
| `topic`   | Always — include constraints from the clarification step |
| `depth`   | `thorough` for complex decisions |
| `focus`   | When the user has a specific angle to emphasize (budget, use-case, comparison criteria) |

**Examples:**
```
deep_research(topic="best toaster for home use under $100", depth="thorough")
deep_research(topic="electric car for city commuting family of 4", depth="thorough", focus="reliability and total cost of ownership")
deep_research(topic="React vs Vue for a medium-sized SaaS app", depth="thorough", focus="developer experience and ecosystem maturity")
```

### 3. Present the Report

When `deep_research` returns:

- **Lead with the answer** — give the recommendation or conclusion upfront, then
  support it with evidence from the report.
- **Keep specifics intact** — do not paraphrase away prices, model names, or
  data points; present them as found.
- **Offer to drill deeper** — after presenting, invite the user to ask follow-up
  questions or request a deeper look at a specific option.

### 4. Follow-up Research

If the user wants to explore a specific angle after the initial report:

- Run `deep_research` again with a **narrower topic** + `focus` parameter.
- Example flow:
  1. First: `topic="electric cars for city driving", depth="thorough"`
  2. Follow-up: `topic="Tesla Model 3 vs Hyundai Ioniq 6 comparison", focus="charging infrastructure and real-world range"`

## Pitfalls

- **Don't skip clarification for major decisions** — "what car should I buy"
  without knowing budget, family size, or commute type leads to generic advice.
- **Don't strip specifics** — the report contains concrete data; keep it when
  presenting to the user.
- **Don't re-research immediately on failure** — if `deep_research` returns an
  error, report the error message to the user rather than retrying immediately.
- **Don't use `quick` for purchase decisions** — `thorough` is
  appropriate whenever the user is about to spend money or make a significant choice.

## Verification

A successful research session:
- Answers the user's actual question (not a generic overview)
- Cites specific sources with names/URLs
- Gives concrete recommendations with reasoning
- Acknowledges trade-offs or limitations where they exist
