# 交互式执行模式

AutoShell 现在支持在命令执行过程中与用户进行交互，让 AI 能够智能地判断何时需要用户输入或确认。

## 功能概述

交互式执行模式允许 LLM 在生成执行计划时，插入需要用户参与的步骤，包括：

- ✅ **确认操作** - 是/否选择
- ✅ **文本输入** - 自由文本输入（支持正则验证）
- ✅ **多选项选择** - 从列表中选择一个选项
- ✅ **密码输入** - 隐藏显示的敏感信息输入

## 使用场景

### 1. 用户明确要求交互

当用户在命令中明确表示需要交互时：

```bash
# 让用户输入用户名
python main.py -c "创建新用户，用户名让我输入"

# 让用户选择版本
python main.py -c "安装 nginx，让我选择版本"

# 让用户确认操作
python main.py -c "删除日志文件，先问我是否确认"
```

### 2. 潜在危险操作

LLM 会自动判断某些操作需要用户确认：

```bash
# 删除文件
python main.py -c "删除 /tmp 目录下所有 .log 文件"
# AI 会自动插入确认步骤

# 修改系统配置
python main.py -c "修改 nginx 配置文件"
# AI 可能会要求确认
```

### 3. 需要用户提供信息

当任务需要用户提供特定信息时：

```bash
# 需要密码
python main.py -c "连接到数据库，密码我来输入"

# 需要配置值
python main.py -c "配置服务端口，端口号让我指定"
```

## 交互命令类型

### 1. 确认操作 (`__USER_CONFIRM__`)

用于是/否确认：

```json
{
  "description": "确认删除日志文件",
  "command": "__USER_CONFIRM__",
  "prompt": "即将删除 /var/log/*.log 文件，是否继续？",
  "default": "no"
}
```

**用户界面示例：**
```
┌─────────────────────────────────────────┐
│ ⚠️  确认操作                             │
│ 即将删除 /var/log/*.log 文件，是否继续？  │
│ 是否继续？ [Y/n]:                        │
└─────────────────────────────────────────┘
```

### 2. 文本输入 (`__USER_INPUT__`)

用于获取用户输入的文本：

```json
{
  "description": "获取用户名",
  "command": "__USER_INPUT__",
  "prompt": "请输入新用户的用户名",
  "default": "",
  "validation": "^[a-z][a-z0-9_-]*$"
}
```

**参数说明：**
- `prompt`: 提示信息
- `default`: 默认值（可选）
- `validation`: 正则表达式验证模式（可选）

**用户界面示例：**
```
┌─────────────────────────────────────────┐
│ 📝 输入信息                              │
│ 请输入新用户的用户名                      │
│ 格式要求: ^[a-z][a-z0-9_-]*$            │
│ 请输入: _                                │
└─────────────────────────────────────────┘
```

### 3. 多选项选择 (`__USER_CHOICE__`)

让用户从多个选项中选择：

```json
{
  "description": "选择 nginx 版本",
  "command": "__USER_CHOICE__",
  "prompt": "请选择要安装的 nginx 版本",
  "options": ["stable", "mainline", "legacy"],
  "default": "stable"
}
```

**用户界面示例：**
```
┌─────────────────────────────────────────┐
│ 🔢 选择选项                              │
│ 请选择要安装的 nginx 版本                 │
│                                         │
│   1. stable (默认)                      │
│   2. mainline                           │
│   3. legacy                             │
│ 请选择 [1-3]: _                          │
└─────────────────────────────────────────┘
```

### 4. 密码输入 (`__USER_PASSWORD__`)

用于输入密码等敏感信息（输入时隐藏）：

```json
{
  "description": "获取数据库密码",
  "command": "__USER_PASSWORD__",
  "prompt": "请输入数据库密码"
}
```

**用户界面示例：**
```
┌─────────────────────────────────────────┐
│ 🔒 密码输入                              │
│ 请输入数据库密码                          │
│ 输入将被隐藏                              │
│ 密码: ****                               │
└─────────────────────────────────────────┘
```

## 引用用户输入

