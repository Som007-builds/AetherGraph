from config import LLM_PROVIDER
from config import GROQ_API_KEY, GROQ_MODEL
from config import GEMINI_API_KEY, GEMINI_MODEL
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def call_llm(prompt: str, max_tokens: int = 1500) -> str:
    """
    Single function all agents use to call the LLM.
    Change LLM_PROVIDER in config.py to switch: 'groq', 'gemini', 'claude'
    """
    if LLM_PROVIDER == "groq":
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    elif LLM_PROVIDER == "gemini":
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text.strip()

    elif LLM_PROVIDER == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")