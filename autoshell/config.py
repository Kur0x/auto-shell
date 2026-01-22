import os
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Load environment variables from .env file if it exists
env_loaded = load_dotenv()

class Config:
    DEBUG = False  # 默认关闭debug输出，通过命令行参数--debug启用
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-needed")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # 系统信息收集配置
    COLLECT_DETAILED_INFO = os.getenv("COLLECT_DETAILED_INFO", "true").lower() == "true"
    SYSTEM_INFO_CACHE_TTL = int(os.getenv("SYSTEM_INFO_CACHE_TTL", "300"))  # 秒
    SSH_INFO_TIMEOUT = int(os.getenv("SSH_INFO_TIMEOUT", "10"))  # 秒

    @staticmethod
    def is_ollama() -> bool:
        """检测是否使用 Ollama"""
        base_url = Config.OPENAI_BASE_URL.lower()
        return any([
            "localhost" in base_url,
            "127.0.0.1" in base_url,
            ":11434" in base_url
        ])

    @staticmethod
    def validate():
        if Config.DEBUG:
            console.print(f"[dim][DEBUG] Validating configuration...[/dim]")
        
        # 检测提供商类型
        is_ollama = Config.is_ollama()
        provider_name = "Ollama (Local)" if is_ollama else "OpenAI Compatible"
        
        if Config.DEBUG:
            console.print(f"[dim][DEBUG] LLM Provider: {provider_name}[/dim]")
            console.print(f"[dim][DEBUG] OPENAI_API_KEY exists: {bool(Config.OPENAI_API_KEY)}[/dim]")
            console.print(f"[dim][DEBUG] OPENAI_BASE_URL: {Config.OPENAI_BASE_URL}[/dim]")
            console.print(f"[dim][DEBUG] LLM_MODEL: {Config.LLM_MODEL}[/dim]")
            console.print(f"[dim][DEBUG] MAX_RETRIES: {Config.MAX_RETRIES}[/dim]")
        
        # 只对非 Ollama 提供商验证 API Key
        if not is_ollama and not Config.OPENAI_API_KEY:
            raise ValueError(
                "Environment variable OPENAI_API_KEY is not set. "
                "Please set it in .env file or environment.\n"
                "For Ollama, set OPENAI_BASE_URL to http://localhost:11434/v1"
            )
        
        if Config.DEBUG:
            console.print(f"[dim][DEBUG] Configuration validated successfully[/dim]")
