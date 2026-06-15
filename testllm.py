from dotenv import load_dotenv
load_dotenv(override=True)

from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="claude-opus",
    messages=[{"role": "user", "content": "What is RAG in AI? Answer in 2.5 sentences."}],
    max_tokens=100
)

print(response.choices[0].message.content)
