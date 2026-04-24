import re
import textwrap
from pathlib import Path

import feedparser
import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

DEFAULT_FEED = "http://feeds.bbci.co.uk/news/rss.xml"
NOTES_DIR = Path(__file__).parent.parent / "notes"
# Cap fetched page text so it doesn't flood the model's context window.
FETCH_CHAR_LIMIT = 8_000


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


def fetch_url(url: str) -> str:
    """Fetch a webpage and return its cleaned text content."""
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; agent-lab-bot/1.0)"},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} fetching {url}"
    except httpx.RequestError as e:
        return f"Error: could not reach {url}: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove boilerplate tags that add noise without useful content.
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Collapse runs of blank lines down to a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > FETCH_CHAR_LIMIT:
        text = text[:FETCH_CHAR_LIMIT]
        text += f"\n\n[truncated — fetched {FETCH_CHAR_LIMIT} of {len(text)} chars]"

    return f"URL: {url}\n\n{text}"


def save_note(title: str, content: str) -> str:
    """Write a markdown note to the notes/ folder."""
    NOTES_DIR.mkdir(exist_ok=True)

    # Sanitize title to a safe filename: lowercase, spaces to hyphens, strip specials.
    filename = re.sub(r"[^\w\s-]", "", title.lower())
    filename = re.sub(r"[\s_]+", "-", filename).strip("-")
    path = NOTES_DIR / f"{filename}.md"

    path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
    return f"Note saved: {path}"


# Dispatch table: maps the schema "name" string to its implementation.
# agent.py looks up tool names here instead of using if/elif chains.
TOOL_REGISTRY = {
    "fetch_news": fetch_news,
    "web_search": web_search,
    "fetch_url": fetch_url,
    "save_note": save_note,
}
