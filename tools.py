"""
Deep research tool handler — multi-step web research orchestration.

Designed for single-GPU / single-model setups:
  - All operations are strictly sequential (no parallel LLM or web calls)
  - At most 2 ctx.llm.complete() calls per research session (plan + synthesize)
  - Content is capped per source to keep synthesis context manageable
  - Graceful fallback at every step so partial results are returned on errors
"""

import json
import re
import sys
import logging

logger = logging.getLogger(__name__)


def _eprint(*args):
    """Always-visible stderr print — appears in server logs regardless of log level."""
    print("[deep-research]", *args, file=sys.stderr, flush=True)

# ── Content limits (tuned for single-GPU / single-model setups) ──────────────
_MAX_CONTENT_PER_SOURCE = 1800   # chars kept from each web_extract result
_MAX_SNIPPET_FALLBACK = 500      # chars from a search snippet when extract fails
_MAX_SYNTHESIS_INPUT = 14000     # total chars fed into the synthesis LLM call

# ── Query counts per depth level ─────────────────────────────────────────────
_QUERY_COUNT = {"quick": 2, "standard": 4, "thorough": 6}
_EXTRACTS_PER_QUERY = {"quick": 1, "standard": 2, "thorough": 3}


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _build_research_script(queries, extracts_per_query, max_content, max_snippet):
    """Build the Python script executed via execute_code for search + extraction.

    Uses ``from hermes_tools import web_search, web_extract`` as documented at
    https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution
    so that intermediate tool results never enter the context window.
    """
    return f"""\
from hermes_tools import web_search, web_extract
import json

queries = {json.dumps(queries)}
extracts_per_query = {extracts_per_query}
max_content = {max_content}
max_snippet = {max_snippet}

findings = []
sources = []
errors = []

for query in queries:
    try:
        search_result = web_search(query, limit=10)
        web_results = search_result.get("data", {{}}).get("web", [])
        if not web_results:
            errors.append(f"No results for: {{query!r}}")
            continue

        extracted_this_query = 0
        for r in web_results:
            if extracted_this_query >= extracts_per_query:
                break

            url = (r.get("url") or "").strip()
            title = (r.get("title") or r.get("name") or url).strip()
            snippet = (r.get("snippet") or r.get("description") or "")[:max_snippet]

            if not url or url in sources:
                continue

            content = None
            try:
                page = web_extract([url])
                for p in page.get("results", []):
                    if p.get("content"):
                        content = p["content"].strip()
                        break
            except Exception:
                pass

            if not content:
                if snippet:
                    content = f"[Search snippet] {{snippet}}"
                else:
                    continue

            findings.append({{
                "query": query,
                "url": url,
                "title": title,
                "content": content[:max_content],
            }})
            sources.append(url)
            extracted_this_query += 1
    except Exception as e:
        errors.append(f"Search failed for {{query!r}}: {{str(e)[:300]}}")

print(json.dumps({{"findings": findings, "sources": sources, "errors": errors}}))
"""


# ── LLM-assisted planning ─────────────────────────────────────────────────────

def _fallback_queries(topic, depth):
    """Generate basic queries without an LLM call (used when ctx.llm is unavailable)."""
    n = _QUERY_COUNT.get(depth, 4)
    candidates = [
        topic,
        f"{topic} best options guide",
        f"{topic} comparison review 2025",
        f"{topic} recommendations expert advice",
        f"{topic} pros cons alternatives",
        f"{topic} user experience real world",
    ]
    return candidates[:n]


def _plan_queries(llm, topic, depth):
    """
    Use the model to generate targeted search queries for the research topic.
    Single LLM call; falls back to _fallback_queries on any failure.
    Designed for single-GPU: keeps the prompt concise.
    """
    n = _QUERY_COUNT.get(depth, 4)

    prompt = (
        f'Generate {n} specific search queries to thoroughly research: "{topic}"\n\n'
        "Rules:\n"
        "- Return ONLY a JSON array of query strings, nothing else\n"
        "- Queries must be specific and targeted, not generic\n"
        "- Cover different angles: overview, comparisons, expert opinions, recent info\n"
        "- Include relevant qualifiers (year, budget, use case) where helpful\n\n"
        'Format: ["query one", "query two", "query three"]'
    )

    try:
        response = llm.complete(prompt)
        match = re.search(r"\[.*?\]", response, re.DOTALL)
        if match:
            queries = json.loads(match.group())
            if isinstance(queries, list) and queries:
                return [str(q).strip() for q in queries[:n] if str(q).strip()]
    except Exception as e:
        logger.debug("Query planning LLM call failed (%s), using fallback queries", e)

    return _fallback_queries(topic, depth)


# ── Synthesis ─────────────────────────────────────────────────────────────────

