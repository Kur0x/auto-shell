# AutoShell SSH 远程执行功能实施指南

## 概述

本文档提供了实施 SSH 远程执行功能的详细步骤指南，包括代码修改、测试验证和部署建议。

## 实施步骤

### 步骤 1：创建执行器模块结构

创建新的执行器模块目录和基础文件：

```bash
mkdir autoshell/executors
touch autoshell/executors/__init__.py
touch autoshell/executors/base.py
touch autoshell/executors/local.py
touch autoshell/executors/ssh.py
```

### 步骤 2：实现抽象基类

在 `autoshell/executors/base.py` 中定义 `CommandExecutor` 抽象基类。

**关键点**：
- 使用 `abc.ABC` 和 `@abstractmethod` 装饰器
- 定义统一的 `execute()` 方法签名
- 包含 `is_safe()`, `close()`, `get_context()` 抽象方法

**参考**：详见 [`ssh-remote-execution-design.md`](plans/ssh-remote-execution-design.md:30) 第 2.1 节

### 步骤 3：重构本地执行器

将现有的 [`CommandExecutor`](autoshell/executor.py:11) 类重构为 `LocalCommandExecutor`：

1. 继承自 `CommandExecutor` 基类
2. 保留现有的白名单和安全检查逻辑
3. 实现 `get_context()` 方法返回本地环境信息
4. 添加 `close()` 方法（空实现）

**迁移清单**：
- ✓ 白名单常量 `WHITELIST`
- ✓ `is_safe()` 方法
- ✓ `execute()` 方法（包含用户确认逻辑）
- ✓ 新增 `get_context()` 方法
- ✓ 新增 `close()` 方法

### 步骤 4：实现 SSH 执行器

在 `autoshell/executors/ssh.py` 中实现 `SSHCommandExecutor` 类：

**核心功能**：

1. **连接管理**
   ```python
   def _connect(self):
       self.client = paramiko.SSHClient()
       self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
       # 优先使用密钥认证
       # 建立连接
   ```

2. **环境检测**
   ```python
   def _detect_remote_environment(self):
       # 检测 OS: uname -s
       # 检测 Shell: echo $SHELL
       # 获取 CWD: pwd
   ```

3. **命令执行**
   ```python
   def execute(self, command, cwd=None, description=None):
       # 构建完整命令（包含 cd）
       # 执行并捕获输出
       # 清理终端控制字符
       # 返回标准化结果
   ```

4. **输出清理**
   ```python
   def _clean_terminal_output(self, output):
       # 移除 ANSI 转义序列
       # 处理特殊字符
   ```

**注意事项**：
- 使用 `get_pty=True` 以支持交互式命令
- 实现连接健康检查和自动重连
- 正确处理 UTF-8 编码和解码错误

### 步骤 5：扩展配置类

修改 [`autoshell/config.py`](autoshell/config.py:7)：

**新增配置项**：
```python
# 执行模式
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "local")

# SSH 配置
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
SSH_TIMEOUT = int(os.getenv("SSH_TIMEOUT", "30"))
```

**增强验证逻辑**：
```python
@staticmethod
def validate():
    # 验证 LLM 配置
    if not Config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required")
    
    # 验证 SSH 配置（当启用 SSH 模式时）
    if Config.EXECUTION_MODE == "ssh":
        if not Config.SSH_HOST:
            raise ValueError("SSH_HOST is required")
        # ... 其他验证
```

**新增辅助方法**：
```python
@staticmethod
def is_ssh_mode() -> bool:
    return Config.EXECUTION_MODE.lower() == "ssh"
```

### 步骤 6：修改 Agent 类

更新 [`autoshell/agent.py`](autoshell/agent.py:15) 以集成执行器：

**关键修改**：

1. **导入执行器**
   ```python
   from .executors.local import LocalCommandExecutor
   from .executors.ssh import SSHCommandExecutor
   ```

