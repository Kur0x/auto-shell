# AutoShell 架构设计文档

## 1. 系统概述
AutoShell 是一个智能命令行工具，旨在将自然语言指令转换为安全的 Shell 命令执行。它具备环境感知、安全审计和自动纠错能力。

## 2. 核心组件设计

### 2.1 配置管理 (Configuration)
- 使用环境变量加载敏感信息。
- 支持 `.env` 文件。
- **关键配置项**:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL` (可选)
  - `LLM_MODEL` (默认: `gpt-3.5-turbo` 或其他)
  - `MAX_RETRIES` (默认: 3)

### 2.2 环境感知 (ContextManager)
负责收集运行时信息，构建 Prompt 的上下文部分。
- `get_os_info()`: 返回 "Windows", "Linux", "Darwin"
- `get_shell_type()`: 返回 "cmd", "powershell", "bash", "zsh"
- `get_cwd()`: 返回当前路径
- `get_user()`: 返回当前用户名

### 2.3 LLM 客户端 (LLMClient)
负责与 OpenAI 兼容接口通信。
- **System Prompt 模板**:
  ```text
  You are an expert system engineer...
  Context:
  - OS: {os}
  - Shell: {shell}
  - CWD: {cwd}
  - User: {user}

  Requirement: Convert user input to a SERIES of shell commands to accomplish the task.
  Response Format: JSON 
  {
    "thought": "Analysis of the task...",
    "steps": [
       {"description": "Create project directory", "command": "mkdir my_project"},
       {"description": "Navigate into directory", "command": "cd my_project"},
       {"description": "Create file", "command": "touch app.py"}
    ]
  }
  ```
- **方法**:
  - `generate_plan(user_query, context, error_history=None)`

### 2.4 执行引擎 (CommandExecutor)
负责安全检查和命令执行。
- **Whitelist**: `['ls', 'dir', 'pwd', 'echo', 'whoami', 'date', 'cd', 'mkdir', 'touch', 'cat', 'type']` (扩展白名单以支持更多文件操作)
- **方法**:
  - `is_safe(command)`: 检查白名单
  - `execute(command, cwd=None)`: 
    - 如果 `is_safe` -> 直接运行
    - 否则 -> `rich` 高亮展示 -> 等待用户输入 `[Y/n]` -> 运行
    - 增加 `cwd` 参数，确保在正确的上下文中运行。

### 2.5 主控制流 (Agent)
协调上述组件，实现 "批量执行" 和 "状态管理"。
- **State**: `session_cwd` (默认为启动目录)
- **Loop**:
  1. 获取用户输入。
  2. `LLMClient.generate_plan` 生成步骤列表。
  3. 展示计划概览。
  4. **For Each Step**:
     - 检查如果是 `cd <path>`:
       - 计算新路径。
       - 验证路径存在。
       - 更新 `session_cwd`。
       - (可选) 打印切换目录信息。
       - **Continue** (不调用 Executor)。
     - 调用 `CommandExecutor.execute(command, cwd=session_cwd)`。
     - **IF** 失败 (code != 0):
       - 触发自愈逻辑 (针对当前步骤重试)。
       - 如果自愈失败 -> **BREAK** (遇错即停)。
  5. 报告最终结果。

## 3. 技术栈
- Python 3.8+
- `openai`: API 交互
- `rich`: UI/UX (Spinner, Color, Input)
- `python-dotenv`: 配置加载
- `platform`, `os`, `subprocess`, `shutil`: 系统交互

## 4. 目录结构
```
AutoShell/
├── .env.example
├── requirements.txt
├── main.py
└── autoshell/
    ├── __init__.py
    ├── config.py
    ├── context.py
    ├── llm.py
    └── executor.py
```
