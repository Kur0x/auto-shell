# 上下文文件功能实现指南

本文档提供上下文文件功能的详细实现步骤。

## 实现步骤概览

1. 创建上下文文件管理模块 (`autoshell/context_file.py`)
2. 更新配置模块 (`autoshell/config.py`)
3. 扩展命令行参数 (`main.py`)
4. 修改Agent类 (`autoshell/agent.py`)
5. 修改LLM客户端 (`autoshell/llm.py`)
6. 更新文档和配置示例
7. 测试功能

---

## 步骤1：创建上下文文件管理模块

创建文件：`autoshell/context_file.py`

```python
import os
from pathlib import Path
from rich.console import Console

console = Console()

class ContextFileManager:
    """管理用户提供的上下文文件"""
    
    # 支持的文本文件扩展名
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.json', '.yaml', '.yml',
        '.sh', '.bash', '.py', '.js', '.ts',
        '.conf', '.cfg', '.ini', '.toml',
        '.xml', '.html', '.css', '.sql',
        '.log', '.env', '.gitignore'
    }
    
    @staticmethod
    def validate_file(filepath: str, max_size: int) -> tuple:
        """
        验证文件是否存在、可读、大小合理
        
        :param filepath: 文件路径
        :param max_size: 最大文件大小（字节）
        :return: (is_valid: bool, error_message: str or None)
        """
        try:
            path = Path(filepath)
            
            # 检查文件是否存在
            if not path.exists():
                return False, f"文件不存在: {filepath}"
            
            # 检查是否为文件（不是目录）
            if not path.is_file():
                return False, f"路径不是文件: {filepath}"
            
            # 检查文件大小
            file_size = path.stat().st_size
            if file_size > max_size:
                size_mb = file_size / (1024 * 1024)
                max_mb = max_size / (1024 * 1024)
                return False, f"文件过大: {size_mb:.2f}MB (最大: {max_mb:.2f}MB)"
            
            # 检查文件是否可读
            if not os.access(filepath, os.R_OK):
                return False, f"文件不可读: {filepath}"
            
            # 检查文件扩展名（可选警告）
            if path.suffix.lower() not in ContextFileManager.SUPPORTED_EXTENSIONS:
                console.print(f"[yellow]警告: 文件扩展名 '{path.suffix}' 可能不是文本文件[/yellow]")
            
            return True, None
            
        except Exception as e:
            return False, f"验证文件时出错: {str(e)}"
    
    @staticmethod
    def read_context_file(filepath: str) -> dict:
        """
        读取单个上下文文件
        
        :param filepath: 文件路径
        :return: {
            'filepath': str,
            'filename': str,
            'content': str,
            'size': int,
            'error': str or None
        }
        """
        result = {
            'filepath': filepath,
            'filename': Path(filepath).name,
            'content': '',
            'size': 0,
            'error': None
        }
        
        try:
            path = Path(filepath)
            result['size'] = path.stat().st_size
            
            # 尝试多种编码读取
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                result['error'] = "无法使用支持的编码读取文件"
                return result
            
            result['content'] = content
            
        except Exception as e:
            result['error'] = f"读取文件时出错: {str(e)}"
        
        return result
    
    @staticmethod
    def read_multiple_files(filepaths: list, max_size: int) -> list:
        """
        读取多个上下文文件
        
        :param filepaths: 文件路径列表
        :param max_size: 单个文件最大大小
        :return: 文件信息列表
        """
        results = []
        
        for filepath in filepaths:
            # 验证文件
            is_valid, error_msg = ContextFileManager.validate_file(filepath, max_size)
            
            if not is_valid:
                console.print(f"[bold red]错误:[/bold red] {error_msg}")
                continue
            
            # 读取文件
            file_info = ContextFileManager.read_context_file(filepath)
            
            if file_info['error']:
                console.print(f"[bold red]错误:[/bold red] {file_info['error']}")
                continue
            
            results.append(file_info)
        
        return results
    
    @staticmethod
    def format_context_string(context_files: list) -> str:
        """
        将上下文文件格式化为prompt字符串
        
        :param context_files: 文件信息列表
        :return: 格式化的字符串
        """
        if not context_files:
            return ""
        
        lines = ["\n=== User Provided Context Files ===\n"]
        lines.append("The user has provided the following context files for reference:\n")
        
        for file_info in context_files:
            filename = file_info['filename']
            content = file_info['content']
            size = file_info['size']
            
            lines.append(f"\n--- File: {filename} (Size: {size} bytes) ---")
            lines.append(content)
            lines.append(f"--- End of {filename} ---\n")
        
        lines.append("\nPlease consider the information in these context files when generating commands.")
        lines.append("The context may include:")
        lines.append("- Examples to follow")
        lines.append("- Configuration requirements")
        lines.append("- Environment setup instructions")
        lines.append("- Coding standards or conventions")
        lines.append("- Project-specific information")
        lines.append("- Proxy settings or network configuration")
        lines.append("=== End of User Context ===\n")
        
        return "\n".join(lines)
    
    @staticmethod
    def display_file_summary(context_files: list):
        """
        显示上下文文件摘要
        
        :param context_files: 文件信息列表
        """
        if not context_files:
            return
        
        console.print(f"\n[bold cyan]已加载 {len(context_files)} 个上下文文件:[/bold cyan]")
        
        for i, file_info in enumerate(context_files, 1):
            filename = file_info['filename']
            size = file_info['size']
            lines = len(file_info['content'].splitlines())
            
            size_kb = size / 1024
            console.print(f"  {i}. [green]{filename}[/green] - {size_kb:.2f}KB, {lines} 行")
        
        console.print()
```

