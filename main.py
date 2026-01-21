import sys
import argparse
import io
from rich.console import Console
from rich.panel import Panel
from autoshell.agent import AutoShellAgent
from autoshell.context import ContextManager

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
  
  # SSH模式（交互）
  python main.py --ssh-host user@example.com --ssh-port 22
  
  # SSH模式（一次性执行）
  python main.py --ssh-host user@example.com -c "检查磁盘使用情况"
  
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
    
    return parser.parse_args()

def main():
    try:
        args = parse_args()
        
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
                "Type 'exit' or 'quit' to close.",
                title="Welcome",
                border_style="blue"
            ))

        agent = AutoShellAgent(ssh_config=ssh_config)
        
        # 显示当前上下文
        ctx = ContextManager.get_full_context()
        if ssh_config:
            console.print(f"[dim]Mode: SSH Remote | Target: {args.ssh_host}[/dim]\n")
        else:
            console.print(f"[dim]Detected: {ctx['os']} | {ctx['shell']} | {ctx['user']}[/dim]\n")

        # 一次性执行模式
        if args.command:
            agent.run(args.command)
            return
        
        # 交互模式
        while True:
            try:
                user_input = console.input("[bold cyan]AutoShell > [/bold cyan]").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ["exit", "quit"]:
                    console.print("[bold green]Goodbye![/bold green]")
                    break
                    
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
