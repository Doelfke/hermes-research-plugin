"""
Deep Research Plugin — registration.

Registers:
  - deep_research tool       (LLM calls this for research tasks)
  - /research slash command  (user-facing entry point; wraps the tool)
  - Bundled skill deep-research (loadable via skill_view("deep-research:deep-research"))
"""

import json
import re
import logging
from pathlib import Path

from . import schemas
from .tools import make_deep_research_handler

logger = logging.getLogger(__name__)

_SKILLS_DIR = Path(__file__).parent / "skills"


def register(ctx):
    """Wire schemas to handlers and register the slash command and bundled skill."""

    # ── Tool: deep_research ───────────────────────────────────────────────────
    handler = make_deep_research_handler(ctx)
    ctx.register_tool(
        name="deep_research",
        toolset="deep_research",
        schema=schemas.DEEP_RESEARCH,
        handler=handler,
        description=(
            "Multi-step deep web research: plans search queries, searches the web, "
            "extracts content, and synthesizes a comprehensive report. "
            "Use for product comparisons, purchase decisions, topic deep-dives, "
            "and any question benefiting from multiple sources."
        ),
    )

    # ── Slash command: /research ──────────────────────────────────────────────
    # Registered as "research" → invoked as /research <topic>
    # Supports: --depth quick|standard|thorough   --focus <text>
    def _handle_research_command(raw_args: str):
        topic = raw_args.strip()

        if not topic or topic.lower() in ("help", "--help", "-h"):
            return (
                "**Deep Research Plugin**\n\n"
                "**Usage:** `/research <topic> [--depth quick|standard|thorough] [--focus <constraint>]`\n\n"
                "**Examples:**\n"
                "```\n"
                "/research what's the best toaster for home use under $100\n"
                "/research what electric car should I buy for city commuting --depth thorough\n"
                "/research noise-cancelling headphones --focus budget under $200\n"
                "/research latest AI research papers 2025 --depth quick\n"
                "/research should I move to Austin TX --focus family with young kids\n"
                "```\n\n"
                "**Depth levels:**\n"
                "- `thorough` — 6 queries, 7–9 sources (most comprehensive)\n\n"
                "_Requires `web_search` configured. Run `hermes setup` to verify._"
            )

        # Parse --depth flag
        depth = "thorough"
        depth_match = re.search(
            r"--depth\s+(quick|standard|thorough)", topic, re.IGNORECASE
        )
        if depth_match:
            depth = depth_match.group(1).lower()
            topic = (topic[: depth_match.start()] + " " + topic[depth_match.end() :]).strip()

        # Parse --focus flag (captures everything to end-of-string or next --)
        focus = ""
        focus_match = re.search(
            r"--focus\s+(.+?)(?:\s+--|$)", topic, re.IGNORECASE | re.DOTALL
        )
        if focus_match:
            focus = focus_match.group(1).strip()
            topic = (topic[: focus_match.start()] + " " + topic[focus_match.end() :]).strip()

        if not topic:
            return "Please provide a research topic. Usage: `/research <topic>`"

        tool_args = {"topic": topic, "depth": depth}
        if focus:
            tool_args["focus"] = focus

        try:
            result_json = ctx.dispatch_tool("deep_research", tool_args)
            result = json.loads(result_json)

            if result.get("success"):
                report = result.get("report", "*(no report generated)*")
                sources = result.get("sources", [])
                count = result.get("sources_count", len(sources))
                errs = result.get("errors") or []

                sources_block = (
                    "\n".join(f"- {s}" for s in sources[:15])
                    if sources
                    else "None recorded"
                )
                errs_block = (
                    "\n\n⚠️ *Some sources could not be retrieved:*\n"
                    + "\n".join(f"  - {e}" for e in errs)
                    if errs
                    else ""
                )

                return (
                    f"{report}\n\n"
                    f"---\n"
                    f"📚 **Sources ({count}):**\n{sources_block}"
                    f"{errs_block}"
                )
            else:
                err = result.get("error", "Unknown error")
                return f"❌ Research failed: {err}"

        except Exception as e:
            logger.exception("/research command failed")
            return f"❌ Research command error: {e}"

    ctx.register_command(
        "research",
        handler=_handle_research_command,
        description=(
            "Deep web research on any topic — searches, extracts, and synthesizes "
            "a comprehensive report. Use: /research <topic> [--depth quick|standard|thorough]"
        ),
    )

    # ── Bundle skills ─────────────────────────────────────────────────────────
    if _SKILLS_DIR.exists():
        for child in sorted(_SKILLS_DIR.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)
                logger.debug("deep-research plugin: registered skill %r", child.name)

    logger.info(
        "deep-research plugin loaded — tool: deep_research, command: /research"
    )
