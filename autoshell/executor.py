import subprocess
import shlex
import os
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

class CommandExecutor:
    # 不可变白名单 (扩充)
    WHITELIST = {
        "ls", "dir", "pwd", "echo", "date", "whoami", "hostname", "uname", "cd",
        "mkdir", "touch", "cat", "type", "cp", "mv", "rm", "grep", "find", "head", "tail"
    }

    @classmethod
    def is_safe(cls, command: str) -> bool:
        """
        检查命令是否在白名单中。
        """
        try:
            if any(op in command for op in ["&&", "||", ";", "|"]):
                return False

            tokens = shlex.split(command)
            if not tokens:
                return False
            
            cmd_base = tokens[0].lower()
            return cmd_base in cls.WHITELIST
            
        except Exception:
            return False

    @classmethod
    def execute(cls, command: str, cwd: str = None, description: str = None) -> dict:
        """
        执行命令，包含安全检查和用户确认。
        
        :param command: 要执行的 Shell 命令
        :param cwd: 命令执行的工作目录 (None 表示当前进程目录)
        :param description: 步骤描述，用于 UI 展示
        :return: 结果字典
        """
        
        is_safe_cmd = cls.is_safe(command)
        
        if not is_safe_cmd:
            if description:
                console.print(f"[bold blue]Step:[/bold blue] {description}")
            
            syntax = Syntax(command, "bash", theme="monokai", line_numbers=False)
            console.print(Panel(syntax, title="[bold red]Review Safe-Check[/bold red]", expand=False, border_style="red"))
            
            if not Confirm.ask("[bold red]Command not in whitelist. Execute?[/bold red]", default=False):
                return {"return_code": -1, "stdout": "", "stderr": "User aborted execution.", "executed": False}

        try:
            # 确保 cwd 存在
            if cwd and not os.path.exists(cwd):
                return {
                    "return_code": -1,
                    "stdout": "",
                    "stderr": f"Directory not found: {cwd}",
                    "executed": True
                }

            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd, # 关键变更：支持指定工作目录
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
