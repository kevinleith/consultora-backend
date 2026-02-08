from anthropic import Anthropic

import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)


with open("agente.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=300,
    temperature=0.2,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print(response.content[0].text)
