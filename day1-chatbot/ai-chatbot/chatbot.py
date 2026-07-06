from litellm import completion
from mem0 import Memory

MODEL = "ollama/gemma4:e2b"
OLLAMA = "http://localhost:11434"
USER_ID = "student1"

config = {
    "vector_store": {"provider": "chroma", "config": {"path": "./chroma_db"}},
    "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text", "ollama_base_url": OLLAMA}},
    "llm": {"provider": "ollama", "config": {"model": "gemma4:e2b", "ollama_base_url": OLLAMA}},
}
memory = Memory.from_config(config)


def chat(user_message):
    # Recall relevant facts from memory
    results = memory.search(user_message, filters={"user_id": USER_ID})
    recalled = "\n".join(r["memory"] for r in results.get("results", []))

    # Build messages, injecting memory as system context
    messages = []
    if recalled:
        messages.append({"role": "system", "content": f"Known facts about the user:\n{recalled}"})
    messages.append({"role": "user", "content": user_message})

    response = completion(model=MODEL, messages=messages, api_base=OLLAMA)
    reply = response.choices[0].message.content

    # Store this turn for future recall
    memory.add(f"User: {user_message}\nAssistant: {reply}", user_id=USER_ID)

    return reply


if __name__ == "__main__":
    print("Chatbot ready. Type 'quit' to exit.")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break
        print(f"Bot: {chat(user_input)}\n")
