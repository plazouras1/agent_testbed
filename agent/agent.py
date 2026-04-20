import os
from google import genai
from google.genai import types
from .schemas import TOOLS
from .tools import TOOL_REGISTRY

# gemini-2.5-flash: fast, capable, and available on the free tier.
# Swap to gemini-2.5-pro for more capable reasoning.
MODEL = "gemini-2.5-flash"


def run_agent(user_input: str, contents: list) -> tuple[str, list]:
    """
    Add the user's message to history, run the agentic loop until Gemini
    produces a final answer, and return (reply_text, updated_contents).

    The caller owns the contents list and passes it back each turn so the
    agent maintains conversation history across multiple user inputs.

    Note: Gemini calls its history list "contents" (list of Content objects)
    rather than "messages" (list of dicts) as in the Anthropic SDK.
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Append the new user turn. The full history goes to the API every call
    # because the API is stateless — no session is stored server-side.
    contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

    # ── THE AGENTIC LOOP ──────────────────────────────────────────────────────
    # Same concept as with any tool-using model: call the API, check whether
    # the model wants to use a tool, execute it, feed the result back, repeat.
    # The loop exits when the response contains no function_call parts.
    loop_iteration = 0
    while True:
        loop_iteration += 1
        print(f"\n[loop {loop_iteration}] calling {MODEL}...")

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(tools=[TOOLS]),
        )

        response_content = response.candidates[0].content

        # Gemini signals tool use by including Part objects with a function_call
        # field set. If none are present, the model is done and we return.
        function_call_parts = [p for p in response_content.parts if p.function_call]

        if not function_call_parts:
            # No function calls — model produced a final answer.
            final_text = "".join(
                p.text for p in response_content.parts if hasattr(p, "text") and p.text
            ).strip()
            print(f"[loop {loop_iteration}] stop — model returned final answer")
            contents.append(response_content)
            return final_text, contents

        # ── Tool-use cycle ────────────────────────────────────────────────────
        # Step 1: record the model's response (text + function_call parts).
        #         The API requires the model turn in history before results.
        print(f"[loop {loop_iteration}] stop — model requested {len(function_call_parts)} tool call(s)")
        contents.append(response_content)

        # Step 2: execute every function_call and collect FunctionResponse parts.
        result_parts = []
        for part in function_call_parts:
            fc = part.function_call
            print(f"[tool]  {fc.name}({dict(fc.args)})")
            result = _execute_tool(fc.name, dict(fc.args))
            print(f"[result] {result[:120].strip()}{'...' if len(result) > 120 else ''}")
            # Gemini expects results wrapped in FunctionResponse, keyed by the
            # same tool name. The response dict can hold any string payload.
            result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            )

        # Step 3: send all results back in a single user Content.
        #         Unlike Anthropic, there's no tool_use_id to match — Gemini
        #         matches results to calls by name and position in the parts list.
        contents.append(types.Content(role="user", parts=result_parts))
        print(f"[loop {loop_iteration}] tool results appended to history — looping back")

        # Step 4: loop — call the API again with the updated history.


def _execute_tool(name: str, input_args: dict) -> str:
    """
    Look up the tool by name and call it with the arguments Gemini provided.
    Errors are returned as strings so the model can see them and adapt rather
    than crashing the agent loop.
    """
    tool_fn = TOOL_REGISTRY.get(name)
    if not tool_fn:
        return f"Error: unknown tool '{name}'"
    try:
        return tool_fn(**input_args)
    except Exception as e:
        return f"Error running {name}: {type(e).__name__}: {e}"
