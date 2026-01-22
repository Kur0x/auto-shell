# OS信息增强功能实施指南

## 概述

本文档提供详细的代码实现指导，用于在AutoShell中添加详细的操作系统信息收集功能。

## 实施步骤

### 步骤1：扩展ContextManager（本地信息收集）

修改 [`autoshell/context.py`](autoshell/context.py)，添加详细信息收集功能。

#### 1.1 添加辅助函数

```python
import os
import platform
import getpass
import shutil
import subprocess
import re

class ContextManager:
    """负责感知当前运行环境的上下文信息。"""
    
    # 保留现有方法...
    
    @staticmethod
    def _read_file_safe(filepath: str) -> str:
        """安全读取文件内容"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    @staticmethod
    def _run_command_safe(command: str) -> str:
        """安全执行命令并返回输出"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    @staticmethod
    def _parse_os_release(content: str) -> dict:
        """解析 /etc/os-release 文件内容"""
        info = {}
        for line in content.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                # 移除引号
                value = value.strip('"').strip("'")
                info[key] = value
        return info
    
    @staticmethod
    def _detect_package_manager() -> str:
        """检测Linux包管理器"""
        managers = {
            'apt': 'apt',
            'apt-get': 'apt',
            'yum': 'yum',
            'dnf': 'dnf',
            'pacman': 'pacman',
            'zypper': 'zypper',
            'apk': 'apk'
        }
        
        for cmd, name in managers.items():
            if shutil.which(cmd):
                return name
        
        return "unknown"
    
    @staticmethod
    def _get_linux_distro_info() -> dict:
        """获取Linux发行版详细信息"""
        info = {}
        
        # 尝试读取 /etc/os-release
        os_release_content = ContextManager._read_file_safe('/etc/os-release')
        if os_release_content:
            parsed = ContextManager._parse_os_release(os_release_content)
            info['distro_name'] = parsed.get('NAME', 'Unknown')
            info['distro_id'] = parsed.get('ID', 'unknown')
            info['distro_version'] = parsed.get('VERSION_ID', 'unknown')
            info['distro_pretty_name'] = parsed.get('PRETTY_NAME', 'Unknown Linux')
        else:
            # 降级方案：尝试其他文件
            redhat_release = ContextManager._read_file_safe('/etc/redhat-release')
            if redhat_release:
                info['distro_pretty_name'] = redhat_release.strip()
            else:
                info['distro_pretty_name'] = 'Unknown Linux'
        
        return info
    
    @staticmethod
    def _get_powershell_version() -> str:
        """获取PowerShell版本"""
        version = ContextManager._run_command_safe('powershell -Command "$PSVersionTable.PSVersion.ToString()"')
        if not version:
            version = ContextManager._run_command_safe('pwsh -Command "$PSVersionTable.PSVersion.ToString()"')
        return version or "unknown"
    
    @staticmethod
    def _get_macos_release_name() -> str:
        """获取macOS版本名称"""
        version = platform.mac_ver()[0]
        if not version:
            return "Unknown"
        
        # 简单的版本映射
        major = int(version.split('.')[0])
        names = {
            14: "Sonoma",
            13: "Ventura",
            12: "Monterey",
            11: "Big Sur",
            10: "Catalina"
        }
        return names.get(major, f"macOS {version}")
```

#### 1.2 添加详细信息收集方法

