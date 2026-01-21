# AutoShell SSH 远程执行快速参考

## 快速开始

### 本地模式（默认）

```bash
# .env 配置
EXECUTION_MODE=local

# 运行
python main.py
```

### SSH 远程模式

```bash
# .env 配置
EXECUTION_MODE=ssh
SSH_HOST=192.168.1.100
SSH_USERNAME=admin
SSH_KEY_PATH=C:/Users/YourName/.ssh/id_rsa

# 运行
python main.py
```

## 核心架构

```
CommandExecutor (抽象基类)
    ├── LocalCommandExecutor (本地执行)
    └── SSHCommandExecutor (SSH 远程执行)
```

## 关键文件

| 文件路径 | 说明 |
|---------|------|
| `autoshell/executors/base.py` | 执行器抽象基类 |
| `autoshell/executors/local.py` | 本地执行器实现 |
| `autoshell/executors/ssh.py` | SSH 执行器实现 |
| `autoshell/config.py` | 配置管理（含 SSH 配置） |
| `autoshell/agent.py` | 主控制流（执行器选择） |

## 配置参数

### LLM 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | 必填 |
| `OPENAI_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-3.5-turbo` |
| `MAX_RETRIES` | 最大重试次数 | `3` |

### 执行模式配置

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `EXECUTION_MODE` | 执行模式 | `local`, `ssh` |

### SSH 配置

| 参数 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `SSH_HOST` | SSH 服务器地址 | - | 是（SSH 模式） |
| `SSH_PORT` | SSH 端口 | `22` | 否 |
| `SSH_USERNAME` | SSH 用户名 | - | 是（SSH 模式） |
| `SSH_PASSWORD` | SSH 密码 | - | 否* |
| `SSH_KEY_PATH` | SSH 私钥路径 | - | 否* |
| `SSH_TIMEOUT` | 连接超时（秒） | `30` | 否 |

*注：`SSH_PASSWORD` 和 `SSH_KEY_PATH` 至少需要提供一个，优先使用密钥认证。

## 执行器接口

### CommandExecutor 抽象方法

```python
class CommandExecutor(ABC):
    @abstractmethod
    def execute(self, command: str, cwd: str = None, 
                description: str = None) -> Dict:
        """执行命令并返回结果"""
        pass
    
    @abstractmethod
    def is_safe(self, command: str) -> bool:
        """检查命令是否安全"""
        pass
    
    @abstractmethod
    def close(self):
        """清理资源"""
        pass
    
    @abstractmethod
    def get_context(self) -> Dict:
        """获取执行环境上下文"""
        pass
```

### 返回值格式

```python
{
    "return_code": int,    # 退出码（0 表示成功）
    "stdout": str,         # 标准输出
    "stderr": str,         # 标准错误
    "executed": bool       # 是否已执行（False 表示用户取消）
}
```

### 上下文格式

```python
{
    "os": str,              # 操作系统（Windows/Linux/Darwin）
    "shell": str,           # Shell 类型（cmd/powershell/bash/zsh）
    "cwd": str,             # 当前工作目录
    "user": str,            # 用户名
    "execution_mode": str,  # 执行模式（local/ssh）
    "remote_host": str      # 远程主机（仅 SSH 模式）
}
```

## 白名单命令

### 本地执行器

```python
WHITELIST = {
    "ls", "dir", "pwd", "echo", "date", "whoami", "hostname", 
    "uname", "cd", "mkdir", "touch", "cat", "type", "cp", 
    "mv", "rm", "grep", "find", "head", "tail"
}
```

### SSH 执行器

```python
WHITELIST = {
    "ls", "pwd", "echo", "date", "whoami", "hostname", "uname", 
    "cd", "mkdir", "touch", "cat", "cp", "mv", "rm", "grep", 
    "find", "head", "tail", "chmod", "chown"
}
```

## SSH 认证方式

### 密钥认证（推荐）

```bash
# 生成密钥对
ssh-keygen -t rsa -b 4096 -f ~/.ssh/autoshell_key

# 复制公钥到远程服务器
ssh-copy-id -i ~/.ssh/autoshell_key.pub user@remote_host

# .env 配置
SSH_KEY_PATH=C:/Users/YourName/.ssh/autoshell_key
```

### 密码认证

```bash
# .env 配置
SSH_PASSWORD=your_password
```

## 使用示例

### 示例 1：远程文件操作

```
AutoShell > create a directory called projects
AutoShell > navigate into projects
AutoShell > create three files: app.py, config.py, and readme.md
AutoShell > list all files with details
```

**执行流程**：
1. 在远程服务器创建 `projects` 目录
2. 更新会话 CWD 为 `~/projects`
3. 在 `~/projects` 中创建三个文件
4. 列出 `~/projects` 目录内容

### 示例 2：系统信息查询

```
AutoShell > show me system information including OS version, hostname, and current user
```

**执行流程**：
1. LLM 生成命令计划（如 `uname -a`, `hostname`, `whoami`）
2. 在远程服务器依次执行
3. 汇总输出并显示

### 示例 3：跨目录操作

```
AutoShell > create a backup directory in home, copy all .py files from current directory to backup
```

**执行流程**：
1. 在 `~` 创建 `backup` 目录
2. 使用 `cp` 命令复制文件
3. 保持当前会话 CWD 不变

## 路径处理

### 本地模式（Windows）

