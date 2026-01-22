#!/usr/bin/env python3
"""
Ollama 集成测试脚本

测试 AutoShell 与 Ollama 的集成是否正常工作。
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()

def test_ollama_connection():
    """测试 Ollama 连接"""
    console.print(Panel.fit(
        "[bold blue]Ollama 连接测试[/bold blue]",
        border_style="blue"
    ))
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            console.print("[green]✓[/green] Ollama 服务运行正常")
            models = response.json().get("models", [])
            if models:
                console.print(f"[green]✓[/green] 已安装 {len(models)} 个模型:")
                for model in models:
                    console.print(f"  - {model['name']}")
            else:
                console.print("[yellow]⚠[/yellow] 未找到已安装的模型")
                console.print("[dim]提示: 运行 'ollama pull qwen2.5:7b' 下载模型[/dim]")
            return True
        else:
            console.print(f"[red]✗[/red] Ollama 服务响应异常: {response.status_code}")
            return False
    except Exception as e:
        console.print(f"[red]✗[/red] 无法连接到 Ollama: {str(e)}")
        console.print("[dim]提示: 确保 Ollama 已安装并运行[/dim]")
        console.print("[dim]安装: https://ollama.ai[/dim]")
        console.print("[dim]启动: ollama serve[/dim]")
        return False

def test_config():
    """测试配置"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]配置测试[/bold blue]",
        border_style="blue"
    ))
    
    # 设置 Ollama 配置
    os.environ["OPENAI_API_KEY"] = "ollama"
    os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
    os.environ["LLM_MODEL"] = "qwen2.5:7b"
    
    try:
        from autoshell.config import Config
        Config.validate()
        
        if Config.is_ollama():
            console.print("[green]✓[/green] Ollama 配置检测正确")
        else:
            console.print("[red]✗[/red] Ollama 配置检测失败")
            return False
        
        console.print(f"[green]✓[/green] API Base URL: {Config.OPENAI_BASE_URL}")
        console.print(f"[green]✓[/green] Model: {Config.LLM_MODEL}")
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] 配置验证失败: {str(e)}")
        return False

def test_llm_client():
    """测试 LLM 客户端"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]LLM 客户端测试[/bold blue]",
        border_style="blue"
    ))
    
    try:
        from autoshell.llm import LLMClient
        from autoshell.context import ContextManager
        
        client = LLMClient()
        
        if not client.is_ollama:
            console.print("[red]✗[/red] LLM 客户端未检测到 Ollama")
            return False
        
        console.print("[green]✓[/green] LLM 客户端初始化成功")
        
        # 测试简单查询
        console.print("\n[dim]测试查询: '列出当前目录的文件'[/dim]")
        context_str = ContextManager.get_context_string()
        
        plan = client.generate_plan(
            "列出当前目录的文件",
            context_str
        )
        
        if "steps" in plan and len(plan["steps"]) > 0:
            console.print(f"[green]✓[/green] 成功生成计划，包含 {len(plan['steps'])} 个步骤")
            console.print(f"[dim]思路: {plan.get('thought', 'N/A')}[/dim]")
            for i, step in enumerate(plan["steps"], 1):
                console.print(f"[dim]  {i}. {step.get('description', 'N/A')}[/dim]")
            return True
        else:
            console.print("[red]✗[/red] 生成的计划格式不正确")
            return False
            
    except Exception as e:
        console.print(f"[red]✗[/red] LLM 客户端测试失败: {str(e)}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False

def main():
    """运行所有测试"""
    console.print(Panel.fit(
        "[bold cyan]AutoShell Ollama 集成测试[/bold cyan]\n"
        "测试 Ollama 集成是否正常工作",
        title="测试套件",
        border_style="cyan"
    ))
    
    results = []
    
    # 测试 1: Ollama 连接
    results.append(("Ollama 连接", test_ollama_connection()))
    
    # 测试 2: 配置
    results.append(("配置验证", test_config()))
    
    # 测试 3: LLM 客户端
    results.append(("LLM 客户端", test_llm_client()))
    
    # 总结
    console.print("\n")
    console.print(Panel.fit(
        "[bold blue]测试总结[/bold blue]",
        border_style="blue"
    ))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[green]✓ 通过[/green]" if result else "[red]✗ 失败[/red]"
        console.print(f"{status} - {name}")
    
    console.print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        console.print("\n[bold green]🎉 所有测试通过！Ollama 集成正常工作。[/bold green]")
        return 0
    else:
        console.print("\n[bold red]❌ 部分测试失败，请检查配置和 Ollama 服务。[/bold red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