```python
    @staticmethod
    def get_detailed_os_info() -> dict:
        """获取详细的操作系统信息（本地）"""
        os_type = platform.system()
        
        info = {
            "os_type": os_type,
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node()
        }
        
        if os_type == "Linux":
            # Linux详细信息
            distro_info = ContextManager._get_linux_distro_info()
            info.update(distro_info)
            info["kernel"] = platform.release()
            info["package_manager"] = ContextManager._detect_package_manager()
            
            # 检查sudo权限（非阻塞）
            has_sudo = ContextManager._run_command_safe('sudo -n true 2>/dev/null && echo "yes" || echo "no"')
            info["has_sudo"] = has_sudo == "yes"
            
        elif os_type == "Windows":
            info["windows_version"] = platform.version()
            info["windows_release"] = platform.release()
            info["powershell_version"] = ContextManager._get_powershell_version()
            
        elif os_type == "Darwin":
            info["macos_version"] = platform.mac_ver()[0]
            info["macos_release"] = ContextManager._get_macos_release_name()
            # 检查Homebrew
            info["has_homebrew"] = bool(shutil.which('brew'))
        
        return info
    
    @classmethod
    def get_enhanced_context_string(cls, detailed_info: dict = None) -> str:
        """获取增强的上下文字符串"""
        if detailed_info is None:
            detailed_info = cls.get_detailed_os_info()
        
        os_type = detailed_info.get("os_type", "Unknown")
        
        # 基础信息
        lines = []
        
        if os_type == "Linux":
            distro = detailed_info.get("distro_pretty_name", "Unknown Linux")
            kernel = detailed_info.get("kernel", "unknown")
            arch = detailed_info.get("architecture", "unknown")
            pkg_mgr = detailed_info.get("package_manager", "unknown")
            
            lines.append(f"- OS: {distro}")
            lines.append(f"- Architecture: {arch}")
            lines.append(f"- Kernel: {kernel}")
            lines.append(f"- Package Manager: {pkg_mgr}")
            lines.append(f"- Shell: {cls.get_shell_type()}")
            
            if detailed_info.get("has_sudo"):
                lines.append("- Sudo Access: Available")
            
        elif os_type == "Windows":
            win_ver = detailed_info.get("windows_release", "Unknown")
            ps_ver = detailed_info.get("powershell_version", "unknown")
            arch = detailed_info.get("architecture", "unknown")
            
            lines.append(f"- OS: Windows {win_ver}")
            lines.append(f"- Architecture: {arch}")
            lines.append(f"- PowerShell Version: {ps_ver}")
            lines.append(f"- Shell: {cls.get_shell_type()}")
            
        elif os_type == "Darwin":
            macos_release = detailed_info.get("macos_release", "Unknown")
            macos_ver = detailed_info.get("macos_version", "unknown")
            arch = detailed_info.get("architecture", "unknown")
            
            lines.append(f"- OS: macOS {macos_release} ({macos_ver})")
            lines.append(f"- Architecture: {arch}")
            lines.append(f"- Shell: {cls.get_shell_type()}")
            
            if detailed_info.get("has_homebrew"):
                lines.append("- Package Manager: Homebrew")
        
        # 通用信息
        lines.append(f"- Current Working Directory: {cls.get_cwd()}")
        lines.append(f"- User: {cls.get_user()}")
        lines.append(f"- Python Version: {detailed_info.get('python_version', 'unknown')}")
        
        return "\n".join(lines)
```

### 步骤2：创建SSH上下文管理器

创建新文件 `autoshell/ssh_context.py`：

