"""Check that the Gemini API key works. Independent of the pipeline."""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()  # reads GEMINI_API_KEY from the .env file

key = os.getenv("GEMINI_API_KEY")
if not key:
    raise SystemExit("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=key)
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Reply with exactly one word: OK",
)
print("Gemini replied:", response.text.strip())
