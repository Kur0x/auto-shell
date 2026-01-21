# AutoShell SSH 使用指南

## 概述

AutoShell 现在支持通过命令行参数配置SSH远程执行模式，无需在环境变量中配置。同时支持一次性执行命令，无需进入交互模式。

## 安装依赖

首先确保安装了SSH支持所需的依赖：

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. 本地模式（默认）

#### 交互模式
```bash
python main.py
```

#### 一次性执行
```bash
python main.py -c "列出当前目录下的所有文件"
python main.py -c "创建一个名为test的目录"
```

### 2. SSH远程模式

#### SSH交互模式
```bash
# 使用密码认证（不推荐）
python main.py --ssh-host user@example.com --ssh-password yourpassword

# 使用SSH密钥认证（推荐）
python main.py --ssh-host user@example.com --ssh-key ~/.ssh/id_rsa

# 指定非标准端口
python main.py --ssh-host user@example.com --ssh-port 2222 --ssh-key ~/.ssh/id_rsa
```

#### SSH一次性执行
```bash
# 使用密钥认证执行单个命令
python main.py --ssh-host user@example.com --ssh-key ~/.ssh/id_rsa -c "检查磁盘使用情况"

# 执行复杂任务
python main.py --ssh-host admin@server.com --ssh-key ~/.ssh/id_rsa -c "重启nginx服务"

# 执行系统维护任务
python main.py --ssh-host root@server.com --ssh-key ~/.ssh/id_rsa -c "清理/tmp目录中超过7天的文件"
```

## 命令行参数说明

### 基本参数

- `-c, --command`: 一次性执行的命令内容（非交互模式）
  - 示例：`-c "列出所有进程"`

### SSH相关参数

- `--ssh-host`: SSH远程主机地址（格式：`user@host`）
  - 示例：`--ssh-host admin@192.168.1.100`
  
- `--ssh-port`: SSH端口号（默认：22）
  - 示例：`--ssh-port 2222`
  
- `--ssh-password`: SSH密码（不推荐，建议使用密钥）
  - 示例：`--ssh-password mypassword`
  
- `--ssh-key`: SSH私钥文件路径
  - 示例：`--ssh-key ~/.ssh/id_rsa`
  - 示例：`--ssh-key C:\Users\username\.ssh\id_rsa`

## 使用示例

### 示例1：本地一次性执行
```bash
python main.py -c "查找当前目录下所有的Python文件"
```

### 示例2：SSH远程交互模式
```bash
python main.py --ssh-host ubuntu@192.168.1.100 --ssh-key ~/.ssh/id_rsa
```
进入交互模式后，可以输入自然语言命令：
```
AutoShell > 检查系统负载
AutoShell > 查看nginx日志的最后50行
AutoShell > 重启docker容器
```

### 示例3：SSH远程一次性执行
```bash
# 检查远程服务器磁盘空间
python main.py --ssh-host root@server.com --ssh-key ~/.ssh/id_rsa -c "检查磁盘使用情况"

# 部署应用
python main.py --ssh-host deploy@app-server.com --ssh-key ~/.ssh/deploy_key -c "拉取最新代码并重启应用"

# 系统维护
python main.py --ssh-host admin@db-server.com --ssh-key ~/.ssh/id_rsa -c "备份数据库到/backup目录"
```

### 示例4：多服务器批量操作
```bash
# 可以通过脚本循环执行
for server in server1 server2 server3; do
    python main.py --ssh-host admin@$server.example.com --ssh-key ~/.ssh/id_rsa -c "更新系统软件包"
done
```

## 安全建议

1. **优先使用SSH密钥认证**：比密码认证更安全
2. **保护私钥文件**：确保私钥文件权限正确（Linux/Mac: `chmod 600 ~/.ssh/id_rsa`）
3. **避免在命令行中直接输入密码**：密码可能被记录在shell历史中
4. **使用专用密钥**：为自动化任务创建专用的SSH密钥对
5. **限制密钥权限**：在服务器端的`authorized_keys`中可以限制密钥的使用范围

## 故障排查

### 问题1：SSH连接失败
```
SSH Error: Authentication failed
```
**解决方案**：
- 检查用户名和主机地址是否正确
- 确认SSH密钥路径正确
- 验证密钥是否已添加到远程服务器的`~/.ssh/authorized_keys`

### 问题2：paramiko未安装
```
SSH support not available. Please install paramiko: pip install paramiko
```
**解决方案**：
```bash
pip install paramiko
```

### 问题3：权限被拒绝
```
SSH Error: Permission denied
```
**解决方案**：
- 检查SSH密钥文件权限（应为600）
- 确认远程服务器的SSH配置允许密钥认证
- 验证用户是否有执行命令的权限

## 高级用法

### 使用配置文件（未来功能）
可以创建配置文件来保存常用的SSH连接信息：

```yaml
# autoshell_config.yaml
ssh_profiles:
  production:
    host: admin@prod-server.com
    key: ~/.ssh/prod_key
    port: 22
  
  staging:
    host: admin@staging-server.com
    key: ~/.ssh/staging_key
    port: 2222
```

### 与CI/CD集成
在CI/CD流程中使用AutoShell进行自动化部署：

```yaml
# .gitlab-ci.yml 示例
deploy:
  script:
    - python main.py --ssh-host deploy@$SERVER_HOST --ssh-key $SSH_KEY_PATH -c "部署应用到生产环境"
```

## 注意事项

1. SSH模式下，命令仍然会经过安全检查
2. 危险命令需要用户确认后才会执行
3. 远程执行的工作目录可以通过LLM理解上下文自动处理
4. 建议在生产环境使用前先在测试环境验证

## 获取帮助

查看所有可用的命令行参数：
```bash
python main.py --help
```

输出示例：
```
usage: main.py [-h] [-c COMMAND] [--ssh-host SSH_HOST] [--ssh-port SSH_PORT]
               [--ssh-password SSH_PASSWORD] [--ssh-key SSH_KEY]

AutoShell - Intelligent Command Line Assistant

optional arguments:
  -h, --help            show this help message and exit
  -c COMMAND, --command COMMAND
                        一次性执行命令后退出（非交互模式）
  --ssh-host SSH_HOST   SSH远程主机（格式：user@host）
  --ssh-port SSH_PORT   SSH端口（默认：22）
  --ssh-password SSH_PASSWORD
                        SSH密码（不推荐，建议使用密钥）
  --ssh-key SSH_KEY     SSH私钥文件路径
```