```python
# 使用 os.path 处理路径
new_cwd = os.path.abspath(os.path.join(session_cwd, target_dir))

# 示例
session_cwd = "C:\\Users\\Admin"
target_dir = "Documents"
new_cwd = "C:\\Users\\Admin\\Documents"
```

### SSH 模式（Linux）

```python
# 使用 POSIX 路径规范
if not target_dir.startswith('/'):
    new_cwd = f"{session_cwd}/{target_dir}"
else:
    new_cwd = target_dir

# 示例
session_cwd = "/home/admin"
target_dir = "projects"
new_cwd = "/home/admin/projects"
```

## 错误处理

### 连接错误

```python
try:
    executor = SSHCommandExecutor(...)
except ConnectionError as e:
    print(f"Failed to connect: {e}")
    # 检查网络、SSH 服务、认证信息
```

### 执行错误

```python
result = executor.execute(command)
if result["return_code"] != 0:
    print(f"Command failed: {result['stderr']}")
    # 触发 LLM 自愈机制
```

### 用户取消

```python
result = executor.execute(command)
if not result["executed"]:
    print("User aborted execution")
    # 停止当前任务
```

## 性能优化

### 连接复用

SSH 执行器在整个会话期间保持连接：

```python
# 初始化时建立连接
executor = SSHCommandExecutor(...)

# 多次执行命令，复用连接
executor.execute("ls")
executor.execute("pwd")
executor.execute("whoami")

# 清理时关闭连接
executor.close()
```

### 连接健康检查

```python
if not self.client.get_transport().is_active():
    console.print("[yellow]Reconnecting...[/yellow]")
    self._connect()
```

## 安全最佳实践

### 1. 使用密钥认证

```bash
# 生成强密钥
ssh-keygen -t rsa -b 4096

# 设置正确的权限
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### 2. 限制 SSH 用户权限

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash autoshell

# 限制 sudo 权限
# 在 /etc/sudoers.d/autoshell 中配置
```

### 3. 配置防火墙

```bash
# 仅允许特定 IP 访问 SSH
sudo ufw allow from 192.168.1.0/24 to any port 22
```

### 4. 启用命令审计

```python
# 记录所有执行的命令
import logging

logging.info(f"Executing: {command} on {self.host}")
```

### 5. 定期轮换密钥

```bash
# 每 90 天更新 SSH 密钥
ssh-keygen -t rsa -b 4096 -f ~/.ssh/autoshell_key_new
ssh-copy-id -i ~/.ssh/autoshell_key_new.pub user@host
# 更新 .env 配置
```

## 故障排查清单

### SSH 连接失败

- [ ] 检查网络连通性：`ping remote_host`
- [ ] 验证 SSH 服务：`ssh user@remote_host`
- [ ] 检查防火墙规则
- [ ] 验证认证信息（密钥/密码）
- [ ] 检查密钥权限：`ls -l ~/.ssh/id_rsa`

### 输出乱码

- [ ] 确认使用 UTF-8 编码
- [ ] 检查 `_clean_terminal_output()` 方法
- [ ] 验证 ANSI 转义序列清理

### 命令执行失败

- [ ] 检查命令语法（本地 vs 远程）
- [ ] 验证工作目录是否存在
- [ ] 检查文件/目录权限
- [ ] 查看详细错误信息

### 会话状态异常

- [ ] 验证 `session_cwd` 更新逻辑
- [ ] 检查路径拼接（本地 vs 远程）
- [ ] 添加调试日志

## 依赖版本

```
openai>=1.0.0
rich>=13.0.0
python-dotenv>=1.0.0
paramiko>=3.0.0
```

## 相关文档

- [完整设计文档](ssh-remote-execution-design.md)
- [实施指南](implementation-guide.md)
- [原始架构文档](architecture.md)

## 常见问题

### Q: 可以同时连接多个服务器吗？

A: 当前版本每次只支持一个执行器。要支持多服务器，需要扩展 Agent 类以管理多个执行器实例。

### Q: 如何切换执行模式？

A: 修改 `.env` 文件中的 `EXECUTION_MODE` 参数，然后重启 AutoShell。

### Q: SSH 密钥和密码可以同时配置吗？

A: 可以。系统会优先尝试密钥认证，失败后回退到密码认证。

### Q: 如何处理需要 sudo 的命令？

A: 当前白名单不包含 `sudo`。如需执行，会触发用户确认。建议配置免密 sudo 或使用具有足够权限的用户。

### Q: 支持 SSH 跳板机吗？

A: 当前版本不支持。可以通过配置 SSH 配置文件（`~/.ssh/config`）实现 ProxyJump。

### Q: 如何查看执行日志？

A: 当前版本输出到控制台。可以扩展添加文件日志记录功能。

## 版本历史

- **v1.1.0** (计划中)
  - 添加 SSH 远程执行支持
  - 实现执行器抽象层
  - 支持密钥和密码认证
  - 跨平台路径处理

- **v1.0.0** (当前)
  - 基础本地命令执行
  - LLM 智能规划
  - 自愈机制
  - 安全白名单

## 贡献指南

如需扩展或改进 SSH 功能，请参考：

1. 遵循现有的执行器接口设计
2. 添加相应的单元测试
3. 更新相关文档
4. 提交 Pull Request

## 许可证

与 AutoShell 主项目保持一致。
