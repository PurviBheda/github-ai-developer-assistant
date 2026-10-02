from openai import OpenAI
from src.config import LLM_API_KEY

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

response = client.chat.completions.create(
    model="gemini-3.8-flash",
    messages=[
        {
            "role": "user",
            "content": "Explain what MCP is in one sentence."
        }
    ]
)

print(response.choices[0].message.content)