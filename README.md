# Agent Lab 01 — Minimal Tool-Using Agent with Claude

A from-scratch implementation of a tool-using AI agent using only the Anthropic Python SDK. No frameworks, no magic. Every file is small and meant to be read.

---

## Project Structure

```
agent-lab01/
├── agent/
│   ├── __init__.py   empty — makes agent/ a Python package
│   ├── schemas.py    tool definitions Claude reads to decide when/how to call tools
│   ├── tools.py      actual Python implementations of each tool + dispatch table
│   └── agent.py      the agentic loop — the heart of the project
├── main.py           interactive REPL: reads user input, calls agent, prints reply
├── requirements.txt  four dependencies
├── .env              your ANTHROPIC_API_KEY (gitignored)
└── .env.example      safe-to-commit template
```

---

## What Is an Agentic Loop?

A standard LLM call is one-shot: you send a message, get a reply, done.

An **agentic loop** is different. Instead of always generating a final answer, the model can pause mid-response and say "I need to call a tool first." Your code runs the tool, sends the result back, and the model continues. This repeats until the model has everything it needs to answer.

```
┌─────────────────────────────────────────┐
│               your code                  │
│                                          │
│   messages ──► Claude API                │
│                    │                     │
│         stop_reason == "tool_use"?       │
│              yes ──┐   no               │
│                    ▼    ▼               │
│              run tool  return answer     │
│                    │                     │
│         append tool_result to messages  │
│                    │                     │
│         ◄──────────┘  (loop back)       │
└─────────────────────────────────────────┘
```

The loop exits when `stop_reason == "end_turn"` — Claude is done thinking and has a final answer.

---

## How Claude Signals Tool Use (`stop_reason`)

Every API response includes a `stop_reason` field that tells you **why** Claude stopped generating:

| `stop_reason` | Meaning |
|---|---|
| `"end_turn"` | Claude finished its answer. Return the text. |
| `"tool_use"` | Claude wants to call one or more tools. Execute them and loop. |
| `"max_tokens"` | Hit the token limit mid-response. Handle gracefully. |

When `stop_reason == "tool_use"`, the response's `content` list contains one or more `ToolUseBlock` objects. Each has:

```python
block.type     # "tool_use"
block.id       # e.g. "toolu_01XYZ..." — unique ID for this call
block.name     # "web_search" or "fetch_news" — which tool to run
block.input    # {"query": "..."} — the arguments Claude chose
```

The `block.id` is critical — you'll use it to link the result back.

---

## How Tool Results Flow Back

After executing a tool, you must send the result back as a `user` message containing `tool_result` blocks. The API then calls Claude again with the full updated history.

Here's what the `messages` list looks like after a single tool call:

```python
# Turn 1 — user asks a question
messages[0] = {"role": "user", "content": "Who won the last F1 race?"}

# Turn 2 — Claude responds, asks to use web_search
messages[1] = {
    "role": "assistant",
    "content": [
        TextBlock(text="Let me search for that."),
        ToolUseBlock(id="toolu_01XYZ", name="web_search", input={"query": "last F1 race winner 2025"})
    ]
}

# Turn 3 — your code runs the tool and sends the result
messages[2] = {
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_01XYZ",  # must match the ToolUseBlock id above
            "content": "1. Max Verstappen won the Bahrain GP..."
        }
    ]
}

# Turn 4 — Claude reads the result and gives a final answer
messages[3] = {"role": "assistant", "content": [TextBlock(text="Max Verstappen won...")]}
```

Two rules the API enforces:
1. The assistant turn with `tool_use` blocks **must appear in history** before you send back results.
2. `tool_result` blocks must be the **entire content** of the following user message — don't mix in plain text before them.

---

## How Tool Schemas Work (`agent/schemas.py`)

Each tool is defined as a dict with three keys:

```python
{
    "name": "web_search",          # must match the key in TOOL_REGISTRY
    "description": "...",          # Claude reads this to decide WHEN to call it
    "input_schema": { ... }        # Claude reads this to know WHAT arguments to pass
}
```

Claude never executes tools — it only reads `description` to decide whether to call a tool, and `input_schema` to know what arguments to fill in. **Good descriptions produce reliable tool selection. Vague descriptions produce missed or wrong calls.**

---

## The Files

**`agent/schemas.py`** — The tool definitions. This is the "contract" you hand to Claude. It only describes the tools; no Python logic lives here.

**`agent/tools.py`** — The actual implementations. `fetch_news` uses `feedparser` to parse an RSS feed. `web_search` uses `DDGS().text()` from the `ddgs` package. Both return plain strings — `tool_result` content accepts strings, and human-readable text is easier to debug. `TOOL_REGISTRY` is a dict mapping tool name → function, used in `agent.py` to dispatch without if/elif chains.

**`agent/agent.py`** — The agentic loop. `run_agent(user_input, messages)` appends the user message, loops calling the API, dispatches tool calls via `_execute_tool`, and returns when `stop_reason == "end_turn"`. This is the most important file — read it carefully.

**`main.py`** — A minimal REPL. Loads `.env`, maintains the `messages` list across turns, and relays between user and agent. Under 35 lines.

---

## Setup

```bash
# 1. Activate the virtual environment
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Anthropic API key
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux
# then open .env and replace "your-api-key-here" with your real key

# 4. Run the agent
python main.py
```

---

## Example Session

```
Agent Lab — type your question, or 'quit' to exit.
Tools available: fetch_news, web_search

You: What are the top headlines right now?
Agent: thinking...
Agent: Here are the latest headlines from BBC News:

1. **Global climate summit reaches new agreement** — World leaders agreed...
2. **Tech giant announces major layoffs** — The company said...
...

You: Search for the latest news about the Anthropic API
Agent: thinking...
Agent: Here's what I found:

1. Anthropic releases Claude 4 with improved reasoning...
   https://...
```

---

## Key Concepts Glossary

| Term | Meaning |
|---|---|
| **agentic loop** | A `while` loop that calls the API repeatedly until the model signals it's done |
| **`stop_reason`** | Why Claude stopped generating: `"end_turn"` (done) or `"tool_use"` (needs a tool) |
| **`tool_use` block** | An object in `response.content` describing which tool to call and with what arguments |
| **`tool_result` block** | A dict you construct with the tool's output, sent back in the next `user` message |
| **`tool_use_id`** | The unique ID linking a `tool_use` block to its corresponding `tool_result` |
| **tool registry** | A `dict` mapping tool name strings to their Python implementations |
| **message history** | The full list of `{role, content}` dicts sent to the API every call (it's stateless) |
