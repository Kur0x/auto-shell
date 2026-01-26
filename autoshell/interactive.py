"""
交互式用户输入处理模块

提供统一的用户交互接口，支持：
- 确认（是/否）
- 文本输入（带验证）
- 多选项选择
- 密码输入（隐藏显示）
"""

import re
from typing import Optional, List, Any, Dict
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class InteractiveHandler:
    """处理用户交互的统一接口"""
    
    # 支持的交互命令类型
    INTERACTIVE_COMMANDS = {
        "__USER_CONFIRM__": "confirm",
        "__USER_INPUT__": "input",
        "__USER_CHOICE__": "choice",
        "__USER_PASSWORD__": "password"
    }
    
    @classmethod
    def is_interactive_command(cls, command: str) -> bool:
        """检查命令是否为交互式命令"""
        return command in cls.INTERACTIVE_COMMANDS
    
    @classmethod
    def handle_interactive_step(cls, step: Dict[str, Any]) -> Optional[Any]:
        """
        处理交互式步骤
        
        :param step: 步骤字典，包含 command, prompt, 以及其他参数
        :return: 用户输入的值，如果用户取消则返回 None
        """
        command = step.get("command", "")
        
        if not cls.is_interactive_command(command):
            raise ValueError(f"Unknown interactive command: {command}")
        
        command_type = cls.INTERACTIVE_COMMANDS[command]
        
        try:
            if command_type == "confirm":
                return cls.handle_confirm(
                    prompt=step.get("prompt", "确认继续？"),
                    default=step.get("default", "yes")
                )
            elif command_type == "input":
                return cls.handle_input(
                    prompt=step.get("prompt", "请输入"),
                    default=step.get("default", ""),
                    validation=step.get("validation")
                )
            elif command_type == "choice":
                return cls.handle_choice(
                    prompt=step.get("prompt", "请选择"),
                    options=step.get("options", []),
                    default=step.get("default")
                )
            elif command_type == "password":
                return cls.handle_password(
                    prompt=step.get("prompt", "请输入密码")
                )
        except KeyboardInterrupt:
            console.print("\n[yellow]用户取消操作[/yellow]")
            return None
        except EOFError:
            console.print("\n[yellow]输入中断[/yellow]")
            return None
    
    @staticmethod
    def handle_confirm(prompt: str, default: str = "yes") -> bool:
        """
        处理是/否确认
        
        :param prompt: 提示信息
        :param default: 默认值 ("yes" 或 "no")
        :return: True 表示确认，False 表示拒绝
        """
        # 显示提示面板
        panel = Panel(
            f"[bold yellow]⚠️  {prompt}[/bold yellow]",
            title="[bold blue]确认操作[/bold blue]",
            border_style="yellow",
            expand=False
        )
        console.print(panel)
        
        # 获取用户确认
        default_bool = default.lower() in ["yes", "y", "true", "1"]
        result = Confirm.ask(
            "[bold cyan]是否继续？[/bold cyan]",
            default=default_bool
        )
        
        if result:
            console.print("[green]✓ 已确认[/green]")
        else:
            console.print("[yellow]✗ 已取消[/yellow]")
        
        return result
    
    @staticmethod
    def handle_input(
        prompt: str,
        default: str = "",
        validation: Optional[str] = None
    ) -> str:
        """
        处理文本输入（带验证）
        
        :param prompt: 提示信息
        :param default: 默认值
        :param validation: 正则表达式验证模式
        :return: 用户输入的字符串
        """
        # 显示提示面板
        panel_content = f"[bold cyan]📝 {prompt}[/bold cyan]"
        if default:
            panel_content += f"\n[dim]默认值: {default}[/dim]"
        if validation:
            panel_content += f"\n[dim]格式要求: {validation}[/dim]"
        
        panel = Panel(
            panel_content,
            title="[bold blue]输入信息[/bold blue]",
            border_style="cyan",
            expand=False
        )
        console.print(panel)
        
        # 编译验证正则表达式
        pattern = None
        if validation:
            try:
                pattern = re.compile(validation)
            except re.error as e:
                console.print(f"[yellow]警告: 无效的验证模式: {e}[/yellow]")
                pattern = None
        
        # 循环获取输入直到验证通过
        while True:
            if default:
                user_input = Prompt.ask(
                    "[bold cyan]请输入[/bold cyan]",
                    default=default
                )
            else:
                user_input = Prompt.ask("[bold cyan]请输入[/bold cyan]")
            
            # 如果没有验证模式，直接返回
            if not pattern:
                console.print(f"[green]✓ 已接收: {user_input}[/green]")
                return user_input
            
            # 验证输入
            if user_input and pattern.match(user_input):
                console.print(f"[green]✓ 已接收: {user_input}[/green]")
                return user_input
            else:
                console.print(f"[red]✗ 输入格式不正确，请重试[/red]")
                console.print(f"[dim]要求格式: {validation}[/dim]")
    
    @staticmethod
    def handle_choice(
        prompt: str,
        options: List[str],
        default: Optional[str] = None
    ) -> str:
        """
        处理多选项选择
        
        :param prompt: 提示信息
        :param options: 选项列表
        :param default: 默认选项
        :return: 用户选择的选项
        """
        if not options:
            console.print("[red]错误: 没有可选项[/red]")
            return ""
        
        # 创建选项表格
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("序号", style="cyan", width=4)
        table.add_column("选项", style="white")
        
        for i, option in enumerate(options, 1):
            marker = " [dim](默认)[/dim]" if option == default else ""
            table.add_row(f"{i}.", f"{option}{marker}")
        
        # 显示提示面板
        panel = Panel(
            f"[bold cyan]🔢 {prompt}[/bold cyan]\n\n{table}",
            title="[bold blue]选择选项[/bold blue]",
            border_style="cyan",
            expand=False
        )
        console.print(panel)
        
        # 确定默认选项的索引
        default_index = None
        if default and default in options:
            default_index = options.index(default) + 1
        
        # 循环获取选择直到有效
        while True:
            if default_index:
                choice_str = Prompt.ask(
                    f"[bold cyan]请选择 [1-{len(options)}][/bold cyan]",
                    default=str(default_index)
                )
            else:
                choice_str = Prompt.ask(
                    f"[bold cyan]请选择 [1-{len(options)}][/bold cyan]"
                )
            
            try:
                choice_index = int(choice_str)
                if 1 <= choice_index <= len(options):
                    selected = options[choice_index - 1]
                    console.print(f"[green]✓ 已选择: {selected}[/green]")
                    return selected
                else:
                    console.print(f"[red]✗ 请输入 1 到 {len(options)} 之间的数字[/red]")
            except ValueError:
                console.print(f"[red]✗ 请输入有效的数字[/red]")
    
    @staticmethod
    def handle_password(prompt: str) -> str:
        """
        处理密码输入（隐藏显示）
        
        :param prompt: 提示信息
        :return: 用户输入的密码
        """
        # 显示提示面板
        panel = Panel(
            f"[bold yellow]🔒 {prompt}[/bold yellow]\n[dim]输入将被隐藏[/dim]",
            title="[bold blue]密码输入[/bold blue]",
            border_style="yellow",
            expand=False
        )
        console.print(panel)
        
        # 获取密码（隐藏输入）
        password = Prompt.ask(
            "[bold yellow]密码[/bold yellow]",
            password=True
        )
        
        if password:
            console.print("[green]✓ 密码已接收[/green]")
        else:
            console.print("[yellow]⚠ 密码为空[/yellow]")
        
        return password