```python
"""SSH模式下的远程系统信息收集"""

import re
from typing import Dict, Optional, Any
from rich.console import Console

console = Console()

# 尝试导入paramiko
try:
    import paramiko
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False
    paramiko = None


class SSHContextManager:
    """SSH模式下的远程系统信息收集"""
    
    @staticmethod
    def _execute_ssh_command(ssh_client, command: str, timeout: int = 5) -> str:
        """通过SSH执行命令并返回输出"""
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8').strip()
            return output
        except Exception as e:
            if Config.DEBUG:
                console.print(f"[dim][DEBUG] SSH command failed: {command} - {e}[/dim]")
            return ""
    
    @staticmethod
    def _parse_os_release(content: str) -> dict:
        """解析 /etc/os-release 文件内容"""
        info = {}
        for line in content.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                info[key] = value
        return info
    
    @staticmethod
    def get_remote_system_info(ssh_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        收集远程系统详细信息
        
        :param ssh_config: SSH配置字典
        :return: 系统信息字典
        """
        if not SSH_AVAILABLE:
            return {
                "os_type": "Linux",
                "distro_pretty_name": "Unknown Linux (SSH unavailable)",
                "error": "paramiko not installed"
            }
        
        # 默认信息
        default_info = {
            "os_type": "Linux",
            "distro_pretty_name": "Unknown Linux",
            "architecture": "x86_64",
            "kernel": "unknown",
            "package_manager": "unknown"
        }
        
        try:
            # 解析SSH配置
            host_str = ssh_config.get('host', '')
            if '@' in host_str:
                username, hostname = host_str.split('@', 1)
            else:
                username = None
                hostname = host_str
            
            port = ssh_config.get('port', 22)
            password = ssh_config.get('password')
            key_filename = ssh_config.get('key_filename')
            
            # 创建SSH客户端
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 连接参数
            connect_kwargs = {
                'hostname': hostname,
                'port': port,
                'timeout': 10
            }
            
            if username:
                connect_kwargs['username'] = username
            
            if key_filename:
                import os
                key_filename = os.path.expanduser(key_filename)
                connect_kwargs['key_filename'] = key_filename
            elif password:
                connect_kwargs['password'] = password
            
            # 连接
            client.connect(**connect_kwargs)
            
            # 收集信息
            info = {}
            
            # OS类型
            os_type = SSHContextManager._execute_ssh_command(client, "uname -s")
            info["os_type"] = os_type or "Linux"
            
            # 架构
            arch = SSHContextManager._execute_ssh_command(client, "uname -m")
            info["architecture"] = arch or "unknown"
            
            # 内核版本
            kernel = SSHContextManager._execute_ssh_command(client, "uname -r")
            info["kernel"] = kernel or "unknown"
            
            # 发行版信息
            os_release = SSHContextManager._execute_ssh_command(
                client,
                "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo 'Unknown'"
            )
            
            if os_release and os_release != "Unknown":
                if "=" in os_release:
                    # /etc/os-release 格式
                    parsed = SSHContextManager._parse_os_release(os_release)
                    info['distro_name'] = parsed.get('NAME', 'Unknown')
                    info['distro_id'] = parsed.get('ID', 'unknown')
                    info['distro_version'] = parsed.get('VERSION_ID', 'unknown')
                    info['distro_pretty_name'] = parsed.get('PRETTY_NAME', 'Unknown Linux')
                else:
                    # 简单格式（如 /etc/redhat-release）
                    info['distro_pretty_name'] = os_release
            else:
                info['distro_pretty_name'] = 'Unknown Linux'
            
            # 检测包管理器
            pkg_managers = ['apt', 'yum', 'dnf', 'pacman', 'zypper', 'apk']
            for mgr in pkg_managers:
                result = SSHContextManager._execute_ssh_command(client, f"which {mgr} 2>/dev/null")
                if result:
                    info['package_manager'] = mgr
                    break
            else:
                info['package_manager'] = 'unknown'
            
            # Shell类型
            shell = SSHContextManager._execute_ssh_command(client, "echo $SHELL")
            if shell:
                import os
                info['shell'] = os.path.basename(shell)
            else:
                info['shell'] = 'bash'
            
            # 用户名
            user = SSHContextManager._execute_ssh_command(client, "whoami")
            info['user'] = user or 'unknown'
            
            # Home目录
            home = SSHContextManager._execute_ssh_command(client, "echo $HOME")
            info['home'] = home or '~'
            
            # Python版本
            python_ver = SSHContextManager._execute_ssh_command(
                client,
                "python3 --version 2>&1 || python --version 2>&1 || echo 'Not installed'"
            )
            if python_ver and "Python" in python_ver:
                info['python_version'] = python_ver.replace("Python ", "").strip()
            else:
                info['python_version'] = 'not installed'
            
            # 检查sudo权限
            has_sudo = SSHContextManager._execute_ssh_command(
                client,
                "sudo -n true 2>/dev/null && echo 'yes' || echo 'no'"
            )
            info['has_sudo'] = has_sudo == 'yes'
            
            # 主机名
            hostname_full = SSHContextManager._execute_ssh_command(client, "hostname")
            info['hostname'] = hostname_full or hostname
            
            # 关闭连接
            client.close()
            
            return info
            
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to collect remote system info: {e}[/yellow]")
            return default_info
    
    @staticmethod
    def format_remote_context(info: Dict[str, Any]) -> str:
        """格式化远程系统信息为上下文字符串"""
        lines = []
        
        distro = info.get("distro_pretty_name", "Unknown Linux")
        kernel = info.get("kernel", "unknown")
        arch = info.get("architecture", "unknown")
        pkg_mgr = info.get("package_manager", "unknown")
        shell = info.get("shell", "bash")
        user = info.get("user", "unknown")
        hostname = info.get("hostname", "remote")
        
        lines.append(f"- Remote OS: {distro}")
        lines.append(f"- Architecture: {arch}")
        lines.append(f"- Kernel: {kernel}")
        lines.append(f"- Package Manager: {pkg_mgr}")
        lines.append(f"- Shell: {shell}")
        lines.append(f"- User: {user}@{hostname}")
        
        if info.get("has_sudo"):
            lines.append("- Sudo Access: Available")
        
        python_ver = info.get("python_version", "unknown")
        if python_ver != "not installed":
            lines.append(f"- Python Version: {python_ver}")
        
        return "\n".join(lines)
```

