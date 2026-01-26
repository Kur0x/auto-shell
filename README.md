# AutoShell

AutoShell 是一个智能命令行助手，使用 AI 将自然语言转换为 Shell 命令并执行。

## 核心特性

✅ **自然语言转命令** - 用自然语言描述任务，AI 自动生成并执行命令
✅ **智能环境识别** - 自动识别OS发行版和包管理器，生成精准命令
✅ **交互式执行** - 支持用户确认、输入、选择等交互操作（新功能！）⭐
✅ **上下文文件支持** - 提供文本文件作为上下文，让AI更好地理解需求
✅ **自适应执行** - 根据执行结果动态调整策略
✅ **SSH 远程执行** - 支持在远程服务器上执行命令，自动识别远程环境
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

#### 3. 上下文文件模式（新功能！）

上下文文件功能允许您提供文本文件作为上下文信息，让AI更好地理解您的需求。

```bash
# 使用单个上下文文件
python main.py -f examples.txt -c "创建类似的脚本"

# 使用多个上下文文件
python main.py -f config.md -f examples.txt -c "配置环境"

# 结合自适应模式
python main.py --adaptive -f requirements.md -c "检查并安装依赖"

# 结合SSH模式
python main.py --ssh-host user@server -f deploy.md -c "部署应用"
```

**上下文文件用途**：
- 提供命令示例供参考
- 说明配置要求和规范
- 提供项目文档和说明
- 指定环境配置指令（如proxy设置）

详细文档：[CONTEXT_FILE_USAGE.md](CONTEXT_FILE_USAGE.md)

#### 4. 交互式执行模式（新功能！）⭐

交互式执行模式允许 AI 在执行过程中与用户交互，获取确认、输入或选择。

```bash
# 让用户输入信息
python main.py -c "创建新用户，用户名让我输入"

# 让用户选择选项
python main.py -c "安装 nginx，让我选择版本"

# 危险操作自动请求确认
python main.py -c "删除 /tmp 目录下所有 .log 文件"
# AI 会自动插入确认步骤

# 结合 SSH 模式
python main.py --ssh-host user@server -c "创建用户，用户名让我输入"

# 结合自适应模式
python main.py --adaptive -c "部署应用，配置文件路径让我指定"
```

**交互类型**：
- 🔘 **确认操作** - 是/否选择
- 📝 **文本输入** - 自由文本输入（支持正则验证）
- 🔢 **多选项选择** - 从列表中选择
- 🔒 **密码输入** - 隐藏显示的敏感信息

详细文档：[docs/INTERACTIVE_MODE.md](docs/INTERACTIVE_MODE.md)

#### 5. SSH 远程模式

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

#### 6. 调试模式

默认情况下，AutoShell 不显示调试信息。如需查看详细的执行日志，可以使用 `--debug` 参数：

```bash
# 启用调试输出
python main.py --debug -c "列出当前目录"

# 调试模式 + 自适应模式
python main.py --debug --adaptive -c "执行复杂任务"
```

**调试模式会显示**：
- LLM 客户端初始化信息
- API 调用详情和响应时间
- JSON 解析过程
- 错误堆栈跟踪

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

### LLM 提供商

AutoShell 支持多种 LLM 提供商：

#### 1. OpenAI API（默认）

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
```

#### 2. Ollama（本地）⭐ 新增

首先安装并启动 Ollama：

```bash
# 安装 Ollama (参考 https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取模型
ollama pull qwen2.5:7b

# 启动 Ollama 服务（通常自动启动）
ollama serve
```

然后配置 AutoShell：

```bash
OPENAI_API_KEY=ollama  # 任意字符串
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:7b
```

**推荐模型**：
- `qwen2.5:7b` - 通义千问 2.5（中文优秀）⭐ 推荐
- `qwen2.5:14b` - 更强大，需要更多内存
- `llama3.1:8b` - Meta Llama 3.1（英文优秀）
- `mistral:7b` - Mistral AI（速度快）

**Ollama 优势**：
- 🚀 完全本地运行，数据不离开你的电脑
- 💰 免费使用，无 API 调用费用
- ⚡ 低延迟，响应更快
- 🔒 隐私保护，敏感命令不会发送到云端

详细设置指南：[plans/OLLAMA_SETUP.md](plans/OLLAMA_SETUP.md)

#### 3. 其他兼容 API

任何提供 OpenAI 兼容 API 的服务都可以使用：

```bash
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://your-endpoint.com/v1
LLM_MODEL=your-model
```

### 执行配置

```bash
# 最大重试次数
MAX_RETRIES=3

# 系统信息收集配置（新功能！）
COLLECT_DETAILED_INFO=true      # 是否收集详细系统信息
SYSTEM_INFO_CACHE_TTL=300       # 系统信息缓存时间（秒）
SSH_INFO_TIMEOUT=10             # SSH信息收集超时（秒）
```

**智能环境识别**：AutoShell 现在能够自动识别：
- Linux发行版（Ubuntu、CentOS、Debian等）和版本
- 包管理器（apt、yum、dnf、pacman等）
- 系统架构（x86_64、aarch64等）
- SSH远程服务器的详细信息

这使得AI能够生成更精准的命令，例如：
- Ubuntu系统自动使用 `apt`
- CentOS 8自动使用 `dnf`
- Arch Linux自动使用 `pacman`

详细文档：[OS_INFO_FEATURE.md](OS_INFO_FEATURE.md)

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
--debug                # 启用调试输出模式
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

- [交互式执行模式](docs/INTERACTIVE_MODE.md) - 交互式执行功能详解 ⭐ 最新
- [上下文文件使用指南](CONTEXT_FILE_USAGE.md) - 上下文文件功能详解
- [智能环境识别](OS_INFO_FEATURE.md) - OS信息增强功能
- [自适应执行模式](ADAPTIVE_MODE.md) - 详细使用指南
- [SSH 使用指南](SSH_USAGE.md) - SSH 配置和使用
- [Ollama 设置指南](plans/OLLAMA_SETUP.md) - 本地 LLM 配置
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

### v1.4.0 (2026-01-26) ⭐ 最新

- ✨ **交互式执行模式** - 支持用户确认、输入、选择等交互操作
- ✨ 四种交互类型：确认、文本输入、多选项、密码
- ✨ 输入验证（正则表达式）
- ✨ 占位符引用用户输入（${USER_INPUT_N}）
- ✨ SSH 和自适应模式完全支持交互
- 🚀 智能判断何时需要用户交互
- 📝 新增交互式模式文档

详细文档：[docs/INTERACTIVE_MODE.md](docs/INTERACTIVE_MODE.md)

### v1.3.0 (2026-01-26)

- ✨ **增强自适应模式** - 多阶段任务规划和智能错误恢复
- ✨ 任务自动分解为多个逻辑阶段
- ✨ 智能错误分类和恢复策略（权限、命令不存在等）
- ✨ 结构化执行上下文管理
- ✨ 自动提取关键信息（路径、IP、数字等）
- 🚀 阶段依赖关系管理
- 🚀 连续失败检测和中止机制
- 📝 新增增强自适应模式文档

详细文档：[ADAPTIVE_MODE_ENHANCED.md](ADAPTIVE_MODE_ENHANCED.md)

### v1.2.0 (2026-01-22)

- ✨ 新增智能环境识别功能
- ✨ 自动识别Linux发行版和包管理器
- ✨ SSH模式支持远程系统信息收集
- ✨ 根据OS类型生成精准命令
- 🚀 系统信息缓存机制提升性能
- 📝 新增OS信息功能文档

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

**文档更新**：2026-01-22
