import subprocess
import shlex
import os
import time
from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

# 尝试导入paramiko，如果不存在则SSH功能不可用
try:
    import paramiko
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False
    paramiko = None  # type: ignore

class CommandExecutor:
    # 不可变白名单 (扩充)
    WHITELIST = {
        "ls", "dir", "pwd", "echo", "date", "whoami", "hostname", "uname", "cd",
        "mkdir", "touch", "cat", "type", "cp", "grep", "find", "head", "tail",
        "df", "du", "sort", "wc", "ps", "top", "free", "uptime", "netstat", "ss",
        "systemctl", "service", "journalctl", "dmesg", "lsof", "which", "whereis",
        "sudo", "xargs", "awk", "sed", "sleep"
    }

    @classmethod
    def is_safe(cls, command: str) -> bool:
        """
        检查命令是否在白名单中。
        允许管道操作，但检查管道中的每个命令。
        """
        try:
            # 允许管道，但不允许 && || ; 这些可能执行多个独立命令的操作符
            if any(op in command for op in ["&&", "||", ";"]):
                return False

            # 如果包含管道，检查管道中的每个命令
            if "|" in command:
                # 分割管道命令
                pipe_commands = command.split("|")
                for pipe_cmd in pipe_commands:
                    tokens = shlex.split(pipe_cmd.strip())
                    if not tokens:
                        return False
                    cmd_base = tokens[0].lower()
                    if cmd_base not in cls.WHITELIST:
                        return False
                return True
            
            # 单个命令检查
            tokens = shlex.split(command)
            if not tokens:
                return False
            
            cmd_base = tokens[0].lower()
            return cmd_base in cls.WHITELIST
            
        except Exception:
            return False

    @classmethod
    def execute(cls, command: str, cwd: Optional[str] = None, description: Optional[str] = None, ssh_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行命令，包含安全检查和用户确认。支持本地和SSH远程执行。
        
        :param command: 要执行的 Shell 命令
        :param cwd: 命令执行的工作目录 (None 表示当前进程目录)
        :param description: 步骤描述，用于 UI 展示
        :param ssh_config: SSH配置字典（host, port, password, key_filename）
        :return: 结果字典
        """
        
        # SSH模式
        if ssh_config:
            return cls._execute_ssh(command, cwd, description, ssh_config)
        
        # 本地模式
        is_safe_cmd = cls.is_safe(command)
        
        if not is_safe_cmd:
            if description:
                console.print(f"[bold blue]Step:[/bold blue] {description}")
            
            syntax = Syntax(command, "bash", theme="monokai", line_numbers=False, word_wrap=True)
            console.print(Panel(syntax, title="[bold red]Review Safe-Check[/bold red]", expand=True, border_style="red"))
            
            if not Confirm.ask("[bold red]Command not in whitelist. Execute?[/bold red]", default=True):
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

            # 使用Popen实现实时输出
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # 行缓冲
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # 实时读取输出
            try:
                while True:
                    # 检查进程是否结束
                    if process.poll() is not None:
                        break
                    
                    # 读取stdout（非阻塞）
                    import select
                    import sys
                    
                    # Windows不支持select，使用简单的readline
                    if sys.platform == 'win32':
                        if process.stdout:
                            line = process.stdout.readline()
                            if line:
                                stdout_lines.append(line)
                                print(line, end='', flush=True)
                    else:
                        # Unix系统使用select
                        streams = []
                        if process.stdout:
                            streams.append(process.stdout)
                        if process.stderr:
                            streams.append(process.stderr)
                        
                        if streams:
                            readable, _, _ = select.select(streams, [], [], 0.1)
                            
                            if process.stdout and process.stdout in readable:
                                line = process.stdout.readline()
                                if line:
                                    stdout_lines.append(line)
                                    print(line, end='', flush=True)
                            
                            if process.stderr and process.stderr in readable:
                                line = process.stderr.readline()
                                if line:
                                    stderr_lines.append(line)
                                    console.print(line, style="red", end='')
                
                # 读取剩余输出
                if process.stdout:
                    remaining_stdout = process.stdout.read()
                    if remaining_stdout:
                        stdout_lines.append(remaining_stdout)
                        print(remaining_stdout, end='', flush=True)
                
                if process.stderr:
                    remaining_stderr = process.stderr.read()
                    if remaining_stderr:
                        stderr_lines.append(remaining_stderr)
                        console.print(remaining_stderr, style="red", end='')
                
                # 等待进程结束
                process.wait()
                
                return {
                    "return_code": process.returncode,
                    "stdout": ''.join(stdout_lines),
                    "stderr": ''.join(stderr_lines),
                    "executed": True
                }
                
            except KeyboardInterrupt:
                # 用户中断
                console.print("\n[yellow]Terminating process...[/yellow]")
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                return {
                    "return_code": -1,
                    "stdout": ''.join(stdout_lines),
                    "stderr": "Process interrupted by user (Ctrl+C)",
                    "executed": True
                }
                
        except Exception as e:
             return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "executed": True
            }
    
    @classmethod
    def _execute_ssh(cls, command: str, cwd: Optional[str] = None, description: Optional[str] = None, ssh_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        通过SSH执行远程命令
        
        :param command: 要执行的命令
        :param cwd: 远程工作目录
        :param description: 步骤描述
        :param ssh_config: SSH配置
        :return: 结果字典
        """
        if not SSH_AVAILABLE:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": "SSH support not available. Please install paramiko: pip install paramiko",
                "executed": False
            }
        
        if not ssh_config or 'host' not in ssh_config:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": "Invalid SSH configuration",
                "executed": False
            }
        
        # 解析host（可能包含user@host格式）
        host_str = ssh_config['host']
        if '@' in host_str:
            username, hostname = host_str.split('@', 1)
        else:
            username = None
            hostname = host_str
        
        port = ssh_config.get('port', 22)
        password = ssh_config.get('password')
        key_filename = ssh_config.get('key_filename')
        
        # 安全检查（SSH模式下也需要确认危险命令）
        is_safe_cmd = cls.is_safe(command)
        
        if not is_safe_cmd:
            if description:
                console.print(f"[bold blue]Step:[/bold blue] {description}")
            
            syntax = Syntax(command, "bash", theme="monokai", line_numbers=False, word_wrap=True)
            console.print(Panel(syntax, title="[bold red]Review Safe-Check (SSH)[/bold red]", expand=True, border_style="red"))
            
            if not Confirm.ask(f"[bold red]Execute on {hostname}?[/bold red]", default=True):
                return {"return_code": -1, "stdout": "", "stderr": "User aborted execution.", "executed": False}
        
        try:
            # 创建SSH客户端
            client = paramiko.SSHClient()  # type: ignore
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # type: ignore
            
            # 加载SSH配置文件
            ssh_config_obj = paramiko.SSHConfig()  # type: ignore
            ssh_config_path = os.path.expanduser('~/.ssh/config')
            if os.path.exists(ssh_config_path):
                with open(ssh_config_path) as f:
                    ssh_config_obj.parse(f)
                
                # 查找主机配置
                host_config = ssh_config_obj.lookup(hostname)
                
                # 从配置文件获取实际的主机名和其他参数
                hostname = host_config.get('hostname', hostname)
                if not username and 'user' in host_config:
                    username = host_config['user']
                if not key_filename and 'identityfile' in host_config:
                    key_filename = host_config['identityfile'][0] if isinstance(host_config['identityfile'], list) else host_config['identityfile']
                if 'port' in host_config:
                    port = int(host_config['port'])
            
            # 连接参数
            connect_kwargs = {
                'hostname': hostname,
                'port': port,
            }
            
            if username:
                connect_kwargs['username'] = username
            
            if key_filename:
                # 展开路径中的 ~
                key_filename = os.path.expanduser(key_filename)
                connect_kwargs['key_filename'] = key_filename
            elif password:
                connect_kwargs['password'] = password
            
            # 连接到远程主机
            client.connect(**connect_kwargs)
            
            # 如果指定了工作目录，需要在命令前加上cd
            if cwd:
                command = f"cd {cwd} && {command}"
            
            # 使用PTY执行命令，支持信号传递和中断
            stdin, stdout, stderr = client.exec_command(
                command,
                get_pty=True  # 关键：分配伪终端，支持信号传递
            )
            
            # 设置channel为非阻塞模式
            stdout.channel.setblocking(0)
            
            stdout_data = []
            stderr_data = []
            
            try:
                # 非阻塞读取输出，实时显示并可响应KeyboardInterrupt
                while not stdout.channel.exit_status_ready():
                    # 检查是否有标准输出数据
                    if stdout.channel.recv_ready():
                        data = stdout.channel.recv(4096)
                        decoded = data.decode('utf-8', errors='replace')
                        stdout_data.append(decoded)
                        # 实时输出到控制台
                        print(decoded, end='', flush=True)
                    
                    # 检查是否有标准错误数据
                    if stdout.channel.recv_stderr_ready():
                        data = stdout.channel.recv_stderr(4096)
                        decoded = data.decode('utf-8', errors='replace')
                        stderr_data.append(decoded)
                        # 实时输出错误到控制台（使用红色）
                        console.print(decoded, style="red", end='')
                    
                    # 短暂休眠，避免CPU占用过高
                    time.sleep(0.05)  # 减少延迟以提高响应速度
                
                # 读取剩余数据
                while stdout.channel.recv_ready():
                    data = stdout.channel.recv(4096)
                    decoded = data.decode('utf-8', errors='replace')
                    stdout_data.append(decoded)
                    print(decoded, end='', flush=True)
                
                while stdout.channel.recv_stderr_ready():
                    data = stdout.channel.recv_stderr(4096)
                    decoded = data.decode('utf-8', errors='replace')
                    stderr_data.append(decoded)
                    console.print(decoded, style="red", end='')
                
                # 获取退出状态
                return_code = stdout.channel.recv_exit_status()
                
                # 关闭连接
                client.close()
                
                return {
                    "return_code": return_code,
                    "stdout": ''.join(stdout_data),
                    "stderr": ''.join(stderr_data),
                    "executed": True
                }
                
            except KeyboardInterrupt:
                # 用户按下Ctrl+C，发送中断信号到远程进程
                console.print("\n[yellow]Sending interrupt signal to remote process...[/yellow]")
                
                try:
                    # 发送Ctrl+C (ASCII 3) 到远程进程
                    stdout.channel.send(b'\x03')
                    
                    # 等待一小段时间让进程响应
                    time.sleep(0.5)
                    
                    # 如果进程还在运行，再次发送中断信号
                    if not stdout.channel.exit_status_ready():
                        stdout.channel.send(b'\x03')
                        time.sleep(0.5)
                    
                    # 读取剩余输出并实时显示
                    while stdout.channel.recv_ready():
                        data = stdout.channel.recv(4096)
                        decoded = data.decode('utf-8', errors='replace')
                        stdout_data.append(decoded)
                        print(decoded, end='', flush=True)
                    
                    while stdout.channel.recv_stderr_ready():
                        data = stdout.channel.recv_stderr(4096)
                        decoded = data.decode('utf-8', errors='replace')
                        stderr_data.append(decoded)
                        console.print(decoded, style="red", end='')
                    
                except Exception as e:
                    # 忽略发送中断信号时的错误
                    pass
                
                # 关闭连接
                try:
                    stdout.channel.close()
                except:
                    pass
                
                client.close()
                
                return {
                    "return_code": -1,
                    "stdout": ''.join(stdout_data),
                    "stderr": "Command interrupted by user (Ctrl+C)",
                    "executed": True
                }
            
        except Exception as e:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": f"SSH Error: {str(e)}",
                "executed": True
            }
