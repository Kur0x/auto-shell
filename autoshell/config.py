import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    @staticmethod
    def validate():
        if not Config.OPENAI_API_KEY:
            raise ValueError("Environment variable OPENAI_API_KEY is not set. Please set it in .env file or environment.")
