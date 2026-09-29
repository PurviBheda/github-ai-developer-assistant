from dotenv import load_dotenv
import os

load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")

if github_token:
    print("GitHub token loaded successfully!")
else:
    print("GitHub token not found!")