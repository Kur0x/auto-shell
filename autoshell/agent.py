import os
import shlex
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status

from .config import Config
from .context import ContextManager
from .ssh_context import SSHContextManager
from .llm import LLMClient
from .executor import CommandExecutor
from .interactive import InteractiveHandler, UserInputContext

console = Console()

class AutoShellAgent:
    def __init__(self, ssh_config=None, context_files=None):
        """
        初始化AutoShell Agent
        
        :param ssh_config: SSH配置字典，包含host, port, password, key_filename等
        :param context_files: 用户提供的上下文文件列表
        """
        self.llm = LLMClient()
        self.max_retries = Config.MAX_RETRIES
        self.ssh_config = ssh_config
        self.context_files = context_files or []
        
        # 系统信息缓存
        self._system_info_cache = None
        self._cache_timestamp = None
        self._cache_ttl = Config.SYSTEM_INFO_CACHE_TTL
        
        # 用户输入上下文
        self.user_input_context = UserInputContext()
        
        # 初始化时收集系统信息
        if Config.COLLECT_DETAILED_INFO:
            self._initialize_system_info()
    
    def _initialize_system_info(self):
        """初始化系统信息"""
        try:
            if self.ssh_config:
                # SSH模式：先测试连接
                with console.status("[bold green]Testing SSH connection...[/bold green]", spinner="dots"):
                    success, message = SSHContextManager.test_connection(self.ssh_config)
                
                if not success:
                    # 连接失败，直接抛出异常退出
                    console.print(f"[bold red]SSH Connection Failed:[/bold red] {message}")
                    raise ConnectionError(f"SSH connection failed: {message}")
                
                # 连接成功，显示消息
                console.print(f"[green]✓[/green] {message}")
                
                # 收集远程信息
                with console.status("[bold green]Collecting remote system info...[/bold green]", spinner="dots"):
                    self._system_info_cache = SSHContextManager.get_remote_system_info(self.ssh_config)
            else:
                # 本地模式：收集本地信息
                self._system_info_cache = ContextManager.get_detailed_os_info()
            
            self._cache_timestamp = time.time()
            
            if Config.DEBUG:
                console.print(f"[dim][DEBUG] System info collected: {self._system_info_cache}[/dim]")
        except ConnectionError:
            # SSH连接错误，直接向上抛出
            raise
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to collect system info: {e}[/yellow]")
            self._system_info_cache = None
    
    def _get_system_info(self) -> dict:
        """获取系统信息（带缓存）"""
        now = time.time()
        
        # 检查缓存是否有效
        if self._system_info_cache and self._cache_timestamp:
            if (now - self._cache_timestamp) < self._cache_ttl:
                return self._system_info_cache
        
        # 缓存过期或不存在，重新收集
        self._initialize_system_info()
        return self._system_info_cache or {}

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

        # 1. Generate Plan (Context Aware) - 使用增强的上下文信息
        system_info = self._get_system_info()
        
        if self.ssh_config:
            # SSH模式：使用远程系统信息
            context_str = SSHContextManager.format_remote_context(system_info)
        else:
            # 本地模式：使用本地系统信息
            context_str = ContextManager.get_enhanced_context_string(system_info)
        
        context_str += f"\n- Virtual Session CWD: {session_cwd}"
        
        # 添加用户上下文文件
        user_context = ""
        if self.context_files:
            from .context_file import ContextFileManager
            user_context = ContextFileManager.format_context_string(self.context_files)

        # 尝试生成计划
        try:
            with console.status("[bold green]Generating plan...[/bold green]", spinner="dots"):
                plan_data = self.llm.generate_plan(user_query, context_str, user_context=user_context)
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
            
            # 检查是否为交互式命令
            if InteractiveHandler.is_interactive_command(command):
                # 处理交互式步骤
                user_input = InteractiveHandler.handle_interactive_step(step)
                
                if user_input is None:
                    # 用户取消操作
                    console.print("[yellow]用户取消执行[/yellow]")
                    return
                
                # 存储用户输入
                is_password = command == "__USER_PASSWORD__"
                self.user_input_context.store(i + 1, user_input, is_password=is_password)
                
                # 如果是确认类型且用户拒绝，则停止执行
                if command == "__USER_CONFIRM__" and not user_input:
                    console.print("[yellow]用户拒绝继续，停止执行[/yellow]")
                    return
                
                continue  # 继续下一步
            
            # 替换命令中的用户输入占位符
            command = self.user_input_context.replace_placeholders(command)
            
            console.print(f"[dim]Command: {command}[/dim]")
            console.print(f"[dim]CWD: {session_cwd}[/dim]")

            # 检查是否是纯 CD 命令 (纯状态变更)
            # 只有不包含 &&、||、; 等操作符的纯 cd 命令才进行特殊处理
            # 包含这些操作符的组合命令应该交给 shell 执行
            is_pure_cd = False
            tokens = []
            if not any(op in command for op in ["&&", "||", ";", "|"]):
                # 解析 command，如果是 'cd path'
                # Windows 下 shlex 默认 posix=True 会吃掉反斜杠，需根据 OS 调整
                use_posix = os.name != 'nt'
                try:
                    tokens = shlex.split(command, posix=use_posix)
                except ValueError:
                    # 应对未闭合引号等情况，简单回退到 split
                    tokens = command.split()
                
                if tokens and tokens[0] == "cd":
                    is_pure_cd = True
            
            if is_pure_cd:
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
                max_regenerate_attempts = 5  # 最大重新生成次数
                regenerate_count = 0
                
                for attempt in range(self.max_retries + 1):
                    result = CommandExecutor.execute(command, cwd=session_cwd, description=description, ssh_config=self.ssh_config)
                    
                    # 检查是否需要重新生成命令
                    if result.get("regenerate") and regenerate_count < max_regenerate_attempts:
                        feedback = result.get("feedback", "")
                        console.print(f"[cyan]根据反馈重新生成命令...[/cyan]")
                        console.print(f"[dim]用户反馈: {feedback}[/dim]")
                        
                        try:
                            with console.status("[bold green]重新生成命令...[/bold green]", spinner="dots"):
                                new_step = self.llm.regenerate_command(
                                    original_command=command,
                                    original_description=description,
                                    user_feedback=feedback,
                                    context_str=context_str,
                                    user_goal=user_query,
                                    user_context=user_context
                                )
                            
                            # 更新命令和描述
                            command = new_step.get("command", command)
                            description = new_step.get("description", description)
                            regenerate_count += 1
                            
                            console.print(f"[green]✓ 已重新生成命令:[/green]")
                            console.print(f"[dim]描述: {description}[/dim]")
                            console.print(f"[dim]命令: {command}[/dim]")
                            
                            # 重新尝试执行新命令（不增加attempt计数）
                            continue
                            
                        except Exception as e:
                            console.print(f"[red]重新生成命令失败: {e}[/red]")
                            return
                    
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

    def run_adaptive(self, user_query: str):
        """
        增强的自适应执行模式：
        - 多阶段任务规划
        - 智能错误恢复和重试
        - 结构化的执行上下文管理
        """
        from .adaptive_context import AdaptiveExecutionContext, ExecutionStep, StepStatus
        from .task_planner import TaskPlanner
        from .error_recovery import ErrorRecoveryManager, RecoveryStrategy
        
        console.print(Panel.fit(
            "[bold blue]增强自适应执行模式[/bold blue]\n"
            "✓ 多阶段任务规划\n"
            "✓ 智能错误恢复\n"
            "✓ 动态步骤生成",
            title="Enhanced Adaptive Mode",
            border_style="blue"
        ))
        
        # 获取系统上下文
        system_info = self._get_system_info()
        if self.ssh_config:
            context_str = SSHContextManager.format_remote_context(system_info)
            session_cwd = None
        else:
            context_str = ContextManager.get_enhanced_context_string(system_info)
            session_cwd = os.getcwd()
        context_str += f"\n- Virtual Session CWD: {session_cwd}"
        
        # 用户上下文
        user_context = ""
        if self.context_files:
            from .context_file import ContextFileManager
            user_context = ContextFileManager.format_context_string(self.context_files)
        
        # 初始化组件
        planner = TaskPlanner(self.llm)
        error_manager = ErrorRecoveryManager(max_retries=Config.MAX_RETRIES)
        
        # 生成任务计划
        console.print(f"\n[bold cyan]目标:[/bold cyan] {user_query}\n")
        try:
            exec_context = planner.analyze_and_plan(user_query, context_str, user_context)
        except Exception as e:
            console.print(f"[red]任务规划失败: {e}[/red]")
            return
        
        # 执行循环
        max_iterations = 50
        iteration = 0
        
        while not planner.is_plan_complete() and iteration < max_iterations:
            iteration += 1
            
            # 获取下一个可执行的阶段
            current_phase = planner.get_next_executable_phase()
            if not current_phase:
                console.print("[yellow]没有可执行的阶段[/yellow]")
                break
            
            console.print(f"\n[bold magenta]═══ 阶段 {current_phase.phase_id}: {current_phase.name} ═══[/bold magenta]")
            console.print(f"[dim]目标: {current_phase.goal}[/dim]\n")
            
            # 设置当前阶段
            exec_context.set_current_phase(current_phase)
            
            # 生成阶段的步骤
            try:
                with console.status("[bold green]生成执行步骤...[/bold green]", spinner="dots"):
                    next_plan = self.llm.generate_next_steps(
                        user_goal=current_phase.goal,
                        context_str=context_str + "\n\n" + exec_context.get_context_summary(max_steps=5),
                        execution_history=[],  # 使用新的上下文管理
                        max_steps=3,
                        user_context=user_context
                    )
            except Exception as e:
                console.print(f"[red]生成步骤失败: {e}[/red]")
                exec_context.complete_current_phase(success=False)
                continue
            
            thought = next_plan.get("thought", "")
            steps = next_plan.get("steps", [])
            
            if not steps:
                console.print("[yellow]没有生成步骤[/yellow]")
                exec_context.complete_current_phase(success=False)
                continue
            
            # 显示思考和计划
            if thought:
                console.print(Panel(f"[italic]{thought}[/italic]", title="AI 分析", border_style="blue"))
            self._print_plan_table(steps)
            
            # 执行步骤
            phase_success = True
            for i, step_data in enumerate(steps):
                description = step_data.get("description", "No description")
                command = step_data.get("command", "")
                
                console.print(f"\n[bold cyan]步骤 {i+1}/{len(steps)}:[/bold cyan] {description}")
                console.print(f"[dim]命令: {command}[/dim]")
                
                # 执行命令（带重试和重新生成）
                retry_count = 0
                step_success = False
                current_command = command
                current_description = description
                max_regenerate_attempts = 5
                regenerate_count = 0
                
                while retry_count <= Config.MAX_RETRIES:
                    # 执行命令
                    result = CommandExecutor.execute(
                        current_command,
                        cwd=session_cwd,
                        description=current_description,
                        ssh_config=self.ssh_config
                    )
                    
                    # 检查是否需要重新生成命令
                    if result.get("regenerate") and regenerate_count < max_regenerate_attempts:
                        feedback = result.get("feedback", "")
                        console.print(f"[cyan]根据反馈重新生成命令...[/cyan]")
                        console.print(f"[dim]用户反馈: {feedback}[/dim]")
                        
                        try:
                            with console.status("[bold green]重新生成命令...[/bold green]", spinner="dots"):
                                new_step = self.llm.regenerate_command(
                                    original_command=current_command,
                                    original_description=current_description,
                                    user_feedback=feedback,
                                    context_str=context_str,
                                    user_goal=user_query,
                                    user_context=user_context
                                )
                            
                            # 更新命令和描述
                            current_command = new_step.get("command", current_command)
                            current_description = new_step.get("description", current_description)
                            regenerate_count += 1
                            
                            console.print(f"[green]✓ 已重新生成命令:[/green]")
                            console.print(f"[dim]描述: {current_description}[/dim]")
                            console.print(f"[dim]命令: {current_command}[/dim]")
                            
                            # 重新尝试执行新命令
                            continue
                            
                        except Exception as e:
                            console.print(f"[red]重新生成命令失败: {e}[/red]")
                            return
                    
                    if not result["executed"]:
                        console.print("[yellow]用户取消执行[/yellow]")
                        return
                    
                    # 创建执行步骤记录
                    exec_step = ExecutionStep(
                        description=description,
                        command=current_command,
                        output=result["stdout"] if result["return_code"] == 0 else result["stderr"],
                        success=result["return_code"] == 0,
                        status=StepStatus.SUCCESS if result["return_code"] == 0 else StepStatus.FAILED,
                        error_message=result["stderr"] if result["return_code"] != 0 else None,
                        retry_count=retry_count
                    )
                    
                    # 添加到上下文
                    exec_context.add_step_to_current_phase(exec_step)
                    error_manager.record_execution_result(exec_step.success)
                    
                    if exec_step.success:
                        console.print(f"[green]✓ 成功[/green]")
                        if result["stdout"].strip():
                            output_preview = result["stdout"][:500]
                            if len(result["stdout"]) > 500:
                                output_preview += "\n... (输出已截断)"
                            console.print(Panel(output_preview, title="输出", border_style="green", expand=False))
                        step_success = True
                        break
                    else:
                        # 失败 - 分析错误
                        console.print(f"[red]✗ 失败 (尝试 {retry_count + 1}/{Config.MAX_RETRIES + 1})[/red]")
                        error_msg = result["stderr"] or result["stdout"]
                        console.print(Panel(error_msg, title="错误", border_style="red", expand=False))
                        
                        # 错误分析
                        error_analysis = error_manager.analyze_error(
                            current_command,
                            error_msg,
                            result["return_code"]
                        )
                        
                        console.print(f"[yellow]错误类型: {error_analysis.error_type.value}[/yellow]")
                        console.print(f"[yellow]分析: {error_analysis.explanation}[/yellow]")
                        
                        # 判断是否重试
                        should_retry, retry_command = error_manager.should_retry(current_command, error_analysis)
                        
                        if not should_retry:
                            console.print("[red]无法恢复，跳过此步骤[/red]")
                            break
                        
                        if retry_command:
                            # 有具体的重试命令（如添加 sudo）
                            console.print(f"[cyan]重试命令: {retry_command}[/cyan]")
                            current_command = retry_command
                            retry_count += 1
                        else:
                            # 需要 LLM 生成修复方案
                            console.print("[cyan]请求 AI 生成修复方案...[/cyan]")
                            try:
                                recovery_prompt = error_manager.get_recovery_prompt(error_analysis)
                                fix_plan = self.llm.generate_next_steps(
                                    user_goal=recovery_prompt,
                                    context_str=context_str + "\n\n" + exec_context.get_context_summary(),
                                    execution_history=[],
                                    max_steps=1,
                                    user_context=user_context
                                )
                                
                                if fix_plan.get("steps"):
                                    current_command = fix_plan["steps"][0]["command"]
                                    console.print(f"[cyan]AI 建议: {current_command}[/cyan]")
                                    retry_count += 1
                                else:
                                    console.print("[red]AI 无法生成修复方案[/red]")
                                    break
                            except Exception as e:
                                console.print(f"[red]生成修复方案失败: {e}[/red]")
                                break
                
                if not step_success:
                    phase_success = False
                    console.print("[yellow]步骤失败，继续下一阶段[/yellow]")
                    break
            
            # 完成当前阶段
            exec_context.complete_current_phase(success=phase_success)
            
            # 显示进度
            planner.display_progress()
        
        # 任务完成
        console.print("\n" + "="*60)
        if planner.is_plan_complete():
            console.print("[bold green]✓ 所有阶段完成！[/bold green]")
        elif iteration >= max_iterations:
            console.print("[yellow]达到最大迭代次数[/yellow]")
        else:
            console.print("[yellow]任务执行中断[/yellow]")
        
        # 显示最终摘要
        console.print(f"\n[bold]执行摘要:[/bold]")
        console.print(f"总阶段数: {len(exec_context.phases)}")
        console.print(f"完成阶段: {sum(1 for p in exec_context.phases if p.is_complete())}")
        console.print(f"总步骤数: {exec_context.total_steps}")
        console.print(f"成功步骤: {exec_context.successful_steps}")
        console.print(f"失败步骤: {exec_context.failed_steps}")
        console.print(f"总体进度: {planner.get_progress()*100:.0f}%")

    def _print_plan_table(self, steps):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Task Description", min_width=20)
        table.add_column("Command", style="cyan")

        for i, step in enumerate(steps):
            table.add_row(str(i+1), step.get("description", ""), step.get("command", ""))
        
        console.print(table)
