# Tool schemas tell Gemini what tools exist, when to use them, and what arguments to supply.
# Gemini never executes tools itself — it reads these descriptions and decides whether
# to call a tool, then fills in the arguments based on the conversation.
# Vague descriptions cause missed or wrong tool calls. Be specific.

from google.genai import types

TOOLS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="fetch_news",
        description=(
            "Fetches the latest headlines from a public RSS news feed. "
            "Use this when the user asks for current news, recent events, "
            "or headlines on any topic. Returns article titles, links, and summaries."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "feed_url": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "The RSS feed URL to fetch. If the user doesn't specify one, "
                        "omit this argument and the default (BBC News) will be used. "
                        "Example: 'http://feeds.bbci.co.uk/news/rss.xml'"
                    ),
                )
            },
            # feed_url is optional; tools.py supplies a default
        ),
    ),
    types.FunctionDeclaration(
        name="web_search",
        description=(
            "Searches the web using DuckDuckGo and returns relevant results. "
            "Use this to look up facts, people, places, current events, "
            "or anything that benefits from a live web search."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The search query to send to DuckDuckGo.",
                ),
                "max_results": types.Schema(
                    type=types.Type.INTEGER,
                    description="Number of results to return. Defaults to 5 if omitted.",
                ),
            },
            required=["query"],
        ),
    ),
])