2. **初始化执行器**
   ```python
   def __init__(self):
       self.llm = LLMClient()
       self.max_retries = Config.MAX_RETRIES
       
       # 根据配置选择执行器
       if Config.is_ssh_mode():
           self.executor = SSHCommandExecutor(
               host=Config.SSH_HOST,
               port=Config.SSH_PORT,
               username=Config.SSH_USERNAME,
               password=Config.SSH_PASSWORD,
               key_path=Config.SSH_KEY_PATH,
               timeout=Config.SSH_TIMEOUT
           )
       else:
           self.executor = LocalCommandExecutor()
       
       self.execution_context = self.executor.get_context()
   ```

3. **资源清理**
   ```python
   def __del__(self):
       if hasattr(self, 'executor'):
           self.executor.close()
   ```

4. **更新上下文构建**
   ```python
   def _build_context_string(self) -> str:
       ctx = self.execution_context
       context_parts = [
           f"- OS: {ctx['os']}",
           f"- Shell: {ctx['shell']}",
           f"- Current Working Directory: {ctx['cwd']}",
           f"- User: {ctx['user']}",
           f"- Execution Mode: {ctx['execution_mode']}"
       ]
       
       if ctx['execution_mode'] == 'ssh':
           context_parts.append(f"- Remote Host: {ctx['remote_host']}")
       
       return "\n".join(context_parts)
   ```

5. **替换执行调用**
   
   将所有 `CommandExecutor.execute()` 调用替换为 `self.executor.execute()`：
   
   ```python
   # 原代码（第 101 行）
   result = CommandExecutor.execute(command, cwd=session_cwd, description=description)
   
   # 修改为
   result = self.executor.execute(command, cwd=session_cwd, description=description)
   ```

6. **处理 cd 命令的路径差异**
   
   在处理 `cd` 命令时，需要区分本地和远程路径：
   
   ```python
   if tokens and tokens[0] == "cd":
       target_dir = tokens[1] if len(tokens) > 1 else "~"
       
       # 根据执行器类型处理路径
       if isinstance(self.executor, SSHCommandExecutor):
           # SSH 模式：POSIX 路径
           if target_dir == "~":
               target_dir = f"/home/{self.executor.username}"
           
           if not target_dir.startswith('/'):
               new_cwd = f"{session_cwd}/{target_dir}"
           else:
               new_cwd = target_dir
           
           # 验证远程目录
           check_cmd = f"test -d {new_cwd} && echo 'exists'"
           # ... 执行验证
       else:
           # 本地模式：使用 os.path
           if target_dir == "~":
               target_dir = os.path.expanduser("~")
           new_cwd = os.path.abspath(os.path.join(session_cwd, target_dir))
           
           if os.path.isdir(new_cwd):
               session_cwd = new_cwd
               # ...
   ```

### 步骤 7：更新依赖文件

**修改 `requirements.txt`**：
```
openai>=1.0.0
rich>=13.0.0
python-dotenv>=1.0.0
paramiko>=3.0.0
```

**修改 `.env.example`**：
```bash
# LLM Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
MAX_RETRIES=3

# Execution Mode: "local" or "ssh"
EXECUTION_MODE=local

# SSH Configuration (required when EXECUTION_MODE=ssh)
# SSH_HOST=192.168.1.100
# SSH_PORT=22
# SSH_USERNAME=your_username
# SSH_PASSWORD=your_password
# SSH_KEY_PATH=C:/Users/YourName/.ssh/id_rsa
# SSH_TIMEOUT=30
```

### 步骤 8：更新主架构文档

在 [`plans/architecture.md`](plans/architecture.md:1) 中添加新的章节：

**新增内容**：

```markdown
## 5. 远程执行支持 (SSH)

### 5.1 执行器抽象
AutoShell 支持本地和远程（SSH）两种执行模式，通过 `CommandExecutor` 接口实现统一抽象。

### 5.2 执行器类型
- **LocalCommandExecutor**: 在本地 Shell 中执行命令
- **SSHCommandExecutor**: 通过 SSH 在远程服务器执行命令

### 5.3 配置切换
通过环境变量 `EXECUTION_MODE` 切换执行模式：
- `local`: 本地执行（默认）
- `ssh`: 远程 SSH 执行

### 5.4 SSH 特性
- 支持密钥和密码认证（优先密钥）
- 自动检测远程环境（OS、Shell、CWD）
- 实时输出流式传输
- 连接健康检查和自动重连
- 跨平台路径和字符编码处理

详细设计参见：[SSH 远程执行设计文档](ssh-remote-execution-design.md)
```