---

## 步骤2：更新配置模块

修改文件：`autoshell/config.py`

在 `Config` 类中添加以下配置项：

```python
# 上下文文件配置
MAX_CONTEXT_FILE_SIZE = int(os.getenv("MAX_CONTEXT_FILE_SIZE", 1048576))  # 1MB
MAX_CONTEXT_FILES = int(os.getenv("MAX_CONTEXT_FILES", 5))
CONTEXT_FILE_ENCODING = os.getenv("CONTEXT_FILE_ENCODING", "utf-8")
```

---

## 步骤3：扩展命令行参数

修改文件：`main.py`

在 `parse_args()` 函数中添加参数：

```python
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AutoShell - Intelligent Command Line Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 交互模式（本地）
  python main.py
  
  # 一次性执行（本地）
  python main.py -c "列出当前目录下的所有文件"
  
  # 使用上下文文件
  python main.py -f examples.txt -c "创建类似的脚本"
  
  # 使用多个上下文文件
  python main.py -f config.md -f examples.txt -c "配置环境"
  
  # 自适应执行模式（根据输出动态调整）
  python main.py --adaptive -c "执行test.sh，如果输出为1则修改为2"
  
  # SSH模式 + 上下文文件
  python main.py --ssh-host user@example.com -f deploy.md -c "部署应用"
        """
    )
    
    # 一次性执行参数
    parser.add_argument(
        '-c', '--command',
        type=str,
        help='一次性执行命令后退出（非交互模式）'
    )
    
    # 上下文文件参数（新增）
    parser.add_argument(
        '-f', '--context-file',
        type=str,
        action='append',
        dest='context_files',
        help='提供上下文文件（可多次使用）'
    )
    
    # SSH相关参数
    parser.add_argument(
        '--ssh-host',
        type=str,
        help='SSH远程主机（格式：user@host）'
    )
    
    # ... 其他参数保持不变 ...
    
    return parser.parse_args()
```

在 `main()` 函数中处理上下文文件：

```python
def main():
    try:
        args = parse_args()
        
        # 设置全局DEBUG标志
        Config.DEBUG = args.debug
        
        # 处理上下文文件（新增）
        context_files_data = []
        if args.context_files:
            from autoshell.context_file import ContextFileManager
            
            # 检查文件数量限制
            if len(args.context_files) > Config.MAX_CONTEXT_FILES:
                console.print(f"[bold red]错误:[/bold red] 上下文文件数量超过限制 (最多 {Config.MAX_CONTEXT_FILES} 个)")
                sys.exit(1)
            
            # 读取上下文文件
            with console.status("[bold green]正在读取上下文文件...[/bold green]", spinner="dots"):
                context_files_data = ContextFileManager.read_multiple_files(
                    args.context_files,
                    Config.MAX_CONTEXT_FILE_SIZE
                )
            
            # 检查是否成功读取任何文件
            if not context_files_data:
                console.print("[bold red]错误:[/bold red] 无法读取任何上下文文件")
                sys.exit(1)
            
            # 显示文件摘要
            ContextFileManager.display_file_summary(context_files_data)
        
        # 判断是否为SSH模式
        ssh_config = None
        if args.ssh_host:
            # ... SSH配置代码保持不变 ...
        
        # 初始化Agent（传递上下文文件）
        try:
            agent = AutoShellAgent(
                ssh_config=ssh_config,
                context_files=context_files_data  # 新增参数
            )
        except ConnectionError as e:
            # ... 错误处理保持不变 ...
        
        # ... 其余代码保持不变 ...
```

