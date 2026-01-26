# AutoShell 增强自适应模式文档

## 概述

增强的自适应执行模式为 AutoShell 提供了更强大的任务处理能力，包括多阶段任务规划、智能错误恢复和结构化的执行上下文管理。

## 新增功能

### 1. 多阶段任务规划 (Task Planner)

**功能描述：**
- 自动将复杂任务分解为多个逻辑阶段
- 管理阶段之间的依赖关系
- 提供清晰的任务进度追踪

**使用示例：**
```bash
python main.py --adaptive "部署一个 Web 应用：克隆代码、安装依赖、配置环境、启动服务"
```

**工作流程：**
1. AI 分析任务并生成阶段计划
2. 显示任务执行计划表格
3. 按阶段顺序执行，自动处理依赖关系
4. 实时显示每个阶段的进度

### 2. 智能错误恢复 (Error Recovery)

**功能描述：**
- 自动分类错误类型（权限、命令不存在、文件未找到等）
- 根据错误类型选择恢复策略
- 支持自动重试和智能修复

**错误类型识别：**
- `COMMAND_NOT_FOUND` - 命令不存在
- `PERMISSION_DENIED` - 权限不足
- `FILE_NOT_FOUND` - 文件不存在
- `NETWORK_ERROR` - 网络错误
- `SYNTAX_ERROR` - 语法错误
- `RESOURCE_UNAVAILABLE` - 资源不可用

**恢复策略：**
- `RETRY_WITH_SUDO` - 自动添加 sudo 重试
- `RETRY_SAME` - 重试相同命令（网络错误等）
- `ASK_LLM_FOR_FIX` - 请求 AI 生成修复方案
- `SKIP_AND_CONTINUE` - 跳过并继续
- `ABORT` - 中止执行

**示例场景：**
```bash
# 场景1：权限不足
$ cat /etc/shadow
# 系统自动检测到权限错误，尝试：
$ sudo cat /etc/shadow

# 场景2：命令不存在
$ netstat -tuln
# AI 检测到命令不存在，建议替代方案：
$ ss -tuln
```

### 3. 结构化执行上下文 (Adaptive Context)

**功能描述：**
- 记录每个步骤的详细执行信息
- 自动提取关键数据（路径、IP、数字等）
- 维护执行变量和状态
- 提供上下文摘要供 AI 参考

**上下文信息包括：**
- 执行历史和步骤状态
- 成功/失败统计
- 提取的关键信息
- 阶段进度追踪

## 架构设计

### 核心模块

```
autoshell/
├── adaptive_context.py    # 执行上下文管理
├── task_planner.py        # 任务规划器
├── error_recovery.py      # 错误恢复管理
└── agent.py              # 集成增强功能
```

### 数据流

```
用户输入
    ↓
任务规划器 (分解为阶段)
    ↓
执行上下文 (管理状态)
    ↓
步骤生成 (AI 生成命令)
    ↓
命令执行
    ↓
错误检测 → 错误恢复 → 重试/修复
    ↓
更新上下文
    ↓
下一阶段/完成
```

## 配置选项

在 `.env` 文件中添加以下配置：

```bash
# 自适应执行配置
ADAPTIVE_MAX_ITERATIONS=50              # 最大迭代次数
ADAPTIVE_MAX_STEPS_PER_ITERATION=3      # 每次迭代最多生成的步骤数
ADAPTIVE_MAX_CONSECUTIVE_FAILURES=5     # 最大连续失败次数
MAX_RETRIES=3                           # 单个命令最大重试次数
```

## 使用方法

### 基本用法

```bash
# 启用增强自适应模式
python main.py --adaptive "你的任务描述"

# 带调试信息
python main.py --adaptive "你的任务描述" --debug

# SSH 远程执行
python main.py --adaptive "你的任务描述" --ssh user@host
```

### 高级用法