### 步骤3：修改Agent以使用增强的上下文

修改 [`autoshell/agent.py`](autoshell/agent.py)：

#### 3.1 导入新模块

```python
from .ssh_context import SSHContextManager
import time
```

#### 3.2 修改初始化方法

```python
class AutoShellAgent:
    def __init__(self, ssh_config=None):
        """
        初始化AutoShell Agent
        
        :param ssh_config: SSH配置字典，包含host, port, password, key_filename等
        """
        self.llm = LLMClient()
        self.max_retries = Config.MAX_RETRIES
        self.ssh_config = ssh_config
        
        # 系统信息缓存
        self._system_info_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5分钟缓存
        
        # 初始化时收集系统信息
        if Config.COLLECT_DETAILED_INFO:
            self._initialize_system_info()
    
    def _initialize_system_info(self):
        """初始化系统信息"""
        try:
            if self.ssh_config:
                # SSH模式：收集远程信息
                from rich.status import Status
                with console.status("[bold green]Collecting remote system info...[/bold green]", spinner="dots"):
                    self._system_info_cache = SSHContextManager.get_remote_system_info(self.ssh_config)
            else:
                # 本地模式：收集本地信息
                self._system_info_cache = ContextManager.get_detailed_os_info()
            
            self._cache_timestamp = time.time()
            
            if Config.DEBUG:
                console.print(f"[dim][DEBUG] System info collected: {self._system_info_cache}[/dim]")
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
```

#### 3.3 修改run方法

```python
    def run(self, user_query: str):
        """
        处理单个用户请求的完整生命周期：
        Context -> LLM (Plan) -> Loop (Execute Steps) -> (Retry Step if fail) -> Output
        """
        error_history = []
        
        # 维护当前 Session 的 CWD
        if self.ssh_config:
            session_cwd = None
        else:
            session_cwd = os.getcwd()

        # 1. Generate Plan (Context Aware)
        # 使用增强的上下文信息
        system_info = self._get_system_info()
        
        if self.ssh_config:
            # SSH模式：使用远程系统信息
            context_str = SSHContextManager.format_remote_context(system_info)
        else:
            # 本地模式：使用本地系统信息
            context_str = ContextManager.get_enhanced_context_string(system_info)
        
        context_str += f"\n- Virtual Session CWD: {session_cwd}"
        
        # 其余代码保持不变...
```