---

## 步骤4：修改Agent类

修改文件：`autoshell/agent.py`

更新 `__init__` 方法：

```python
class AutoShellAgent:
    def __init__(self, ssh_config=None, context_files=None):
        """
        初始化AutoShell Agent
        
        :param ssh_config: SSH配置字典，包含host, port, password, key_filename等
        :param context_files: 用户提供的上下文文件列表
        """
        self.llm = LLMClient()
        self.max_retries = Config.MAX_RETRIES
        self.ssh_config = ssh_config
        self.context_files = context_files or []  # 新增
        
        # 系统信息缓存
        self._system_info_cache = None
        self._cache_timestamp = None
        self._cache_ttl = Config.SYSTEM_INFO_CACHE_TTL
        
        # 初始化时收集系统信息
        if Config.COLLECT_DETAILED_INFO:
            self._initialize_system_info()
```

更新 `run` 方法：

```python
def run(self, user_query: str):
    """
    处理单个用户请求的完整生命周期：
    Context -> LLM (Plan) -> Loop (Execute Steps) -> (Retry Step if fail) -> Output
    """
    error_history = []
    
    # ... 现有代码保持不变 ...
    
    # 1. Generate Plan (Context Aware) - 使用增强的上下文信息
    system_info = self._get_system_info()
    
    if self.ssh_config:
        # SSH模式：使用远程系统信息
        context_str = SSHContextManager.format_remote_context(system_info)
    else:
        # 本地模式：使用本地系统信息
        context_str = ContextManager.get_enhanced_context_string(system_info)
    
    context_str += f"\n- Virtual Session CWD: {session_cwd}"
    
    # 添加用户上下文（新增）
    user_context = ""
    if self.context_files:
        from .context_file import ContextFileManager
        user_context = ContextFileManager.format_context_string(self.context_files)

    # 尝试生成计划
    try:
        with console.status("[bold green]Generating plan...[/bold green]", spinner="dots"):
            plan_data = self.llm.generate_plan(
                user_query, 
                context_str,
                user_context=user_context  # 新增参数
            )
    except Exception as e:
        console.print(f"[bold red]Planning Error:[/bold red] {str(e)}")
        return
    
    # ... 其余代码保持不变 ...
```

同样更新 `run_adaptive` 方法（如果存在）：

```python
def run_adaptive(self, user_query: str):
    """自适应执行模式"""
    # ... 现有代码 ...
    
    # 添加用户上下文
    user_context = ""
    if self.context_files:
        from .context_file import ContextFileManager
        user_context = ContextFileManager.format_context_string(self.context_files)
    
    # 在调用 generate_next_steps 时传递 user_context
    # ... 其余代码 ...
```

---

## 步骤5：修改LLM客户端

修改文件：`autoshell/llm.py`

更新 `generate_plan` 方法签名和实现：

```python
def generate_plan(self, user_query: str, context_str: str, error_history: list | None = None, user_context: str = "") -> dict:
    """
    根据用户查询和环境上下文生成 Shell 命令计划。
    
    :param user_query: 用户的自然语言指令
    :param context_str: 格式化后的系统环境信息
    :param error_history: 之前的错误历史，用于重试/自愈逻辑
    :param user_context: 用户提供的上下文文件内容（新增）
    :return: 解析后的 JSON 字典 {"thought": ..., "steps": [{"description":..., "command":...}, ...]}
    """
    
    if Config.DEBUG:
        console.print(f"[dim][DEBUG] Starting plan generation for query: {user_query[:50]}...[/dim]")
    start_time = time.time()
    
    system_prompt = f"""
You are an expert system engineer and command-line wizard.
Your goal is to translate natural language instructions into a SERIES of precise, efficient, and safe Shell commands.

Current Execution Environment:
{context_str}

{user_context}

⚠️ IMPORTANT: Pay special attention to the system information above!
- For Ubuntu/Debian systems (apt): use apt or apt-get commands
- For CentOS/RHEL systems (yum/dnf): use yum (CentOS 7 and earlier) or dnf (CentOS 8+)
# ... 其余prompt保持不变 ...
"""
    
    # ... 其余代码保持不变 ...
```

