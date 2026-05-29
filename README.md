# hermes-research-plugin

Deep research assistant plugin for [Hermes](https://hermes-agent.nousresearch.com).
Works like Claude's extended research mode — plans targeted queries, searches the web,
extracts content from sources, and synthesizes a comprehensive report on any topic.

---

## What it does

- Accepts any research question: _"what's the best toaster"_, _"what car should I buy"_, _"compare X vs Y"_
- Generates targeted, multi-angle search queries automatically
- Uses `web_search` + `web_extract` to gather content from multiple sources
- Synthesizes findings into a structured report with recommendations and sources
- **Optimized for single-GPU setups** — all LLM and web calls are strictly sequential, at most 2 model calls per research session

---

## Requirements

- Hermes with `web_search` and `web_extract` tools configured
- Run `hermes setup` if you haven't configured web search yet

---

## Installation

### One-liner (recommended)

```bash
hermes plugins install Doelfke/hermes-research-plugin --enable
```

### With the convenience script

```bash
curl -fsSL https://raw.githubusercontent.com/Doelfke/hermes-research-plugin/main/install.sh | bash
```

### Manual

```bash
git clone https://github.com/Doelfke/hermes-research-plugin \
    ~/.hermes/plugins/deep-research
hermes plugins enable deep-research
```

---

## What gets installed

| What | How to use |
|------|-----------|
| `/research` slash command | Primary entry point — type `/research <topic>` |
| `deep_research` tool | The LLM calls this automatically for research tasks |
| Bundled `deep-research` skill | Load with `skill_view("deep-research:deep-research")` |

---

## Usage

### Slash command

```
/research what's the best toaster for home use under $100
/research what electric car should I buy for city commuting --depth thorough
/research noise-cancelling headphones --focus budget under $200 --depth thorough
/research should I move to Austin TX --focus family with young kids
/research latest advances in battery technology 2025 --depth quick
/research React vs Vue for a medium SaaS app
```

**Flags:**

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--depth` | `thorough`  Controls number of sources gathered |
| `--focus` | any text | *(none)* | Specific angle or constraint to emphasize |

**Depth levels:**

| Level | Queries | Sources | Best for |
| `thorough` | 6 | 7–9 | Complex purchase decisions, nuanced topics |

### Via the skill

```
/skills load deep-research:deep-research
```

Once loaded, the agent follows the skill's research protocol automatically —
including asking clarifying questions before major purchases.

### Programmatic (via `deep_research` tool)

The LLM can call `deep_research` directly:

```json
{
  "topic": "best electric car for city commuting family of 4",
  "depth": "thorough",
  "focus": "reliability and total cost of ownership under $45000"
}
```

---

## Single-GPU notes

This plugin is designed for setups running a single model on one GPU:

- **Sequential only** — no parallel web calls or concurrent LLM requests
- **2 model calls max** per research session (query planning + synthesis)
- **Content capping** — each source is limited to ~1800 chars before synthesis, keeping the synthesis prompt under ~14 000 chars total
- If `ctx.llm` is unavailable, the tool falls back to pre-built queries and returns raw findings without synthesis

To tune for your model's context length, set these in `tools.py`:

```python
_MAX_CONTENT_PER_SOURCE = 1800   # chars per source (lower if OOM during synthesis)
_MAX_SYNTHESIS_INPUT    = 14000  # total chars to synthesis prompt (lower for smaller context)
```

---

## Troubleshooting

**`No research findings could be gathered`**
Run `hermes setup` — `web_search` may not be configured.

**Synthesis returns raw findings without formatting**
The plugin could not call `ctx.llm.complete()`. Check that your Hermes version
supports plugin LLM access (v0.8+).

**`/research` command not found after install**
Run `hermes plugins enable deep-research` and restart Hermes.

---

## License

MIT
