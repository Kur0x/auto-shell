# OS信息增强功能说明

## 概述

AutoShell现在支持收集详细的操作系统信息，包括发行版、版本、包管理器等，使LLM能够生成更准确、更适合目标环境的命令。

## 功能特性

### 1. 本地模式增强

在本地模式下，AutoShell会自动收集以下信息：

#### Linux系统
- **发行版信息**：Ubuntu、CentOS、Debian、Fedora、Arch等
- **发行版版本**：20.04、22.04、7、8等
- **内核版本**：5.15.0-xxx
- **系统架构**：x86_64、aarch64、armv7l等
- **包管理器**：apt、yum、dnf、pacman、zypper、apk
- **Sudo权限**：是否有sudo访问权限
- **Python版本**：系统Python版本

#### Windows系统
- **Windows版本**：Windows 10、11、Server等
- **系统架构**：x64、x86、ARM64
- **PowerShell版本**：5.x、7.x等

#### macOS系统
- **macOS版本**：Monterey、Ventura、Sonoma等
- **系统架构**：x86_64、arm64
- **Homebrew**：是否安装Homebrew

### 2. SSH模式增强

在SSH远程模式下，AutoShell会通过SSH连接收集远程服务器的详细信息：

- 远程系统的发行版和版本
- 远程系统的包管理器
- 远程系统的架构和内核版本
- 远程用户的权限信息
- 远程系统的Python版本

### 3. 智能命令生成

基于收集的详细信息，LLM现在能够：

- **自动选择正确的包管理器**
  - Ubuntu/Debian → `apt` 或 `apt-get`
  - CentOS 7 → `yum`
  - CentOS 8+ → `dnf`
  - Arch Linux → `pacman`
  - Alpine Linux → `apk`
  - macOS → `brew`

- **调整命令语法**
  - 根据OS版本使用正确的命令参数
  - 考虑系统架构选择合适的软件包

- **权限管理**
  - 根据sudo权限自动添加或省略`sudo`

## 使用方法

### 基本使用

功能默认启用，无需额外配置。启动AutoShell时会自动收集系统信息：

```bash
# 本地模式
python main.py

# SSH模式
python main.py --ssh-host user@server --ssh-key ~/.ssh/id_rsa
```

### 配置选项

可以通过环境变量或`.env`文件配置：

```bash
# 是否收集详细信息（默认: true）
COLLECT_DETAILED_INFO=true

# 系统信息缓存时间（秒，默认: 300）
SYSTEM_INFO_CACHE_TTL=300

# SSH信息收集超时（秒，默认: 10）
SSH_INFO_TIMEOUT=10
```

### 禁用详细信息收集

如果不需要详细信息收集功能，可以禁用：

```bash
# 在 .env 文件中设置
COLLECT_DETAILED_INFO=false
```

## 示例

### 示例1：本地Linux系统

启动时显示：
```
Detected: Ubuntu 22.04.3 LTS | Package Manager: apt
```

执行命令：
```
AutoShell > 安装nginx
```

LLM会生成：
```json
{
  "thought": "Install nginx using apt package manager on Ubuntu system",
  "steps": [
    {
      "description": "Update package lists",
      "command": "sudo apt update"
    },
    {
      "description": "Install nginx",
      "command": "sudo apt install -y nginx"
    }
  ]
}
```

### 示例2：SSH远程CentOS 8

启动时显示：
```
Remote System: CentOS Linux 8 (Core) | x86_64 | Package Manager: dnf
```

执行命令：
```
AutoShell > 安装nginx
```

LLM会生成：
```json
{
  "thought": "Install nginx using dnf package manager on CentOS 8 system",
  "steps": [
    {
      "description": "Install nginx",
      "command": "sudo dnf install -y nginx"
    }
  ]
}
```

### 示例3：macOS系统

启动时显示：
```
Detected: macOS Sonoma (14.1) | arm64
```

执行命令：
```
AutoShell > 安装wget
```

LLM会生成：
```json
{
  "thought": "Install wget using Homebrew on macOS",
  "steps": [
    {
      "description": "Install wget",
      "command": "brew install wget"
    }
  ]
}
```

