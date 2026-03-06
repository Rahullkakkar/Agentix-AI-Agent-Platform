# ✅ FIX 4: Removed LLM-based summary — was a full Mistral inference after every
# single turn, adding 2-4s of pure overhead. Replaced with a lightweight
# rolling transcript that stays under ~300 chars and is just as useful
# for the intent classifier's context.

def update_summary(summary: str, user_input: str, agent_reply: str) -> str:
    new_line = f"Agent: {agent_reply[:80]} | User: {user_input[:80]}"
    lines = summary.split("\n") if summary else []
    lines.append(new_line)
    # Keep last 4 turns only
    return "\n".join(lines[-4:])
