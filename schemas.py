"""Tool schemas for the deep-research plugin — what the LLM sees."""

DEEP_RESEARCH = {
    "name": "deep_research",
    "description": (
        "Conduct multi-step deep research on any topic using web search and content extraction. "
        "Plans targeted search queries, gathers information from multiple sources, and synthesizes "
        "a comprehensive, structured report. Use for questions like 'what is the best toaster', "
        "'what car should I buy based on my needs', 'compare noise-cancelling headphones under $300', "
        "or any topic requiring thorough, multi-source research. "
        "Returns a detailed report with findings, recommendations, and sources."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": (
                    "The research topic, question, or query. Be specific and include any "
                    "relevant constraints from the user. "
                    "Examples: 'best toaster for home use under $100', "
                    "'electric car for city commuting with budget under $40000', "
                    "'recent advances in quantum computing 2025', "
                    "'compare MacBook Air vs Dell XPS 13 for software development'"
                ),
            },
            "depth": {
                "type": "string",
                "enum": ["thorough"],
                "description": (
                    "Research depth — always 'thorough': 6 queries / 7-9 sources."
                ),
            },

        },
        "required": ["topic"],
    },
}