#### 3.4 同样修改run_adaptive方法

```python
    def run_adaptive(self, user_query: str):
        """自适应执行模式：渐进式生成和执行步骤，根据输出动态调整"""
        # ... 前面的代码 ...
        
        # 获取上下文 - 使用增强的上下文信息
        system_info = self._get_system_info()
        
        if self.ssh_config:
            context_str = SSHContextManager.format_remote_context(system_info)
        else:
            context_str = ContextManager.get_enhanced_context_string(system_info)
        
        if self.ssh_config:
            session_cwd = None
        else:
            session_cwd = os.getcwd()
        context_str += f"\n- Virtual Session CWD: {session_cwd}"
        
        # 其余代码保持不变...
```

### 步骤4：更新LLM Prompt

修改 [`autoshell/llm.py`](autoshell/llm.py) 中的 [`generate_plan()`](autoshell/llm.py:99) 方法：

```python
    def generate_plan(self, user_query: str, context_str: str, error_history: list | None = None) -> dict:
        """
        根据用户查询和环境上下文生成 Shell 命令计划。
        """
        
        # ... 前面的代码保持不变 ...
        
        system_prompt = f"""
You are an expert system engineer and command-line wizard.
Your goal is to translate natural language instructions into a SERIES of precise, efficient, and safe Shell commands.

Current Execution Environment:
{context_str}

⚠️ IMPORTANT: Pay special attention to the system information above!
- For Ubuntu/Debian systems (apt): use apt or apt-get commands
- For CentOS/RHEL systems (yum/dnf): use yum (CentOS 7) or dnf (CentOS 8+)
- For Arch Linux (pacman): use pacman commands
- For Alpine Linux (apk): use apk commands
- Adjust command syntax and options based on the specific OS version and kernel
- Consider the system architecture (x86_64/aarch64/armv7l) when suggesting installations
- If sudo access is available, use it when necessary for system operations
- Respect the package manager indicated in the environment

⚠️ CRITICAL JSON FORMAT REQUIREMENTS ⚠️

YOU MUST RESPOND WITH **ONLY** A VALID JSON OBJECT IN THIS **EXACT** FORMAT:

{{
   "thought": "Brief explanation of the plan",
   "steps": [
      {{
         "description": "Step description",
         "command": "shell command"
      }}
   ]
}}

🚫 FORBIDDEN:
- NO text before or after the JSON
- NO markdown code blocks (no ```)
- NO explanations outside the JSON
- NO conversational text
- NO other JSON structures (like {{"type":"shell"}} or {{"args":[]}})

✅ REQUIRED FIELDS:
- "thought": string - Your reasoning (required)
- "steps": array - List of command steps (required, must have at least 1 step)
  - Each step MUST have:
    - "description": string - What this step does
    - "command": string - The shell command to execute

📋 EXAMPLES:

Example 1 - Simple command "show current directory":
{{
   "thought": "Execute pwd command to show current working directory",
   "steps": [
      {{
         "description": "Display current directory",
         "command": "pwd"
      }}
   ]
}}

Example 2 - Package installation on Ubuntu:
{{
   "thought": "Install nginx using apt package manager on Ubuntu system",
   "steps": [
      {{
         "description": "Update package lists",
         "command": "sudo apt update"
      }},
      {{
         "description": "Install nginx",
         "command": "sudo apt install -y nginx"
      }}
   ]
}}

Example 3 - Package installation on CentOS 8:
{{
   "thought": "Install nginx using dnf package manager on CentOS 8 system",
   "steps": [
      {{
         "description": "Install nginx",
         "command": "sudo dnf install -y nginx"
      }}
   ]
}}