## 性能考虑

### 信息收集时间

- **本地模式**：< 100ms，几乎无感知
- **SSH模式**：1-2秒（首次连接时）

### 缓存机制

系统信息会被缓存，默认缓存时间为5分钟（300秒）。在缓存有效期内，不会重复收集信息，确保性能。

### 错误处理

如果信息收集失败（如权限不足、超时等），AutoShell会：
1. 显示警告信息
2. 使用基本信息继续运行
3. 不影响核心功能

## 调试

启用调试模式查看详细的信息收集过程：

```bash
python main.py --debug
```

调试输出示例：
```
[DEBUG] System info collected: {
  'os_type': 'Linux',
  'distro_pretty_name': 'Ubuntu 22.04.3 LTS',
  'architecture': 'x86_64',
  'kernel': '5.15.0-91-generic',
  'package_manager': 'apt',
  'has_sudo': True,
  'python_version': '3.10.12'
}
```

## 技术实现

### 架构组件

1. **ContextManager** (`autoshell/context.py`)
   - 负责本地系统信息收集
   - 提供增强的上下文字符串格式化

2. **SSHContextManager** (`autoshell/ssh_context.py`)
   - 负责SSH远程系统信息收集
   - 通过SSH执行探测命令

3. **AutoShellAgent** (`autoshell/agent.py`)
   - 集成系统信息收集
   - 实现缓存机制
   - 管理信息生命周期

4. **LLMClient** (`autoshell/llm.py`)
   - 更新的system prompt
   - 包含OS特定的命令生成指导

### 信息收集方法

#### Linux系统
- 读取 `/etc/os-release` 获取发行版信息
- 使用 `platform` 模块获取基本信息
- 检测常见包管理器的存在性
- 测试sudo权限（非阻塞）

#### SSH远程系统
- 执行 `uname` 系列命令获取基本信息
- 读取远程 `/etc/os-release` 文件
- 检测远程包管理器
- 测试远程sudo权限

## 兼容性

### 支持的Linux发行版

- Ubuntu / Debian
- CentOS / RHEL
- Fedora
- Arch Linux
- Alpine Linux
- openSUSE
- 其他基于上述发行版的衍生版

### 支持的包管理器

- apt / apt-get (Debian系)
- yum (CentOS 7及更早)
- dnf (CentOS 8+, Fedora)
- pacman (Arch Linux)
- zypper (openSUSE)
- apk (Alpine Linux)
- brew (macOS)

## 故障排查

### 问题1：信息收集失败

**症状**：
```
Warning: Failed to collect system info: ...
```

**解决方案**：
1. 检查是否有读取系统文件的权限
2. 确认 `/etc/os-release` 文件存在
3. 尝试禁用详细信息收集：`COLLECT_DETAILED_INFO=false`

### 问题2：SSH模式超时

**症状**：
```
Warning: Failed to collect remote system info: timeout
```

**解决方案**：
1. 增加超时时间：`SSH_INFO_TIMEOUT=20`
2. 检查SSH连接是否稳定
3. 确认远程服务器响应正常

### 问题3：包管理器检测错误

**症状**：LLM使用了错误的包管理器

**解决方案**：
1. 启用调试模式查看检测结果
2. 手动指定包管理器（未来功能）
3. 报告issue以改进检测逻辑

## 未来改进

1. **更多系统信息**
   - 已安装的关键软件版本（docker、nginx等）
   - 系统资源信息（内存、磁盘）
   - 网络配置信息

2. **智能缓存失效**
   - 检测到环境变化时自动刷新缓存
   - 支持手动刷新命令

3. **多主机管理**
   - 保存多个SSH配置
   - 快速切换目标主机

4. **环境指纹**
   - 为常见环境创建预设配置
   - 加速信息收集过程

## 贡献

欢迎贡献代码以支持更多Linux发行版和包管理器！

相关文件：
- `autoshell/context.py` - 本地信息收集
- `autoshell/ssh_context.py` - SSH信息收集
- `plans/os-info-enhancement-design.md` - 设计文档
- `plans/os-info-implementation-guide.md` - 实施指南
