# AutoShell 执行卡住问题 - 诊断报告

## 问题描述
执行命令时卡在 `AutoShell > 执行ls ⠧ Generating plan...` 阶段，程序无响应。

## 诊断分析

### 识别的7个可能问题来源

1. **LLM API连接超时/失败** 
   - 位置: [`autoshell/llm.py:95`](autoshell/llm.py:95)
   - 原因: `client.chat.completions.create()` 调用可能因网络问题挂起

2. **无效的API密钥或Base URL**
   - 位置: [`.env:2,5`](.env:2)
   - 原因: API配置错误导致认证失败

3. **❌ 模型名称错误（最可能）**
   - 位置: [`.env:8`](.env:8)
   - 问题: `LLM_MODEL=gpt-5.2` 是无效的模型名称
   - OpenAI没有gpt-5.2模型，应使用 `gpt-4`, `gpt-3.5-turbo` 等

4. **❌ API调用缺少超时处理（最可能）**
   - 位置: [`autoshell/llm.py:95`](autoshell/llm.py:95)
   - 问题: 原代码没有设置 `timeout` 参数
   - 如果API端点 `https://api.v3.cm/v1/` 响应慢，会无限等待

5. **API响应格式异常**
   - 位置: [`autoshell/llm.py:109`](autoshell/llm.py:109)
   - 原因: LLM返回内容无法被正确解析

6. **异常处理不完整**
   - 位置: [`autoshell/agent.py:42-46`](autoshell/agent.py:42)
   - 原因: 可能没有捕获所有类型的错误

7. **环境变量加载失败**
   - 位置: [`autoshell/config.py:7`](autoshell/config.py:7)
   - 原因: `.env` 文件可能未正确加载

### 最可能的根本原因（Top 2）

#### 🔴 原因1: 无效的模型名称 `gpt-5.2`
- **严重程度**: 高
- **位置**: [`.env:8`](.env:8)
- **问题**: OpenAI API不存在 `gpt-5.2` 模型
- **影响**: API调用会返回错误或超时
- **建议修复**: 改为 `gpt-4` 或 `gpt-3.5-turbo`

#### 🔴 原因2: API调用缺少超时处理
- **严重程度**: 高
- **位置**: [`autoshell/llm.py:18`](autoshell/llm.py:18)
- **问题**: OpenAI客户端初始化时没有设置超时
- **影响**: 如果API端点不可达或响应慢，程序会无限等待
- **已修复**: 添加了 `timeout=30.0` 参数

## 已添加的调试日志

### 1. 配置加载阶段 ([`autoshell/config.py`](autoshell/config.py))
```python
- .env文件是否成功加载
- API Key是否存在
- Base URL配置
- 模型名称
- 最大重试次数
```

### 2. LLM客户端初始化 ([`autoshell/llm.py`](autoshell/llm.py))
```python
- API Base URL
- 模型名称
- API Key（脱敏显示）
- OpenAI客户端初始化状态
```

### 3. API调用过程 ([`autoshell/llm.py`](autoshell/llm.py))
```python
- 开始生成计划（显示查询内容）
- 调用LLM API（显示模型名称）
- API响应时间
- 原始响应长度
- 清理后的JSON长度
- 解析后的步骤数量
- 错误详情和堆栈跟踪
```

## 测试步骤

### 步骤1: 运行程序查看调试输出
```bash
python main.py
```

### 步骤2: 输入测试命令
```
AutoShell > 执行ls
```

### 步骤3: 观察调试输出
查看以下关键信息：
- ✅ `.env` 文件是否加载成功
- ✅ API配置是否正确
- ✅ 模型名称是什么
- ✅ API调用是否开始
- ✅ 是否出现超时或错误
- ✅ 错误类型和详细信息

## 预期的调试输出示例

### 正常情况：
```
[DEBUG] .env file loaded: True
[DEBUG] Validating configuration...
[DEBUG] OPENAI_API_KEY exists: True
[DEBUG] OPENAI_BASE_URL: https://api.v3.cm/v1/
[DEBUG] LLM_MODEL: gpt-5.2
[DEBUG] Initializing LLM Client...
[DEBUG] API Base URL: https://api.v3.cm/v1/
[DEBUG] Model: gpt-5.2
[DEBUG] API Key: sk-p6d4iqc...0dDb
[DEBUG] OpenAI client initialized successfully
[DEBUG] Starting plan generation for query: 执行ls...
[DEBUG] Calling LLM API with model: gpt-5.2
[ERROR] LLM API Error after 30.00s: APIError: Invalid model: gpt-5.2
```

### 如果是超时：
```
[DEBUG] Calling LLM API with model: gpt-5.2
[等待30秒...]
[ERROR] LLM API Error after 30.00s: TimeoutError: Request timed out
```

## 建议的修复方案

### 修复1: 更正模型名称（必须）
编辑 [`.env`](.env:8) 文件：
```bash
# 将
LLM_MODEL=gpt-5.2

# 改为（选择其一）
LLM_MODEL=gpt-4
# 或
LLM_MODEL=gpt-3.5-turbo
# 或
LLM_MODEL=gpt-4-turbo
```

### 修复2: 验证API端点（如果仍有问题）
测试API端点是否可达：
```bash
curl -X POST https://api.v3.cm/v1/chat/completions \
  -H "Authorization: Bearer sk-p6d4iqc4ZEebsTnvB4C4F2Ec983e4323A41c413e79840dDb" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"test"}]}'
```

### 修复3: 增加超时时间（如果网络慢）
如果30秒不够，可以在 [`autoshell/llm.py:23`](autoshell/llm.py:23) 增加超时：
```python
timeout=60.0  # 增加到60秒
```

## 下一步行动

1. **立即执行**: 运行 `python main.py` 并输入 `执行ls`
2. **观察输出**: 查看调试日志，确认具体错误
3. **应用修复**: 根据错误信息应用相应的修复方案
4. **验证修复**: 重新测试确认问题解决

---

**创建时间**: 2026-01-21  
**状态**: 等待用户测试确认
