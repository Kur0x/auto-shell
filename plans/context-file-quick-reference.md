# 上下文文件功能 - 快速参考

## 一句话总结

允许用户通过 `-f` 参数提供文本文件作为上下文，让LLM更好地理解需求并生成精准命令。

## 快速开始

```bash
# 1. 创建上下文文件
echo "示例命令：ls -la" > examples.txt

# 2. 使用上下文文件
python main.py -f examples.txt -c "执行类似的命令"

# 3. 使用多个文件
python main.py -f config.md -f examples.txt -c "配置环境"
```

## 命令格式

```bash
python main.py [选项] -f <文件路径> -c "<命令>"

选项：
  -f, --context-file  上下文文件路径（可多次使用）
  --adaptive          自适应模式
  --ssh-host          SSH远程主机
  --debug             调试模式
```

## 使用场景速查

| 场景 | 命令示例 |
|------|---------|
| 提供示例 | `python main.py -f examples.txt -c "创建类似脚本"` |
| 配置说明 | `python main.py -f proxy.md -c "配置代理"` |
| 项目文档 | `python main.py -f README.md -c "创建新模块"` |
| 多个文件 | `python main.py -f a.txt -f b.md -c "任务"` |
| SSH模式 | `python main.py --ssh-host user@host -f deploy.md -c "部署"` |
| 自适应模式 | `python main.py --adaptive -f req.md -c "检查依赖"` |

## 文件要求

- **格式**：文本文件（.txt, .md, .json, .yaml, .sh, .py等）
- **大小**：单个文件 ≤ 1MB（可配置）
- **数量**：最多5个文件（可配置）
- **编码**：UTF-8（自动尝试其他编码）

## 配置选项

在 `.env` 文件中：

```bash
MAX_CONTEXT_FILE_SIZE=1048576  # 1MB
MAX_CONTEXT_FILES=5            # 最多5个
CONTEXT_FILE_ENCODING=utf-8    # 默认编码
```

## 实现文件清单

需要修改/创建的文件：

1. ✅ **新建** `autoshell/context_file.py` - 核心模块
2. ✅ **修改** `autoshell/config.py` - 添加配置
3. ✅ **修改** `main.py` - 添加参数和处理逻辑
4. ✅ **修改** `autoshell/agent.py` - 集成上下文文件
5. ✅ **修改** `autoshell/llm.py` - 更新prompt
6. ✅ **修改** `.env.example` - 添加配置示例
7. ✅ **新建** `CONTEXT_FILE_USAGE.md` - 使用文档
8. ✅ **修改** `README.md` - 更新说明

## 核心代码片段

### 1. 读取文件

```python
from autoshell.context_file import ContextFileManager

# 读取单个文件
file_info = ContextFileManager.read_context_file("examples.txt")

# 读取多个文件
files = ContextFileManager.read_multiple_files(
    ["a.txt", "b.md"],
    max_size=1024*1024
)
```

### 2. 格式化上下文

```python
# 格式化为prompt字符串
context_string = ContextFileManager.format_context_string(files)
```

### 3. 传递给LLM

```python
# 在agent.py中
user_context = ContextFileManager.format_context_string(self.context_files)

# 在llm.py中
plan_data = self.llm.generate_plan(
    user_query,
    context_str,
    user_context=user_context
)
```

## 测试检查清单

- [ ] 单个文件读取
- [ ] 多个文件读取
- [ ] 文件不存在错误处理
- [ ] 文件过大错误处理
- [ ] 文件数量超限错误处理
- [ ] 编码错误处理
- [ ] 与本地模式集成
- [ ] 与SSH模式集成
- [ ] 与自适应模式集成
- [ ] 命令行参数解析
- [ ] 文档完整性

## 示例文件模板

### examples.txt
```
# 命令示例
ls -la
pwd
echo "Hello World"
```

### proxy-config.md
```markdown
# 代理配置

公司代理：
- HTTP: http://proxy.company.com:8080
- HTTPS: https://proxy.company.com:8080

环境变量：
- http_proxy
- https_proxy
- no_proxy
```

### requirements.md
```markdown
# 项目依赖

## Python包
- requests >= 2.28.0
- rich >= 13.0.0
- openai >= 1.0.0

## 系统工具
- git
- curl
- jq
```

## 常见错误和解决方案

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| 文件不存在 | 路径错误 | 检查文件路径，使用绝对路径 |
| 文件过大 | 超过1MB | 减小文件大小或增加配置限制 |
| 文件数量超限 | 超过5个 | 减少文件数量或增加配置限制 |
| 编码错误 | 非UTF-8编码 | 转换文件为UTF-8编码 |
| 无法读取 | 权限问题 | 检查文件读取权限 |

## 性能考虑

- **Token使用**：每个文件的内容都会添加到prompt中，注意token限制
- **读取时间**：多个大文件可能增加启动时间
- **缓存**：系统信息有缓存，但上下文文件每次都会读取

## 安全注意事项

⚠️ **不要在上下文文件中包含**：
- 密码、API密钥
- 个人敏感信息
- 生产环境凭证
- 私钥文件

✅ **可以包含**：
- 命令示例
- 配置模板
- 项目文档
- 编码规范
- 部署流程

## 下一步

实现完成后，可以考虑的增强功能：

1. **上下文模板**：预定义常用上下文
2. **智能摘要**：自动提取文件关键信息
3. **URL支持**：从网络读取上下文
4. **通配符**：支持 `*.md` 等模式
5. **交互式管理**：在交互模式中动态添加/移除文件

## 相关文档

- [设计文档](context-file-feature-design.md) - 详细设计说明
- [实现指南](context-file-implementation-guide.md) - 分步实现步骤
- [使用文档](../CONTEXT_FILE_USAGE.md) - 用户使用指南（实现后创建）

---

**文档版本**：v1.0  
**创建日期**：2026-01-22  
**状态**：规划完成，待实现
