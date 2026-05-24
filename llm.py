import time
from config import LLM_PROVIDER
from config import GROQ_API_KEY, GROQ_MODEL
from config import GEMINI_API_KEY, GEMINI_MODEL
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def call_llm(prompt: str, max_tokens: int = 1500, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
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

        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                wait = 60 * (attempt + 1)
                print(f"  Rate limit hit. Waiting {wait}s before retry {attempt+1}/{retries}...")
                time.sleep(wait)
            else:
                raise e

    raise Exception("Max retries exceeded due to rate limiting.")