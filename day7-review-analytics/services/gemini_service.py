from google import genai
from google.genai import types
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)

SYSTEM_PROMPT = (
    "You are a database-integrated text processing utility. Analyze the user text data. "
    "You MUST output your response in a strict formatted style containing two sections:\n"
    "1. A bulleted summary synthesized from the reviews.\n"
    "2. A standalone single line stating exactly: 'FINAL_RATING: X' (where X is an integer score from 0 to 10).\n\n"
    "Keep your response analytical and professional."
)

def analyze_review_sentiment(review_content):
    response = client.models.generate_content(
        model=config.MODEL_NAME,
        contents=review_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1
        )
    )

    raw_output = response.text

    # PARSING LOGIC: copied verbatim from logic.py — do not paraphrase, an
    # off-by-one here silently produces a wrong-but-plausible-looking rating.
    rating = 5  # Safe default fallback score if parsing fails
    clean_summary = raw_output

    if "FINAL_RATING:" in raw_output:
        parts = raw_output.split("FINAL_RATING:")
        clean_summary = parts[0].strip()
        try:
            rating = int("".join(filter(str.isdigit, parts[1])))
        except ValueError:
            rating = 5

    if 8 <= rating <= 10:
        category = "Good"
    elif 4 <= rating <= 7:
        category = "Average"
    else:
        category = "Bad"

    return clean_summary, rating, category
