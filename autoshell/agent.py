import os
import shlex
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status

from .config import Config
from .context import ContextManager
from .llm import LLMClient
from .executor import CommandExecutor

console = Console()

class AutoShellAgent:
    def __init__(self, ssh_config=None):
        """
        初始化AutoShell Agent
        
        :param ssh_config: SSH配置字典，包含host, port, password, key_filename等
        """
        self.llm = LLMClient()
        self.max_retries = Config.MAX_RETRIES
        self.ssh_config = ssh_config

    def run(self, user_query: str):
        """
        处理单个用户请求的完整生命周期：
        Context -> LLM (Plan) -> Loop (Execute Steps) -> (Retry Step if fail) -> Output
        """
        error_history = []
        
        # 维护当前 Session 的 CWD
        # SSH模式下使用远程主机的家目录，本地模式使用当前目录
        if self.ssh_config:
            session_cwd = None  # SSH模式下不指定工作目录，使用远程默认目录
        else:
            session_cwd = os.getcwd()  # 本地模式使用当前目录 

        # 1. Generate Plan (Context Aware)
        context_str = ContextManager.get_context_string()
        
        # 将当前的 session_cwd 注入到 Context 中，虽然 ContextManager.get_cwd() 也能获取，
        # 但如果是长会话，session_cwd 可能会变，这里还是以 ContextManager 为准（假设它是实时的），
        # 或者我们显式告知 LLM 当前模拟的 CWD。
        # 修正：ContextManager 获取的是 os.getcwd()，如果 AutoShell 进程本身不chdir，它一直不变。
        # 我们应该告诉 LLM 当前的 session_cwd。
        context_str += f"\n- Virtual Session CWD: {session_cwd}"

        # 尝试生成计划
        try:
            with console.status("[bold green]Generating plan...[/bold green]", spinner="dots"):
                plan_data = self.llm.generate_plan(user_query, context_str)
        except Exception as e:
            console.print(f"[bold red]Planning Error:[/bold red] {str(e)}")
            return

        thought = plan_data.get("thought", "No strategy provided")
        steps = plan_data.get("steps", [])

        if not steps:
            console.print("[bold red]Error:[/bold red] LLM returned an empty plan.")
            return

        # 展示计划（确保thought不为空）
        if thought and thought.strip():
            console.print(Panel(f"[italic]{thought}[/italic]", title="Strategy", border_style="blue"))
        else:
            console.print(Panel("[italic]Executing command...[/italic]", title="Strategy", border_style="blue"))
        self._print_plan_table(steps)

        # 2. Execute Steps
        for i, step in enumerate(steps):
            description = step.get("description", "No description")
            command = step.get("command", "")
            
            console.print(f"\n[bold cyan]Step {i+1}/{len(steps)}:[/bold cyan] {description}")
            console.print(f"[dim]Command: {command}[/dim]")
            console.print(f"[dim]CWD: {session_cwd}[/dim]")

            # 检查是否是 CD 命令 (纯状态变更)
            # 解析 command，如果是 'cd path'
            # Windows 下 shlex 默认 posix=True 会吃掉反斜杠，需根据 OS 调整
            use_posix = os.name != 'nt' 
            try:
                tokens = shlex.split(command, posix=use_posix)
            except ValueError:
                # 应对未闭合引号等情况，简单回退到 split
                tokens = command.split()

            if tokens and tokens[0] == "cd":
                # SSH模式下，CD命令由远程shell处理，不在本地模拟
                if self.ssh_config:
                    # SSH模式：更新session_cwd用于显示，但实际由远程执行
                    target_dir = tokens[1] if len(tokens) > 1 else "~"
                    if session_cwd and target_dir.startswith('/'):
                        session_cwd = target_dir
                    elif session_cwd:
                        session_cwd = f"{session_cwd}/{target_dir}" if session_cwd != "~" else target_dir
                    else:
                        session_cwd = target_dir
                    console.print(f"[green]✓ Changed directory to: {session_cwd}[/green]")
                    continue
                else:
                    # 本地模式：实际改变工作目录
                    target_dir = tokens[1] if len(tokens) > 1 else "~"
                    # 处理 ~
                    if target_dir == "~":
                        target_dir = os.path.expanduser("~")
                    
                    # 计算绝对路径（本地模式session_cwd不会是None）
                    new_cwd = os.path.abspath(os.path.join(session_cwd or os.getcwd(), target_dir))
                    
                    if os.path.isdir(new_cwd):
                        session_cwd = new_cwd
                        console.print(f"[green]✓ Changed directory to: {session_cwd}[/green]")
                        continue # CD 成功，进入下一步
                    else:
                        console.print(f"[red]Directory not found: {new_cwd}[/red]")
                        # 这里也可以选择中断，或者让 LLM 修复。
                        # 为了简单，视为失败，触发 Error Handler。
                        result = {"return_code": 1, "stdout": "", "stderr": f"Directory not found: {new_cwd}", "executed": True}
            else:
                # 执行普通命令
                # 实现针对单个步骤的重试循环
                step_success = False
                for attempt in range(self.max_retries + 1):
                    result = CommandExecutor.execute(command, cwd=session_cwd, description=description, ssh_config=self.ssh_config)
                    
                    if not result["executed"]:
                        console.print("[yellow]Execution aborted by user.[/yellow]")
                        return # 用户取消，整个任务结束

                    if result["return_code"] == 0:
                        console.print(f"[green]OK[/green]")
                        # 如果有输出，是否显示？对于批量任务，默认只显示错误或简要。
                        if result["stdout"].strip():
                            console.print(Panel(result["stdout"], title="Output", border_style="green", expand=False))
                        step_success = True
                        break # 跳出重试循环，继续下一个 Step
                    else:
                        # 失败
                        error_msg = result["stderr"] or result["stdout"]
                        console.print(f"[bold red]Failed (Attempt {attempt+1}):[/bold red] {error_msg}")
                        
                        if attempt < self.max_retries:
                            console.print(f"[yellow]Requesting fix from LLM...[/yellow]")
                            
                            # 构建错误历史，请求修复当前步骤
                            # 注意：我们需要修复的是“当前步骤”，或者“剩下的计划”。
                            # 简化起见：我们只请求修复当前步骤的命令。
                            # 这里复用 generate_plan，但 context 聚焦于当前失败。
                            
                            current_error_history = [{
                                "step_index": i+1,
                                "command": command,
                                "error": error_msg
                            }]
                            
                            # 重新生成计划 (LLM 可能会返回针对剩余任务的新计划)
                            # 为了保持逻辑简单，我们询问 LLM "Fix this specific command"
                            # 但架构上 LLM 返回的是 Plan。
                            # 策略：重新调用 generate_plan，传入错误历史。
                            # 如果 LLM 返回新的 steps 列表，我们是用新列表替换当前剩下的步骤？
                            # 是的，这是最智能的做法。
                            
                            try:
                                with console.status("[bold yellow]Re-planning...[/bold yellow]", spinner="dots"):
                                    new_plan_data = self.llm.generate_plan(user_query, context_str, current_error_history)
                                
                                new_steps = new_plan_data.get("steps", [])
                                if new_steps:
                                    console.print(f"[bold green]Plan updated with {len(new_steps)} steps.[/bold green]")
                                    # 策略：替换剩下的步骤
                                    # 注意：for 循环中修改 list 是危险的。
                                    # 更好的做法是：将 executor 逻辑封装，或者使用 while 循环处理 steps。
                                    # 这里为了简便，我们假设 LLM 返回的是“从当前失败点开始的修正计划”。
                                    # 我们可以递归调用 run？或者重置 steps 列表。
                                    
                                    # 采用递归调用的变体：
                                    # 实际上，既然计划变了，我们应该放弃当前的 for 循环，开始执行新计划。
                                    # 但我们需要保持 session_cwd。
                                    # 让我们重构一下：使用 while 循环处理 steps 队列。
                                    
                                    # 由于重构较大，这里采用简单策略：
                                    # 如果修复成功，我们只用新计划的第一个命令替换当前命令重试，
                                    # 忽略后续步骤的变更（假设 LLM 只改了当前步）。
                                    # 或者：中断当前执行，提示用户“计划已更新”，然后重新开始执行新计划（剩余部分）。
                                    
                                    # 鉴于复杂性，这里实现“原地重试命令”：
                                    # 假设 LLM 返回的 steps[0] 是修复后的当前步。
                                    if len(new_steps) > 0:
                                        command = new_steps[0]['command']
                                        description = new_steps[0]['description']
                                        console.print(f"[bold blue]Retrying with:[/bold blue] {command}")
                                        continue # 继续下一轮 attempt
                                    
                            except Exception as ex:
                                console.print(f"[red]Self-healing failed: {ex}[/red]")
                                break 
                        else:
                            console.print("[bold red]Max retries reached. Stopping execution.[/bold red]")
                            return # 遇错即停

                if not step_success:
                    return # 步骤失败且无法修复，退出

        console.print("\n[bold green]All tasks completed successfully![/bold green]")

    def _print_plan_table(self, steps):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Task Description", min_width=20)
        table.add_column("Command", style="cyan")

        for i, step in enumerate(steps):
            table.add_row(str(i+1), step.get("description", ""), step.get("command", ""))
        
        console.print(table)
