import subprocess
import shlex
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

class CommandExecutor:
    # 不可变白名单
    WHITELIST = {
        "ls", "dir", "pwd", "echo", "date", "whoami", "hostname", "uname", "cd"
    }

    @classmethod
    def is_safe(cls, command: str) -> bool:
        """
        检查命令是否在白名单中。
        简单策略：解析命令的第一个 token，检查其是否在白名单中。
        """
        try:
            # 简单的 shlex.split 可能无法完美处理复杂的管道/重定向，
            # 但对于提取第一个动作词通常足够。
            # 对于 'ls -la | grep x'，第一个词是 'ls'，属于安全。
            # 风险点：'ls && rm -rf /' -> 这种情况下 shlex 会解析出 'ls'。
            # 因此，对于含有 &&, ||, ; 的复合命令，我们应该更加谨慎。
            # 这里采取严格策略：如果包含复合操作符，直接视为不安全（不在白名单内），转为人工确认。
            
            if any(op in command for op in ["&&", "||", ";", "|"]):
                return False

            tokens = shlex.split(command)
            if not tokens:
                return False
            
            cmd_base = tokens[0].lower()
            return cmd_base in cls.WHITELIST
            
        except Exception:
            # 如果解析出错，默认不安全
            return False

    @classmethod
    def execute(cls, command: str, thought: str = None) -> dict:
        """
        执行命令，包含安全检查和用户确认。
        返回结果字典: {"return_code": int, "stdout": str, "stderr": str, "executed": bool}
        """
        
        is_safe_cmd = cls.is_safe(command)
        
        if not is_safe_cmd:
            console.print(Panel(f"[bold yellow]Reasoning:[/bold yellow] {thought}", title="LLM Thought", expand=False))
            
            syntax = Syntax(command, "bash", theme="monokai", line_numbers=False)
            console.print(Panel(syntax, title="[bold red]Review Command[/bold red]", expand=False, border_style="red"))
            
            if not Confirm.ask("[bold red]Command not in whitelist. Execute?[/bold red]", default=False):
                return {"return_code": -1, "stdout": "", "stderr": "User aborted execution.", "executed": False}

        # 特殊处理 cd 命令
        # 注意：在子进程中执行 cd 对父进程无效。
        # 这里我们只模拟 cd 的效果（如果用户确实只想看能不能 cd），或者提示用户限制。
        # 更好的做法可能是：如果检测到 cd，则尝试在 Python 层面 os.chdir()，
        # 但这改变了 AutoShell 的运行目录，可能引发副作用。
        # 为简单起见，且符合“工具”定位，我们允许 subprocess 执行，但通过 shell=True，
        # 实际上如果是 `cd /tmp && ls` 这种复合命令是有意义的。
        # 只有单独的 `cd` 是无意义的。
        
        try:
            # 使用 shell=True 允许通配符、管道等
            # capture_output=True 捕获输出
            # text=True 将输出解码为字符串
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )
            
            return {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "executed": True
            }
        except Exception as e:
             return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "executed": True
            }
