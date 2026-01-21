# AutoShell 更新日志

## [未发布] - 2026-01-21

### 新增功能

#### 1. 命令行参数支持
- 添加了 `-c, --command` 参数，支持一次性执行命令而无需进入交互模式
- 示例：`python main.py -c "列出当前目录下的所有文件"`

#### 2. SSH远程执行支持
- 通过命令行参数配置SSH连接，无需在环境变量中设置
- 支持的SSH参数：
  - `--ssh-host`: SSH远程主机（格式：user@host）
  - `--ssh-port`: SSH端口（默认：22）
  - `--ssh-password`: SSH密码（不推荐）
  - `--ssh-key`: SSH私钥文件路径（推荐）

#### 3. SSH模式示例

**本地一次性执行：**
```bash
python main.py -c "查找所有Python文件"
```

**SSH交互模式：**
```bash
python main.py --ssh-host user@example.com --ssh-key ~/.ssh/id_rsa
```

**SSH一次性执行：**
```bash
python main.py --ssh-host user@example.com --ssh-key ~/.ssh/id_rsa -c "检查磁盘使用情况"
```

### 技术改进

1. **模块化SSH支持**
   - 在 [`autoshell/executor.py`](autoshell/executor.py) 中添加了 `_execute_ssh()` 方法
   - 使用 `paramiko` 库实现SSH连接和命令执行
   - 支持密码和密钥两种认证方式

2. **增强的命令行接口**
   - 在 [`main.py`](main.py) 中使用 `argparse` 实现完整的命令行参数解析
   - 提供详细的帮助信息和使用示例

3. **Agent架构改进**
   - [`AutoShellAgent`](autoshell/agent.py) 现在接受 `ssh_config` 参数
   - 自动将SSH配置传递给命令执行器

### 依赖更新

- 添加 `paramiko>=3.0.0` 到 [`requirements.txt`](requirements.txt)

### 文档

- 创建了详细的 [`SSH_USAGE.md`](SSH_USAGE.md) 使用指南
- 包含安全建议和故障排查指南

### 向后兼容性

- 所有现有功能保持不变
- 本地交互模式仍然是默认行为
- 环境变量配置继续有效（用于API密钥等）

### 使用帮助

查看所有可用参数：
```bash
python main.py --help
```

详细使用说明请参考 [`SSH_USAGE.md`](SSH_USAGE.md)
