# AutoShell

AutoShell 是一个智能命令行助手，使用 AI 将自然语言转换为 Shell 命令并执行。

## 核心特性

✅ **自然语言转命令** - 用自然语言描述任务，AI 自动生成并执行命令
✅ **自适应执行** - 根据执行结果动态调整策略（新功能！）
✅ **SSH 远程执行** - 支持在远程服务器上执行命令
✅ **安全机制** - 命令白名单和用户确认
✅ **错误自愈** - 执行失败时自动修复
✅ **跨平台支持** - Windows、Linux、macOS

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd AutoShell

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 OPENAI_API_KEY
```

### 基本使用

#### 1. 本地模式

```bash
# 交互模式
python main.py

# 一次性执行
python main.py -c "列出当前目录下的所有文件"
```

#### 2. 自适应模式（新功能！）

自适应模式允许 AI 根据执行结果动态生成下一步操作，适合复杂任务。

```bash
# 条件执行：根据输出修改脚本
python main.py --adaptive -c "执行test.sh，如果输出为1则修改为2"

# 文件分析：提取错误信息
python main.py --adaptive -c "分析log.txt，提取ERROR信息到errors.txt"

# 配置更新：条件修改配置文件
python main.py --adaptive -c "读取config.json，如果debug为false则改为true"
```

**自适应模式特点**：
- 渐进式执行：每次生成1-3个步骤
- 反馈驱动：根据输出调整策略
- 条件判断：支持 if-then 逻辑
- 文件操作：使用 cat、sed、grep 等命令

详细文档：[ADAPTIVE_MODE.md](ADAPTIVE_MODE.md)

#### 3. SSH 远程模式

```bash
# SSH 交互模式
python main.py --ssh-host user@example.com

# SSH 一次性执行
python main.py --ssh-host user@example.com -c "检查磁盘使用情况"

# SSH + 自适应模式
python main.py --ssh-host user@example.com --adaptive -c "分析远程日志文件"

# 使用 SSH 密钥
python main.py --ssh-host user@example.com --ssh-key ~/.ssh/id_rsa -c "重启服务"
```

详细文档：[SSH_USAGE.md](SSH_USAGE.md)

## 使用示例

### 示例 1：简单任务（传统模式）

```bash
python main.py -c "创建一个名为test的目录，并在其中创建3个空文件"
```

### 示例 2：条件任务（自适应模式）

```bash
python main.py --adaptive -c "执行 ~/test/a.sh，如果输出为1则修改脚本让它输出为2"
```

**执行过程**：
1. AI 执行脚本，看到输出为 1
2. AI 使用 `sed` 命令修改脚本
3. AI 重新执行脚本，验证输出为 2

### 示例 3：文件分析（自适应模式）

```bash
python main.py --adaptive -c "检查 /var/log/app.log，如果有ERROR，提取到errors.txt"
```

**执行过程**：
1. AI 读取日志文件
2. AI 使用 `grep` 搜索 ERROR
3. AI 提取错误行并保存

### 示例 4：远程服务器（SSH + 自适应）

```bash
python main.py --ssh-host vub --adaptive -c "检查nginx配置，如果有错误则修复"
```

## 配置

### 环境变量

在 `.env` 文件中配置：

```bash
# LLM 配置（必需）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 执行配置
MAX_RETRIES=3
```

### 命令行参数

```bash
# 查看所有参数
python main.py --help

# 主要参数
--adaptive              # 启用自适应执行模式
-c, --command          # 一次性执行命令
--ssh-host             # SSH 远程主机
--ssh-port             # SSH 端口（默认22）
--ssh-key              # SSH 私钥路径
--ssh-password         # SSH 密码（不推荐）
```

## 模式对比

| 特性 | 传统模式 | 自适应模式 |
|------|----------|------------|
| 执行方式 | 一次性生成所有步骤 | 渐进式生成 |
| 反馈循环 | 无 | 有 |
| 条件判断 | 不支持 | 支持 |
| 文件操作 | 通过命令 | 通过命令（更智能） |
| 适用场景 | 简单、确定的任务 | 复杂、需要判断的任务 |
| LLM 调用 | 1次 | 多次 |

## 项目结构

```
AutoShell/
├── main.py                 # 入口文件
├── autoshell/             # 核心模块
│   ├── agent.py           # 主控制器
│   ├── llm.py             # LLM 客户端
│   ├── executor.py        # 命令执行器
│   ├── context.py         # 环境上下文
│   └── config.py          # 配置管理
├── plans/                 # 设计文档
├── ADAPTIVE_MODE.md       # 自适应模式文档
├── SSH_USAGE.md           # SSH 使用文档
└── test_adaptive.py       # 测试脚本
```

## 安全机制

1. **命令白名单**：只允许执行安全的命令
2. **用户确认**：危险操作需要用户确认
3. **SSH 认证**：支持密钥和密码认证
4. **路径限制**：限制文件操作范围

## 开发和测试

### 运行测试

```bash
# 查看测试选项
python test_adaptive.py

# 运行特定测试
python test_adaptive.py conditional
python test_adaptive.py analysis
```

### 调试

```bash
# 查看详细日志
python main.py --adaptive -c "你的任务" 2>&1 | tee debug.log
```

## 文档

- [自适应执行模式](ADAPTIVE_MODE.md) - 详细使用指南
- [SSH 使用指南](SSH_USAGE.md) - SSH 配置和使用
- [设计文档](plans/) - 架构设计和实现细节

## 常见问题

### Q: 什么时候使用自适应模式？

A: 当任务需要根据输出做决策时，例如：
- 条件执行（if-then 逻辑）
- 文件内容分析
- 多步骤协调
- 错误检测和修复

### Q: 自适应模式会调用多次 LLM 吗？

A: 是的，每次迭代调用一次。复杂任务可能需要 5-10 次迭代。

### Q: 如何限制 LLM 调用次数？

A: 自适应模式有最大迭代次数限制（默认50次），可以在代码中调整。

### Q: SSH 模式下文件路径如何处理？

A: 所有路径都相对于远程主机，使用远程主机的文件系统。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 更新日志

### v1.1.0 (2026-01-21)

- ✨ 新增自适应执行模式
- ✨ 支持根据输出动态生成下一步
- ✨ 支持条件判断和复杂任务
- 📝 完善文档和示例

### v1.0.0

- ✨ 基础功能实现
- ✨ SSH 远程执行支持
- ✨ 错误自愈机制

---

**文档更新**：2026-01-21
