import sys
from rich.console import Console
from rich.panel import Panel
from autoshell.agent import AutoShellAgent
from autoshell.context import ContextManager

console = Console()

def main():
    try:
        console.print(Panel.fit(
            "[bold blue]AutoShell[/bold blue] - Intelligent Command Line Assistant\n"
            "Type 'exit' or 'quit' to close.",
            title="Welcome",
            border_style="blue"
        ))

        agent = AutoShellAgent()
        
        # 显示当前上下文
        ctx = ContextManager.get_full_context()
        console.print(f"[dim]Detected: {ctx['os']} | {ctx['shell']} | {ctx['user']}[/dim]\n")

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