### 步骤 9：创建执行器模块的 __init__.py

在 `autoshell/executors/__init__.py` 中导出执行器类：

```python
"""
AutoShell 命令执行器模块

提供本地和远程（SSH）命令执行能力
"""

from .base import CommandExecutor
from .local import LocalCommandExecutor
from .ssh import SSHCommandExecutor

__all__ = [
    'CommandExecutor',
    'LocalCommandExecutor',
    'SSHCommandExecutor'
]
```

### 步骤 10：更新主模块的 __init__.py

在 `autoshell/__init__.py` 中添加执行器导出：

```python
"""AutoShell - Intelligent Command Line Assistant"""

from .agent import AutoShellAgent
from .config import Config
from .context import ContextManager
from .llm import LLMClient
from .executors import CommandExecutor, LocalCommandExecutor, SSHCommandExecutor

__version__ = "1.1.0"

__all__ = [
    'AutoShellAgent',
    'Config',
    'ContextManager',
    'LLMClient',
    'CommandExecutor',
    'LocalCommandExecutor',
    'SSHCommandExecutor'
]
```

## 测试计划

### 测试 1：本地模式验证

**目的**：确保重构后本地执行功能正常

**步骤**：
1. 设置 `.env` 文件：`EXECUTION_MODE=local`
2. 运行 `python main.py`
3. 测试命令：
   ```
   AutoShell > create a directory called test_local
   AutoShell > list files in current directory
   AutoShell > remove the test_local directory
   ```

**预期结果**：所有命令正常执行，输出与之前版本一致

### 测试 2：SSH 连接建立

**目的**：验证 SSH 连接和环境检测

**前置条件**：
- 准备一台可访问的 Linux 服务器
- 配置 SSH 密钥或密码

**步骤**：
1. 配置 `.env` 文件：
   ```
   EXECUTION_MODE=ssh
   SSH_HOST=your_server_ip
   SSH_USERNAME=your_username
   SSH_KEY_PATH=path/to/your/key
   ```
2. 运行 `python main.py`
3. 观察启动输出

**预期结果**：
- 显示 "SSH connected to user@host:port"
- 显示远程环境信息："Remote: Linux | bash | /home/user"

### 测试 3：远程命令执行

**目的**：验证远程命令执行和输出捕获

**步骤**：
1. 在 SSH 模式下运行
2. 测试命令：
   ```
   AutoShell > show me the current directory
   AutoShell > list all files
   AutoShell > check system information with uname -a
   ```

**预期结果**：
- 显示远程服务器的目录和文件
- 正确显示系统信息
- 输出无乱码或控制字符

### 测试 4：跨目录操作

**目的**：验证会话状态管理（cd 命令）

**步骤**：
```
AutoShell > create a directory called test_ssh
AutoShell > navigate into test_ssh
AutoShell > create a file named hello.txt
AutoShell > show the current directory path
AutoShell > go back to parent directory
AutoShell > remove test_ssh directory
```

**预期结果**：
- 所有操作在正确的目录上下文中执行
- `cd` 命令正确更新会话工作目录

### 测试 5：错误处理和自愈

**目的**：验证远程执行的错误处理

**步骤**：
```
AutoShell > navigate to /nonexistent/directory
```

**预期结果**：
- 显示错误信息
- LLM 尝试修复（如果启用自愈）
- 不会导致程序崩溃

### 测试 6：白名单和安全检查

**目的**：验证远程执行的安全机制

**步骤**：
```
AutoShell > run a dangerous command like rm -rf /
```

**预期结果**：
- 显示安全警告
- 要求用户确认
- 用户拒绝后不执行

### 测试 7：连接断开和重连

**目的**：验证连接健康检查

**步骤**：
1. 建立 SSH 连接
2. 在服务器端手动断开连接（或等待超时）
3. 尝试执行新命令

**预期结果**：
- 检测到连接断开
- 自动重新连接
- 命令正常执行