在后续步骤中，可以使用占位符引用用户的输入：

### 按步骤编号引用

```json
{
  "steps": [
    {
      "description": "获取用户名",
      "command": "__USER_INPUT__",
      "prompt": "请输入用户名"
    },
    {
      "description": "创建用户",
      "command": "sudo useradd ${USER_INPUT_1}"
    },
    {
      "description": "设置密码",
      "command": "sudo passwd ${USER_INPUT_1}"
    }
  ]
}
```

- `${USER_INPUT_1}` - 引用第 1 步的用户输入
- `${USER_INPUT_2}` - 引用第 2 步的用户输入
- 以此类推...

### 引用最后一次输入

```json
{
  "steps": [
    {
      "description": "获取端口号",
      "command": "__USER_INPUT__",
      "prompt": "请输入端口号",
      "validation": "^[0-9]{1,5}$"
    },
    {
      "description": "启动服务",
      "command": "python app.py --port ${USER_INPUT_LAST}"
    }
  ]
}
```

- `${USER_INPUT_LAST}` - 引用最后一次用户输入

## 完整示例

### 示例 1：创建用户（带验证）

```bash
python main.py -c "创建新用户，用户名让我输入"
```

**执行流程：**

1. AI 生成计划：
```json
{
  "thought": "需要用户提供用户名，然后创建用户并设置密码",
  "steps": [
    {
      "description": "获取用户名",
      "command": "__USER_INPUT__",
      "prompt": "请输入新用户的用户名",
      "validation": "^[a-z][a-z0-9_-]*$"
    },
    {
      "description": "创建用户",
      "command": "sudo useradd ${USER_INPUT_1}"
    },
    {
      "description": "设置用户密码",
      "command": "sudo passwd ${USER_INPUT_1}"
    }
  ]
}
```

2. 用户输入：`john_doe`

3. 执行命令：
   - `sudo useradd john_doe`
   - `sudo passwd john_doe`

### 示例 2：安装软件（选择版本）

```bash
python main.py -c "安装 nginx，让我选择版本"
```

**执行流程：**

1. AI 生成计划：
```json
{
  "thought": "让用户选择 nginx 版本，然后安装",
  "steps": [
    {
      "description": "选择 nginx 版本",
      "command": "__USER_CHOICE__",
      "prompt": "请选择要安装的 nginx 版本",
      "options": ["stable", "mainline"],
      "default": "stable"
    },
    {
      "description": "安装 nginx",
      "command": "sudo apt install -y nginx-${USER_INPUT_1}"
    }
  ]
}
```

2. 用户选择：`mainline`

3. 执行命令：`sudo apt install -y nginx-mainline`

### 示例 3：危险操作确认

```bash
python main.py -c "删除 /tmp 目录下所有 .log 文件"
```

**执行流程：**

1. AI 生成计划（自动插入确认步骤）：
```json
{
  "thought": "删除文件是危险操作，需要用户确认",
  "steps": [
    {
      "description": "确认删除操作",
      "command": "__USER_CONFIRM__",
      "prompt": "即将删除 /tmp/*.log 文件，是否继续？",
      "default": "no"
    },
    {
      "description": "删除日志文件",
      "command": "sudo rm -f /tmp/*.log"
    }
  ]
}
```

2. 用户确认：`yes`

3. 执行命令：`sudo rm -f /tmp/*.log`

## SSH 远程模式支持

交互式功能在 SSH 远程模式下同样可用：

```bash
# SSH 远程执行 + 交互
python main.py --ssh-host user@example.com -c "创建用户，用户名让我输入"
```

**注意：** 交互发生在本地终端，命令在远程服务器执行。

## 自适应模式支持

交互式功能也支持自适应执行模式：

```bash
python main.py --adaptive -c "部署应用，配置文件路径让我指定"
```

## 最佳实践

### 1. 明确指示需要交互

在命令中明确表达需要交互：

✅ **好的示例：**
- "创建用户，用户名让我输入"
- "安装软件，版本让我选择"
- "删除文件，先问我是否确认"

❌ **不好的示例：**
- "创建用户" 