class UserInputContext:
    """用户输入上下文管理器"""
    
    def __init__(self):
        self.inputs: Dict[int, Any] = {}  # {step_index: value}
        self._password_steps: set = set()  # 记录哪些步骤是密码输入
    
    def store(self, step_index: int, value: Any, is_password: bool = False):
        """存储用户输入"""
        self.inputs[step_index] = value
        if is_password:
            self._password_steps.add(step_index)
    
    def get(self, step_index: int, default: Any = None) -> Any:
        """获取用户输入"""
        return self.inputs.get(step_index, default)
    
    def replace_placeholders(self, command: str) -> str:
        """
        替换命令中的用户输入占位符
        
        支持的占位符格式：
        - ${USER_INPUT_N} - 引用第N步的用户输入
        - ${USER_INPUT_LAST} - 引用最后一次用户输入
        
        :param command: 原始命令
        :return: 替换后的命令
        """
        import re
        
        # 替换 ${USER_INPUT_N}
        def replace_indexed(match):
            index = int(match.group(1))
            value = self.get(index, "")
            return str(value)
        
        command = re.sub(r'\$\{USER_INPUT_(\d+)\}', replace_indexed, command)
        
        # 替换 ${USER_INPUT_LAST}
        if self.inputs:
            last_value = self.inputs[max(self.inputs.keys())]
            command = command.replace('${USER_INPUT_LAST}', str(last_value))
        
        return command
    
    def clear(self):
        """清空所有用户输入"""
        self.inputs.clear()
    
    def summary(self) -> str:
        """生成用户输入摘要"""
        if not self.inputs:
            return "无用户输入"
        
        lines = ["用户输入历史:"]
        for step_index, value in sorted(self.inputs.items()):
            # 隐藏密码类型的值
            display_value = "***" if isinstance(value, str) and len(value) > 0 and step_index in self._password_steps else value
            lines.append(f"  步骤 {step_index}: {display_value}")
        
        return "\n".join(lines)
