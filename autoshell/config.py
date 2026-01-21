import os
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Load environment variables from .env file if it exists
env_loaded = load_dotenv()
console.print(f"[dim][DEBUG] .env file loaded: {env_loaded}[/dim]")

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    @staticmethod
    def validate():
        console.print(f"[dim][DEBUG] Validating configuration...[/dim]")
        console.print(f"[dim][DEBUG] OPENAI_API_KEY exists: {bool(Config.OPENAI_API_KEY)}[/dim]")
        console.print(f"[dim][DEBUG] OPENAI_BASE_URL: {Config.OPENAI_BASE_URL}[/dim]")
        console.print(f"[dim][DEBUG] LLM_MODEL: {Config.LLM_MODEL}[/dim]")
        console.print(f"[dim][DEBUG] MAX_RETRIES: {Config.MAX_RETRIES}[/dim]")
        
        if not Config.OPENAI_API_KEY:
            raise ValueError("Environment variable OPENAI_API_KEY is not set. Please set it in .env file or environment.")
        
        console.print(f"[dim][DEBUG] Configuration validated successfully[/dim]")