如果有 `generate_next_steps` 方法（自适应模式），也需要类似更新。

---

## 步骤6：更新文档和配置示例

### 6.1 更新 `.env.example`

添加以下配置：

```bash
# ========== 上下文文件配置 ==========
# 单个上下文文件最大大小（字节），默认1MB
MAX_CONTEXT_FILE_SIZE=1048576

# 最多支持的上下文文件数量
MAX_CONTEXT_FILES=5

# 上下文文件默认编码
CONTEXT_FILE_ENCODING=utf-8
```

### 6.2 创建使用文档

创建文件：`CONTEXT_FILE_USAGE.md`

```markdown
# 上下文文件使用指南

## 功能介绍

上下文文件功能允许您向AutoShell提供额外的文本文件作为上下文信息，使LLM能够更好地理解您的需求并生成更精准的命令。

## 使用方法

### 基本用法

```bash
# 使用单个上下文文件
python main.py -f examples.txt -c "创建类似的脚本"

# 使用多个上下文文件
python main.py -f config.md -f examples.txt -c "配置环境"
```

### 结合其他模式

```bash
# 自适应模式 + 上下文文件
python main.py --adaptive -f requirements.md -c "检查并安装依赖"

# SSH模式 + 上下文文件
python main.py --ssh-host user@server -f deploy.md -c "部署应用"
```

## 使用场景

### 1. 提供示例

创建 `examples.txt`：
\`\`\`
# 示例：创建Python虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

使用：
\`\`\`bash
python main.py -f examples.txt -c "为我的项目创建虚拟环境"
\`\`\`

### 2. 配置说明

创建 `proxy-config.md`：
\`\`\`markdown
# 代理配置

公司代理服务器：
- HTTP: http://proxy.company.com:8080
- HTTPS: https://proxy.company.com:8080
\`\`\`

使用：
\`\`\`bash
python main.py -f proxy-config.md -c "配置系统代理"
\`\`\`

### 3. 项目文档

\`\`\`bash
python main.py -f README.md -f CONTRIBUTING.md -c "创建新的功能模块"
\`\`\`

## 支持的文件格式

- 文本文件：`.txt`
- Markdown：`.md`
- 配置文件：`.json`, `.yaml`, `.yml`, `.conf`, `.cfg`, `.ini`
- 脚本文件：`.sh`, `.bash`, `.py`, `.js`
- 其他文本格式

## 限制

- 单个文件最大：1MB（可配置）
- 最多文件数：5个（可配置）
- 仅支持文本文件

## 配置

在 `.env` 文件中配置：

\`\`\`bash
MAX_CONTEXT_FILE_SIZE=1048576  # 1MB
MAX_CONTEXT_FILES=5
\`\`\`

## 注意事项

1. **敏感信息**：不要在上下文文件中包含密码、密钥等敏感信息
2. **文件大小**：过大的文件可能导致token超限
3. **文件编码**：建议使用UTF-8编码
4. **路径**：使用绝对路径或相对于当前目录的路径
```

### 6.3 更新 `README.md`

在"核心特性"部分添加：

```markdown
✅ **上下文文件支持** - 提供文本文件作为上下文，让AI更好地理解需求
```

在"基本使用"部分添加：

```markdown
#### 5. 使用上下文文件

```bash
# 单个上下文文件
python main.py -f examples.txt -c "创建类似的脚本"

# 多个上下文文件
python main.py -f config.md -f examples.txt -c "配置环境"

