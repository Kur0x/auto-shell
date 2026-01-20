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

  Requirement: Convert user input to a SINGLE shell command.
  Response Format: JSON {"thought": "reasoning", "command": "actual_command"}
  ```
- **方法**:
  - `generate_command(user_query, context, error_history=None)`

### 2.4 执行引擎 (CommandExecutor)
负责安全检查和命令执行。
- **Whitelist**: `['ls', 'dir', 'pwd', 'echo', 'whoami', 'date', 'cd']` (注意: `cd` 需要特殊处理，因为它是 shell 内置命令，subprocess 无法持久化改变父进程目录，但可以在单次 session 中模拟或提示限制)
- **方法**:
  - `is_safe(command)`: 检查白名单
  - `execute(command, require_confirmation=True)`: 
    - 如果 `is_safe` -> 直接运行
    - 否则 -> `rich` 高亮展示 -> 等待用户输入 `[Y/n]` -> 运行
    - 返回: `(return_code, stdout, stderr)`

### 2.5 主控制流 (Agent)
协调上述组件，实现 "自愈闭环"。
- **Loop**:
  1. 获取用户输入。
  2. `ContextManager` 获取环境。
  3. `LLMClient` 生成命令。
  4. 解析 JSON。
  5. `CommandExecutor` 执行。
  6. **IF** 失败 (code != 0):
     - 将 output/error 添加到历史。
     - 只有当重试次数 < MAX 时，回到步骤 3 (附带错误信息)。
     - **ELSE**: 报告最终失败。
  7. **IF** 成功: 显示结果。

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
