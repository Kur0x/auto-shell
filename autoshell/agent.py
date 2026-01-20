from rich.console import Console
from rich.panel import Panel
from rich.status import Status

from .config import Config
from .context import ContextManager
from .llm import LLMClient
from .executor import CommandExecutor

console = Console()

class AutoShellAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.max_retries = Config.MAX_RETRIES

    def run(self, user_query: str):
        """
        处理单个用户请求的完整生命周期：
        Context -> LLM -> Execute -> (Retry if fail) -> Output
        """
        error_history = []
        
        # 初始环境感知
        context_str = ContextManager.get_context_string()
        
        for attempt in range(self.max_retries + 1):
            try:
                # 1. Generate Command
                status_msg = "Generating command..." if attempt == 0 else f"Fixing command (Attempt {attempt+1}/{self.max_retries + 1})..."
                
                with console.status(f"[bold green]{status_msg}[/bold green]", spinner="dots"):
                    response = self.llm.generate_command(user_query, context_str, error_history)
                
                command = response.get("command")
                thought = response.get("thought")

                if not command:
                    console.print("[bold red]Error:[/bold red] LLM did not return a command.")
                    return

                # 2. Execute Command
                # Executor 内部已经处理了白名单检查和用户确认
                result = CommandExecutor.execute(command, thought)
                
                if not result["executed"]:
                    # 用户取消执行或发生内部错误
                    if result["stderr"] == "User aborted execution.":
                        console.print("[yellow]Execution aborted by user.[/yellow]")
                        return
                    else:
                        console.print(f"[bold red]Execution Error:[/bold red] {result['stderr']}")
                        return

                # 3. Check Result (Self-Healing)
                if result["return_code"] == 0:
                    console.print(Panel(result["stdout"], title="[bold green]Success[/bold green]", border_style="green"))
                    return # 成功退出
                else:
                    # 失败，记录错误并重试
                    error_msg = result["stderr"] or result["stdout"] # 有些命令错误输出在 stdout
                    console.print(f"[bold red]Command Failed (Code {result['return_code']}):[/bold red] {error_msg}")
                    
                    error_history.append({
                        "command": command,
                        "error": error_msg
                    })
                    
                    if attempt < self.max_retries:
                         console.print(f"[yellow]Attempting to self-heal...[/yellow]")
                         continue # 继续下一次循环，带上 error_history
                    else:
                        console.print(f"[bold red]Max retries reached. Operation failed.[/bold red]")
                        return

            except Exception as e:
                console.print(f"[bold red]System Error:[/bold red] {str(e)}")
                return
