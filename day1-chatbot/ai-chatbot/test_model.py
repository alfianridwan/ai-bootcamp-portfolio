from litellm import completion

MODEL = "ollama/gemma4:e2b"

response = completion(
    model=MODEL,
    messages=[{"role": "user", "content": "Say hello in one sentence"}],
    api_base="http://localhost:11434",
)

print(response.choices[0].message.content)
