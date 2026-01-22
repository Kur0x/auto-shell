import sys
import argparse
import io
from rich.console import Console
from rich.panel import Panel
from autoshell.agent import AutoShellAgent
from autoshell.context import ContextManager
from autoshell.config import Config

# 设置标准输出编码为UTF-8，避免Windows下的编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

console = Console()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AutoShell - Intelligent Command Line Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 交互模式（本地）
  python main.py
  
  # 一次性执行（本地）
  python main.py -c "列出当前目录下的所有文件"
  
  # 自适应执行模式（根据输出动态调整）
  python main.py --adaptive -c "执行test.sh，如果输出为1则修改为2"
  
  # SSH模式（交互）
  python main.py --ssh-host user@example.com --ssh-port 22
  
  # SSH模式（一次性执行）
  python main.py --ssh-host user@example.com -c "检查磁盘使用情况"
  
  # SSH + 自适应模式
  python main.py --ssh-host user@example.com --adaptive -c "检查日志并提取错误"
  
  # SSH模式（使用密钥）
  python main.py --ssh-host user@example.com --ssh-key ~/.ssh/id_rsa -c "重启nginx"
        """
    )
    
    # 一次性执行参数
    parser.add_argument(
        '-c', '--command',
        type=str,
        help='一次性执行命令后退出（非交互模式）'
    )
    
    # SSH相关参数
    parser.add_argument(
        '--ssh-host',
        type=str,
        help='SSH远程主机（格式：user@host）'
    )
    
    parser.add_argument(
        '--ssh-port',
        type=int,
        default=22,
        help='SSH端口（默认：22）'
    )
    
    parser.add_argument(
        '--ssh-password',
        type=str,
        help='SSH密码（不推荐，建议使用密钥）'
    )
    
    parser.add_argument(
        '--ssh-key',
        type=str,
        help='SSH私钥文件路径'
    )
    
    parser.add_argument(
        '--adaptive',
        action='store_true',
        help='启用自适应执行模式（根据输出动态生成下一步）'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试输出模式'
    )
    
    return parser.parse_args()

def main():
    try:
        args = parse_args()
        
        # 设置全局DEBUG标志
        Config.DEBUG = args.debug
        
        # 判断是否为SSH模式
        ssh_config = None
        if args.ssh_host:
            ssh_config = {
                'host': args.ssh_host,
                'port': args.ssh_port,
                'password': args.ssh_password,
                'key_filename': args.ssh_key
            }
            console.print(Panel.fit(
                f"[bold blue]AutoShell[/bold blue] - SSH Remote Mode\n"
                f"Connecting to: {args.ssh_host}:{args.ssh_port}",
                title="SSH Mode",
                border_style="blue"
            ))
        else:
            console.print(Panel.fit(
                "[bold blue]AutoShell[/bold blue] - Intelligent Command Line Assistant\n"
                "Type 'exit' or 'quit' to close, or press Ctrl+D.",
                title="Welcome",
                border_style="blue"
            ))

        # 初始化Agent（SSH模式下会先测试连接）
        try:
            agent = AutoShellAgent(ssh_config=ssh_config)
        except ConnectionError as e:
            # SSH连接失败，直接退出
            console.print(f"\n[bold red]Error:[/bold red] Unable to establish SSH connection.")
            console.print(f"[yellow]Please check your SSH configuration and try again.[/yellow]")
            sys.exit(1)
        
        # 显示当前上下文（使用增强的信息）
        if ssh_config:
            # SSH模式
            if agent._system_info_cache:
                info = agent._system_info_cache
                distro = info.get('distro_pretty_name', 'Unknown Linux')
                arch = info.get('architecture', 'unknown')
                pkg_mgr = info.get('package_manager', 'unknown')
                console.print(f"[dim]Remote System: {distro} | {arch} | Package Manager: {pkg_mgr}[/dim]\n")
            else:
                console.print(f"[dim]Mode: SSH Remote | Target: {args.ssh_host}[/dim]\n")
        else:
            # 本地模式
            if agent._system_info_cache:
                info = agent._system_info_cache
                os_type = info.get('os_type', 'Unknown')
                
                if os_type == "Linux":
                    distro = info.get('distro_pretty_name', 'Unknown Linux')
                    pkg_mgr = info.get('package_manager', 'unknown')
                    console.print(f"[dim]Detected: {distro} | Package Manager: {pkg_mgr}[/dim]\n")
                elif os_type == "Windows":
                    win_ver = info.get('windows_release', 'Unknown')
                    console.print(f"[dim]Detected: Windows {win_ver} | {info.get('architecture', 'unknown')}[/dim]\n")
                elif os_type == "Darwin":
                    macos_release = info.get('macos_release', 'Unknown')
                    console.print(f"[dim]Detected: macOS {macos_release} | {info.get('architecture', 'unknown')}[/dim]\n")
            else:
                ctx = ContextManager.get_full_context()
                console.print(f"[dim]Detected: {ctx['os']} | {ctx['shell']} | {ctx['user']}[/dim]\n")

        # 一次性执行模式
        if args.command:
            if args.adaptive:
                agent.run_adaptive(args.command)
            else:
                agent.run(args.command)
            return
        
        # 交互模式
        while True:
            try:
                user_input = console.input("[bold cyan]AutoShell > [/bold cyan]").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("[bold green]Goodbye![/bold green]")
                    break

                # 检查Ctrl+D退出
                if user_input == '\x04':
                    console.print("[bold green]Goodbye![/bold green]")
                    break

                # 检查是否使用自适应模式
                if args.adaptive:
                    agent.run_adaptive(user_input)
                else:
                    agent.run(user_input)
                console.print() # 空行分隔
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user.[/yellow]")
                continue
            except EOFError:
                break
                
    except Exception as e:
        console.print(f"[bold red]Fatal Error:[/bold red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