def _sanitize_text(text):
    """Remove null bytes and non-printable control characters that can corrupt JSON request bodies."""
    # Strip null bytes and ASCII control chars (except tab, newline, carriage return)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def _synthesize_report(llm, topic, findings_text):
    """
    Use the model to synthesize gathered findings into a structured research report.
    Single LLM call; capped input size for single-GPU efficiency.
    """
    findings_text = _sanitize_text(findings_text)
    prompt = (
        f'You are a research assistant. Synthesize the following raw findings into a '
        f'comprehensive, directly useful report on: "{topic}"\n\n'
        "--- RESEARCH FINDINGS ---\n"
        f"{findings_text[:_MAX_SYNTHESIS_INPUT]}\n"
        "-------------------------\n\n"
        "CRITICAL RULES:\n"
        "- NEVER organize output by source or website — organize ONLY by theme/topic\n"
        "- Do NOT list what each individual source says; cross-reference and combine them\n"
        "- Directly answer the user's question; do not just describe what sources exist\n\n"
        "Write a thorough, actionable report using these sections:\n\n"
        "## Summary\n"
        "2–3 sentence direct answer to the core question. Lead with the conclusion.\n\n"
        "## Key Findings\n"
        "Organized by THEME (not by source). Combine and synthesize insights across sources. "
        "Include specific data, names, prices, and facts — citing sources inline as (Source: title).\n\n"
        "## Recommendations\n"
        "Concrete and specific — name actual products/options/actions with reasoning.\n"
        "Do not say 'it depends' without immediately explaining what it depends on.\n\n"
        "## Considerations & Caveats\n"
        "Important trade-offs, limitations, and things the user should watch out for.\n\n"
        "## Sources\n"
        "List each source title and URL used.\n\n"
        "Be direct. Avoid filler and generic advice."
    )

    try:
        return llm.complete(prompt)
    except Exception as e:
        logger.warning("Synthesis LLM call failed: %s", e)
        # Return findings with explicit synthesis instructions for the calling agent
        return (
            f"**NOTE: Automatic synthesis failed ({e}). "
            "YOU MUST synthesize the findings below into a direct answer. "
            "Do NOT present them source-by-source — organize by theme and lead with your conclusion.**\n\n"
            f"---\n\n{findings_text[:4000]}"
        )


# ── Main handler factory ──────────────────────────────────────────────────────

def make_deep_research_handler(ctx):
    """
    Returns the deep_research tool handler with ctx captured in closure.

    The handler uses:
      ctx.llm.complete()     — query planning (1 call) + synthesis (1 call)
      ctx.dispatch_tool()    — execute_code (1 call; runs web_search + web_extract
                               via `from hermes_tools import ...` inside the script)

    All steps are sequential — safe for single-GPU / single-model setups.
    """
    llm = getattr(ctx, "llm", None)

    def handle_deep_research(args, **kwargs):
        topic = (args.get("topic") or "").strip()
        if not topic:
            return json.dumps({"success": False, "error": "topic is required"})

        depth = "thorough"

        extracts_per_query = _EXTRACTS_PER_QUERY.get(depth, 2)

        findings = []   # list of {query, url, title, content}
        sources = []    # deduplicated URLs (insertion order)
        errors = []

        try:
            # ── Step 1: Plan search queries (1 LLM call) ─────────────────────
            if llm:
                queries = _plan_queries(llm, topic, depth)
            else:
                queries = _fallback_queries(topic, depth)

            logger.debug(
                "deep_research: topic=%r depth=%s queries=%s", topic, depth, queries
            )

            # ── Step 2: Search + extract via execute_code (single call) ────
            # web_search and web_extract are called inside the script using
            # `from hermes_tools import ...` so intermediate results never
            # enter the context window.
            script = _build_research_script(
                queries, extracts_per_query,
                _MAX_CONTENT_PER_SOURCE, _MAX_SNIPPET_FALLBACK,
            )
            _eprint(f"Launching execute_code for {len(queries)} queries")
            exec_raw = ctx.dispatch_tool("execute_code", {"code": script})
            if isinstance(exec_raw, str):
                exec_raw = json.loads(exec_raw)

            exec_status = exec_raw.get("status", "error")
            exec_output = (exec_raw.get("output") or "").strip()
            _eprint(f"execute_code status={exec_status!r} output_len={len(exec_output)}")

            if exec_status != "success" or not exec_output:
                return json.dumps({
                    "success": False,
                    "error": (
                        f"Research data collection failed "
                        f"(execute_code status={exec_status!r}): "
                        f"{exec_output[:500] or exec_raw.get('error', 'no output')}"
                    ),
                    "queries_attempted": queries,
                })

            try:
                gathered = json.loads(exec_output)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to parse research script output: {e}",
                    "raw_output": exec_output[:500],
                })

            findings = gathered.get("findings", [])
            sources = gathered.get("sources", [])
            errors = gathered.get("errors", [])
            _eprint(f"execute_code: {len(findings)} findings, {len(errors)} errors")

            # ── Early exit if nothing was gathered ────────────────────────────
            if not findings:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            "No research findings could be gathered. "
                            "Ensure web_search and web_extract are configured "
                            "(run `hermes setup` to verify)."
                        ),
                        "queries_attempted": queries,
                        "errors": errors,
                    }
                )

            # ── Step 3: Synthesize findings (1 LLM call) ──────────────────────
            findings_text = ""
            for i, f in enumerate(findings, 1):
                findings_text += (
                    f"\n### Source {i}: {f['title']}\n"
                    f"URL: {f['url']}\n"
                    f"Query: {f['query']}\n\n"
                    f"{f['content']}\n"
                )

            if llm:
                report = _synthesize_report(llm, topic, findings_text)
            else:
                # No LLM access from plugin context — return findings with
                # explicit instruction for the calling agent to synthesize
                report = (
                    f"# Research Findings: {topic}\n\n"
                    "**IMPORTANT — YOU MUST SYNTHESIZE THIS**: Do NOT present these "
                    "findings source-by-source. Read all findings below, then write a "
                    "coherent answer organized by theme/topic that directly addresses "
                    f'the question: \'{topic}\'. Lead with your conclusion, then support '
                    "it with evidence drawn across multiple sources.\n\n"
                    "---\n\n"
                    + findings_text
                )

            return json.dumps(
                {
                    "success": True,
                    "topic": topic,
                    "depth": depth,
                    "report": report,
                    "sources": sources,
                    "sources_count": len(sources),
                    "queries_used": queries,
                    "errors": errors if errors else None,
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.exception(
                "deep_research handler crashed for topic %r", topic
            )
            return json.dumps(
                {
                    "success": False,
                    "error": f"Research process failed: {e}",
                    "partial_findings": len(findings),
                }
            )

    return handle_deep_research