# 结合其他模式
python main.py --adaptive -f requirements.md -c "检查并安装依赖"
```

详细文档：[CONTEXT_FILE_USAGE.md](CONTEXT_FILE_USAGE.md)
\`\`\`

---

## 步骤7：测试功能

### 7.1 创建测试文件

创建 `test_context_file.py`：

```python
#!/usr/bin/env python3
"""测试上下文文件功能"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from autoshell.context_file import ContextFileManager
from autoshell.config import Config

def test_validate_file():
    """测试文件验证"""
    print("测试文件验证...")
    
    # 创建测试文件
    test_file = "test_context.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("这是一个测试文件\n")
    
    # 测试有效文件
    is_valid, error = ContextFileManager.validate_file(test_file, 1024*1024)
    assert is_valid, f"验证失败: {error}"
    print("✓ 有效文件验证通过")
    
    # 测试不存在的文件
    is_valid, error = ContextFileManager.validate_file("nonexistent.txt", 1024*1024)
    assert not is_valid, "应该检测到文件不存在"
    print("✓ 不存在文件检测通过")
    
    # 清理
    os.remove(test_file)
    print()

def test_read_file():
    """测试文件读取"""
    print("测试文件读取...")
    
    # 创建测试文件
    test_file = "test_context.txt"
    test_content = "这是测试内容\n包含中文\n"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    # 读取文件
    result = ContextFileManager.read_context_file(test_file)
    assert result['error'] is None, f"读取失败: {result['error']}"
    assert result['content'] == test_content, "内容不匹配"
    print("✓ 文件读取通过")
    
    # 清理
    os.remove(test_file)
    print()

def test_format_context():
    """测试格式化"""
    print("测试上下文格式化...")
    
    files = [
        {
            'filename': 'test1.txt',
            'content': 'Content 1',
            'size': 9
        },
        {
            'filename': 'test2.txt',
            'content': 'Content 2',
            'size': 9
        }
    ]
    
    formatted = ContextFileManager.format_context_string(files)
    assert 'test1.txt' in formatted, "应包含文件名"
    assert 'Content 1' in formatted, "应包含文件内容"
    print("✓ 格式化通过")
    print()

def main():
    """运行所有测试"""
    print("=" * 50)
    print("上下文文件功能测试")
    print("=" * 50)
    print()
    
    try:
        test_validate_file()
        test_read_file()
        test_format_context()
        
        print("=" * 50)
        print("所有测试通过！✓")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 7.2 手动测试场景

创建测试文件 `test_examples.txt`：

```
# 示例命令
ls -la
pwd
echo "Hello World"
```

运行测试：

```bash
# 测试1：基本功能
python main.py -f test_examples.txt -c "执行类似的命令"

# 测试2：多个文件
python main.py -f test_examples.txt -f README.md -c "列出项目信息"

# 测试3：结合自适应模式
python main.py --adaptive -f test_examples.txt -c "检查当前目录"

# 测试4：错误处理
python main.py -f nonexistent.txt -c "测试"  # 应该显示错误

# 测试5：文件过大
# 创建一个超过1MB的文件并测试
```

---

## 实现检查清单

完成实现后，检查以下项目：

- [ ] `autoshell/context_file.py` 已创建并实现所有方法
- [ ] `autoshell/config.py` 已添加配置项
- [ ] `main.py` 已添加命令行参数和处理逻辑
- [ ] `autoshell/agent.py` 已更新接收和使用上下文文件
- [ ] `autoshell/llm.py` 已更新prompt构建逻辑
- [ ] `.env.example` 已添加新配置项
- [ ] `CONTEXT_FILE_USAGE.md` 已创建
- [ ] `README.md` 已更新
- [ ] 测试脚本已创建并通过
- [ ] 手动测试场景已验证

---

## 常见问题

### Q: 如何处理大文件？

A: 当前设计限制单个文件最大1MB。如果需要处理更大的文件，可以：
1. 增加 `MAX_CONTEXT_FILE_SIZE` 配置
2. 实现文件内容截断功能
3. 只读取文件的前N行

### Q: 如何支持二进制文件？

A: 当前设计只支持文本文件。如果需要支持二进制文件（如图片），需要：
1. 实现文件类型检测
2. 对二进制文件进行base64编码
3. 修改prompt以处理编码后的内容

### Q: 如何优化token使用？

A: 可以实现以下优化：
1. 智能摘要：只提取文件的关键部分
2. 压缩空白：移除多余的空行和空格
3. 条件包含：根据任务类型选择性包含文件内容

---

## 总结

按照本指南的步骤实现后，AutoShell将支持：
- 通过 `-f` 参数提供上下文文件
- 支持多个文件
- 自动验证和读取文件
- 将文件内容集成到LLM prompt中
- 与现有功能（SSH、自适应模式）无缝集成

实现完成后，用户可以更灵活地向AutoShell提供上下文信息，提高命令生成的准确性和相关性。
```

---

## 实现完成后的验证

1. 运行单元测试：`python test_context_file.py`
2. 运行集成测试：使用各种场景测试
3. 检查文档完整性
4. 验证错误处理
5. 测试边界情况

祝实现顺利！
