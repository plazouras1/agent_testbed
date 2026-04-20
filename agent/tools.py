import feedparser
from ddgs import DDGS

DEFAULT_FEED = "http://feeds.bbci.co.uk/news/rss.xml"


def fetch_news(feed_url: str = DEFAULT_FEED) -> str:
    """Fetch and format headlines from an RSS feed."""
    feed = feedparser.parse(feed_url)

    # feedparser sets bozo=True on any XML parse warning, not just fatal errors.
    # Many valid feeds trigger it, so only treat it as an error if entries is also empty.
    if feed.bozo and not feed.entries:
        return f"Error: could not parse feed at {feed_url}"

    lines = [f"Feed: {feed.feed.get('title', feed_url)}\n"]
    for entry in feed.entries[:10]:
        title = entry.get("title", "No title")
        link = entry.get("link", "")
        summary = entry.get("summary", "")[:200]
        lines.append(f"- {title}\n  {link}\n  {summary}\n")

    return "\n".join(lines) if len(lines) > 1 else "No entries found."


def web_search(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and format the results."""
    results = DDGS().text(query, max_results=max_results)

    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for '{query}':\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        href = r.get("href", "")
        body = r.get("body", "")[:300]
        lines.append(f"{i}. {title}\n   {href}\n   {body}\n")

    return "\n".join(lines)


# Dispatch table: maps the schema "name" string to its implementation.
# agent.py looks up tool names here instead of using if/elif chains.
TOOL_REGISTRY = {
    "fetch_news": fetch_news,
    "web_search": web_search,
}