🔧 EXECUTION RULES:
1. Analyze the user's request based on the current OS, distribution, and version
2. Break down the task into sequential logical steps
3. For each step, formulate a valid shell command for the detected OS and package manager
4. Use the correct package manager (apt/yum/dnf/pacman/apk) based on the system info
5. Use Windows commands (like 'dir', 'cd') for Windows/PowerShell
6. Use Unix commands (like 'ls', 'pwd') for Unix/Linux/Mac
7. 'cd' commands will be handled specially by the execution engine
8. Consider system architecture when suggesting binary installations

⚠️ REMEMBER: Output ONLY the JSON object - absolutely nothing else!
"""

        # 其余代码保持不变...
```

同样更新 [`generate_next_steps()`](autoshell/llm.py:323) 方法的system prompt。

### 步骤5：更新配置文件

修改 [`autoshell/config.py`](autoshell/config.py)：

```python
class Config:
    DEBUG = False
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-needed")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # 新增配置
    COLLECT_DETAILED_INFO = os.getenv("COLLECT_DETAILED_INFO", "true").lower() == "true"
    SYSTEM_INFO_CACHE_TTL = int(os.getenv("SYSTEM_INFO_CACHE_TTL", "300"))  # 秒
    SSH_INFO_TIMEOUT = int(os.getenv("SSH_INFO_TIMEOUT", "10"))  # 秒
    
    # ... 其余代码保持不变 ...
```

### 步骤6：更新.env.example

在 `.env.example` 中添加新的配置项：

```bash
# 现有配置...

# 系统信息收集配置
COLLECT_DETAILED_INFO=true
SYSTEM_INFO_CACHE_TTL=300
SSH_INFO_TIMEOUT=10
```

### 步骤7：更新main.py显示信息

修改 [`main.py`](main.py) 中的系统信息显示：

```python
def main():
    try:
        args = parse_args()
        
        # 设置全局DEBUG标志
        Config.DEBUG = args.debug
        
        # ... SSH配置代码 ...
        
        agent = AutoShellAgent(ssh_config=ssh_config)
        
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
        
        # ... 其余代码保持不变 ...
```

## 测试建议

### 单元测试

创建 `tests/test_context.py`：

```python
import unittest
from autoshell.context import ContextManager

class TestContextManager(unittest.TestCase):
    def test_get_detailed_os_info(self):
        """测试详细信息收集"""
        info = ContextManager.get_detailed_os_info()
        self.assertIn('os_type', info)
        self.assertIn('architecture', info)
    
    def test_enhanced_context_string(self):
        """测试增强的上下文字符串"""
        context_str = ContextManager.get_enhanced_context_string()
        self.assertIsInstance(context_str, str)
        self.assertIn('OS:', context_str)
```

### 集成测试

1. **本地Linux测试**：
   ```bash
   python main.py -c "安装nginx"
   # 验证是否使用了正确的包管理器
   ```

2. **SSH远程测试**：
   ```bash
   python main.py --ssh-host user@server --ssh-key ~/.ssh/id_rsa -c "检查系统信息"
   # 验证是否正确收集了远程系统信息
   ```

3. **调试模式测试**：
   ```bash
   python main.py --debug -c "列出文件"
   # 查看详细的系统信息收集过程
   ```

## 注意事项

1. **错误处理**：所有信息收集函数都应该有适当的错误处理，避免因为某个信息收集失败而导致整个程序崩溃

2. **性能**：SSH模式下的信息收集可能需要1-2秒，应该在初始化时完成，并使用缓存

3. **兼容性**：确保在不同Linux发行版上都能正常工作，提供降级方案

4. **安全性**：不要在日志中输出敏感信息（如SSH密码）

5. **用户体验**：信息收集过程应该有适当的提示，让用户知道程序在做什么

## 完成标准

- [ ] 本地Linux系统能够正确识别发行版和包管理器
- [ ] SSH模式能够正确收集远程服务器信息
- [ ] LLM能够根据系统信息生成正确的命令
- [ ] 缓存机制正常工作
- [ ] 错误处理完善，不会因信息收集失败而崩溃
- [ ] 文档更新完整
- [ ] 通过所有测试用例