```bash
# 复杂任务示例
python main.py --adaptive "搭建开发环境：安装 Python 3.11、配置虚拟环境、安装项目依赖"

# 带上下文文件
python main.py --adaptive "分析日志文件并生成报告" --context logs/app.log

# 多步骤任务
python main.py --adaptive "备份数据库、更新应用代码、重启服务、验证健康状态"
```

## 功能对比

| 功能 | 原始模式 | 增强模式 |
|------|---------|---------|
| 任务规划 | 单次生成所有步骤 | 多阶段分解 |
| 错误处理 | 简单重试 | 智能分类和恢复 |
| 上下文管理 | 简单历史列表 | 结构化上下文 |
| 进度追踪 | 步骤计数 | 阶段和步骤双层追踪 |
| 依赖管理 | 无 | 阶段依赖关系 |
| 数据提取 | 无 | 自动提取关键信息 |

## 实现细节

### 1. TaskPlanner 类

```python
from autoshell.task_planner import TaskPlanner

planner = TaskPlanner(llm_client)
context = planner.analyze_and_plan(
    user_goal="用户目标",
    system_context="系统信息",
    user_context="用户上下文"
)

# 获取下一个可执行阶段
phase = planner.get_next_executable_phase()

# 检查完成状态
if planner.is_plan_complete():
    print("所有阶段完成")
```

### 2. ErrorRecoveryManager 类

```python
from autoshell.error_recovery import ErrorRecoveryManager

error_manager = ErrorRecoveryManager(max_retries=3)

# 分析错误
analysis = error_manager.analyze_error(
    command="cat /etc/shadow",
    error_message="Permission denied",
    return_code=1
)

# 判断是否重试
should_retry, retry_cmd = error_manager.should_retry(command, analysis)
```

### 3. AdaptiveExecutionContext 类

```python
from autoshell.adaptive_context import AdaptiveExecutionContext, ExecutionStep

context = AdaptiveExecutionContext()

# 创建阶段
phase = context.create_phase(
    phase_id=1,
    name="准备环境",
    goal="安装必要的依赖",
    dependencies=[]
)

# 添加步骤
step = ExecutionStep(
    description="安装 Python",
    command="apt-get install python3",
    output="...",
    success=True
)
context.add_step_to_current_phase(step)

# 获取上下文摘要
summary = context.get_context_summary()
```

## 性能优化

### 1. 上下文管理
- 限制历史记录长度（默认 50 条）
- 智能摘要生成，只传递关键信息给 AI
- 自动提取和缓存关键数据

### 2. 错误恢复
- 快速错误分类（正则匹配）
- 避免无效重试（最大重试次数限制）
- 连续失败检测（防止死循环）

### 3. 任务规划
- 缓存系统信息（TTL 5分钟）
- 阶段依赖关系优化
- 并行执行支持（未来版本）

## 故障排除

### 问题1：任务规划失败

**症状：** 显示"任务规划失败"错误

**解决方案：**
1. 检查 LLM 连接是否正常
2. 确认任务描述清晰明确
3. 使用 `--debug` 查看详细日志

### 问题2：错误恢复无效

**症状：** 错误重复发生，无法恢复

**解决方案：**
1. 检查错误类型是否正确识别
2. 增加 `MAX_RETRIES` 配置
3. 手动介入修复环境问题

### 问题3：执行卡住

**症状：** 长时间无响应

**解决方案：**
1. 检查是否达到最大迭代次数
2. 使用 Ctrl+C 中断执行
3. 减少 `ADAPTIVE_MAX_ITERATIONS` 配置

## 最佳实践

### 1. 任务描述
- 使用清晰、具体的描述
- 分解复杂任务为子目标
- 提供必要的上下文信息

### 2. 错误处理
- 设置合理的重试次数
- 监控连续失败情况
- 及时介入处理异常

### 3. 性能优化
- 使用上下文文件提供背景信息
- 避免过于复杂的单次任务
- 定期清理执行历史

## 未来计划

- [ ] 并行阶段执行
- [ ] 更丰富的错误恢复策略
- [ ] 执行计划可视化
- [ ] 任务模板和预设
- [ ] 执行历史持久化
- [ ] 性能指标和分析

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