### 测试 8：长时间运行命令

**目的**：验证输出捕获的完整性

**步骤**：
```
AutoShell > run a command that takes time, like sleep 5 && echo done
```

**预期结果**：
- 等待命令完成
- 正确显示输出
- 返回正确的退出码

## 部署建议

### 开发环境

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件
   ```

3. **测试本地模式**
   ```bash
   python main.py
   ```

4. **配置 SSH 并测试**
   - 生成 SSH 密钥（如果没有）：
     ```bash
     ssh-keygen -t rsa -b 4096
     ```
   - 将公钥复制到远程服务器：
     ```bash
     ssh-copy-id user@remote_host
     ```
   - 更新 `.env` 配置
   - 测试连接

### 生产环境

1. **安全配置**
   - 使用密钥认证，避免密码
   - 限制 SSH 用户权限
   - 配置防火墙规则

2. **日志记录**
   - 添加命令执行日志
   - 记录 SSH 连接事件
   - 监控异常和错误

3. **性能优化**
   - 启用 SSH 连接复用
   - 配置合理的超时时间
   - 考虑连接池实现

4. **监控告警**
   - 监控 SSH 连接状态
   - 跟踪命令执行时间
   - 设置异常告警

## 故障排查

### 问题 1：SSH 连接失败

**症状**：`ConnectionError: Failed to connect to SSH server`

**可能原因**：
- 网络不可达
- SSH 服务未启动
- 防火墙阻止
- 认证失败

**解决方法**：
1. 测试网络连通性：`ping remote_host`
2. 检查 SSH 服务：`ssh user@remote_host`
3. 验证密钥权限：`chmod 600 ~/.ssh/id_rsa`
4. 检查防火墙规则

### 问题 2：输出乱码

**症状**：远程命令输出包含乱码或控制字符

**可能原因**：
- 字符编码不匹配
- PTY 控制字符未清理

**解决方法**：
1. 检查 `_clean_terminal_output()` 方法
2. 确保使用 UTF-8 编码
3. 调整 ANSI 转义序列清理正则表达式

### 问题 3：cd 命令不生效

**症状**：切换目录后，后续命令仍在原目录执行

**可能原因**：
- 会话状态未正确更新
- 路径计算错误

**解决方法**：
1. 检查 `session_cwd` 更新逻辑
2. 验证路径拼接（本地 vs 远程）
3. 添加调试日志输出当前 CWD

### 问题 4：命令执行超时

**症状**：长时间运行的命令被中断

**可能原因**：
- SSH 超时设置过短
- 网络不稳定

**解决方法**：
1. 增加 `SSH_TIMEOUT` 配置
2. 实现命令执行超时参数
3. 添加心跳保持机制

## 后续增强

### 短期（1-2 周）

- [ ] 添加详细的日志记录
- [ ] 实现命令执行历史
- [ ] 支持命令执行超时配置
- [ ] 添加单元测试

### 中期（1-2 月）

- [ ] 实现 SFTP 文件传输
- [ ] 支持多服务器管理
- [ ] 添加性能监控
- [ ] 实现连接池

### 长期（3-6 月）

- [ ] 支持 SSH 隧道和端口转发
- [ ] 实现分布式命令执行
- [ ] 添加 Web 管理界面
- [ ] 支持命令录制和回放

## 参考资料

- [Paramiko 官方文档](http://docs.paramiko.org/)
- [SSH 协议规范](https://www.openssh.com/specs.html)
- [Python subprocess 模块](https://docs.python.org/3/library/subprocess.html)
- [Rich 库文档](https://rich.readthedocs.io/)

## 总结

本实施指南提供了完整的步骤来为 AutoShell 添加 SSH 远程执行功能。关键要点：

1. **模块化设计**：通过抽象基类实现执行器的统一接口
2. **配置驱动**：使用环境变量灵活切换执行模式
3. **安全优先**：保持白名单机制和用户确认流程
4. **跨平台兼容**：正确处理路径和字符编码差异
5. **健壮性**：实现连接管理和错误处理

按照本指南逐步实施，可以确保功能的正确性和稳定性。
