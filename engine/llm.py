from langchain_groq import ChatGroq
import os

# Get a free API key at console.groq.com
# Set it as env var: export GROQ_API_KEY="your_key_here"
# Or create a .env file with: GROQ_API_KEY=your_key_here

llm_chat = ChatGroq(
    model="llama-3.1-8b-instant",  # fastest free model, ~200-400ms
    temperature=0.0,
    api_key=os.environ.get("GROQ_API_KEY")
)

# Wrapper to keep the same llm.invoke(prompt) interface everywhere
class _LLMWrapper:
    def invoke(self, prompt: str) -> str:
        response = llm_chat.invoke(prompt)
        return response.content

llm = _LLMWrapper()
