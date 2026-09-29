from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("GITHUB_TOKEN")

assert token is not None, "GITHUB_TOKEN is missing"

print("GitHub authentication configuration found.")