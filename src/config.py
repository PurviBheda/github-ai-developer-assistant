from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LLM_API_KEY = os.getenv("LLM_API_KEY")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is missing")

if not LLM_API_KEY:
    raise ValueError("LLM_API_KEY is missing")