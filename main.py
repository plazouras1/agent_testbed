from dotenv import load_dotenv

# load_dotenv() must run before importing agent, which reads GEMINI_API_KEY
# from the environment when the client is created.
load_dotenv()

from agent.agent import run_agent  # noqa: E402


def main():
    print("Agent Lab — type your question, or 'quit' to exit.")
    print("Model: gemini-2.5-flash  |  Tools: fetch_news, web_search, fetch_url, save_note\n")

    # contents persists across queries so the agent remembers the conversation.
    # Each entry is a types.Content object — the full history is sent to the
    # API on every call because the API itself is stateless.
    contents = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        print("Agent: thinking...", flush=True)
        reply, contents = run_agent(user_input, contents)
        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()
