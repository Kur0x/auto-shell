# AutoShell 自适应执行实现指南

## 概述

本文档提供了实现自适应执行功能的详细步骤和代码示例。

## 实施步骤

### 步骤 1：创建数据模型（1天）

#### 1.1 创建 `autoshell/adaptive/models.py`

```python
"""
自适应执行的数据模型
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ToolType(Enum):
    """工具类型枚举"""
    COMMAND = "execute_command"
    FILE_READ = "read_file"
    FILE_WRITE = "write_file"
    FILE_EDIT = "edit_file"
    CONDITION = "check_condition"


@dataclass
class Step:
    """执行步骤"""
    tool: str
    description: str
    parameters: Dict[str, Any]
    save_output_as: Optional[str] = None
    condition: Optional[str] = None
    
    def should_execute(self, context: 'ExecutionContext') -> bool:
        """判断是否应该执行此步骤"""
        if not self.condition:
            return True
        return context.evaluate_condition(self.condition)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "tool": self.tool,
            "description": self.description,
            "parameters": self.parameters,
            "save_output_as": self.save_output_as,
            "condition": self.condition
        }


@dataclass
class StepResult:
    """步骤执行结果"""
    step: Step
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典（用于上下文）"""
        return {
            "tool": self.step.tool,
            "description": self.step.description,
            "success": self.success,
            "output": str(self.output)[:500] if self.output else None,  # 限制长度
            "error": self.error
        }
    
    def get_summary(self) -> str:
        """获取结果摘要"""
        status = "✓" if self.success else "✗"
        output_preview = str(self.output)[:100] if self.output else ""
        return f"{status} {self.step.description}: {output_preview}"


@dataclass
class TaskPhase:
    """任务阶段"""
    phase: int
    goal: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    success_criteria: str = ""
    completed: bool = False
    steps_executed: List[StepResult] = field(default_factory=list)
    
    def mark_completed(self):
        """标记阶段完成"""
        self.completed = True
    
    def add_step_result(self, result: StepResult):
        """添加步骤结果"""
        self.steps_executed.append(result)
    
    def get_summary(self) -> str:
        """获取阶段摘要"""
        status = "✓" if self.completed else "⧗"
        return f"{status} Phase {self.phase}: {self.goal} ({len(self.steps_executed)} steps)"


@dataclass
class TaskPlan:
    """任务计划"""
    task_type: str
    complexity: str  # simple, medium, complex
    phases: List[TaskPhase]
    estimated_steps: int = 0
    potential_challenges: List[str] = field(default_factory=list)
    
    def get_current_phase(self) -> Optional[TaskPhase]:
        """获取当前阶段"""
        for phase in self.phases:
            if not phase.completed:
                return phase
        return None
    
    def is_completed(self) -> bool:
        """判断任务是否完成"""
        return all(phase.completed for phase in self.phases)
    
    def get_progress(self) -> float:
        """获取任务进度（0-1）"""
        if not self.phases:
            return 0.0
        completed = sum(1 for p in self.phases if p.completed)
        return completed / len(self.phases)
```

#### 1.2 创建 `autoshell/adaptive/__init__.py`

```python
"""
自适应执行模块
"""
from .models import Step, StepResult, TaskPhase, TaskPlan, ToolType
from .context import ExecutionContext
from .planner import TaskPlanner
from .generator import StepGenerator

__all__ = [
    'Step',
    'StepResult',
    'TaskPhase',
    'TaskPlan',
    'ToolType',
    'ExecutionContext',
    'TaskPlanner',
    'StepGenerator'
]
```

### 步骤 2：实现执行上下文（1天）

#### 2.1 创建 `autoshell/adaptive/context.py`

```python
"""
执行上下文管理
"""
from typing import Any, Dict, List, Optional
from .models import Step, StepResult
import json


class ExecutionContext:
    """执行上下文"""
    
    def __init__(self):
        self.history: List[StepResult] = []
        self.variables: Dict[str, Any] = {}
        self.files_accessed: Dict[str, str] = {}  # path -> last_operation
        self.max_history_length = 20  # 保留最近20步
    
    def add_step_result(self, result: StepResult):
        """添加步骤执行结果"""
        self.history.append(result)
        
        # 如果步骤指定了保存变量
        if result.step.save_output_as and result.success:
            self.set_variable(result.step.save_output_as, result.output)
        
        # 限制历史长度
        if len(self.history) > self.max_history_length:
            self.history = self.history[-self.max_history_length:]
    
    def get_variable(self, name: str) -> Any:
        """获取变量值"""
        return self.variables.get(name)
    
    def set_variable(self, name: str, value: Any):
        """设置变量值"""
        self.variables[name] = value
    
    def record_file_access(self, file_path: str, operation: str):
        """记录文件访问"""
        self.files_accessed[file_path] = operation
    
    def evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式"""
        try:
            # 创建安全的评估环境
            safe_dict = {
                'variables': self.variables,
                **self.variables  # 直接访问变量
            }
            
            # 评估条件
            result = eval(condition, {"__builtins__": {}}, safe_dict)
            return bool(result)
        except Exception as e:
            print(f"条件评估失败: {condition}, 错误: {e}")
            return False
    
    def get_context_summary(self, max_steps: int = 5) -> str:
        """获取上下文摘要（用于 LLM）"""
        parts = []
        
        # 最近的步骤
        if self.history:
            parts.append("## 最近执行的步骤:")
            recent_steps = self.history[-max_steps:]
            for i, result in enumerate(recent_steps, 1):
                parts.append(f"{i}. {result.get_summary()}")
        
        # 当前变量
        if self.variables:
            parts.append("\n## 上下文变量:")
            for name, value in self.variables.items():
                value_str = str(value)[:100]  # 限制长度
                parts.append(f"- {name} = {value_str}")
        
        # 访问的文件
        if self.files_accessed:
            parts.append("\n## 已访问的文件:")
            for path, op in self.files_accessed.items():
                parts.append(f"- {path} ({op})")
        
        return "\n".join(parts) if parts else "无执行历史"
    
    def get_last_output(self) -> Optional[Any]:
        """获取最后一步的输出"""
        if self.history:
            return self.history[-1].output
        return None
    
    def clear(self):
        """清空上下文"""
        self.history.clear()
        self.variables.clear()
        self.files_accessed.clear()
```

### 步骤 3：实现工具系统（3-4天）

#### 3.1 创建 `autoshell/tools/base.py`

```python
"""
工具基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """工具基类"""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
    
    @abstractmethod
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        pass
    
    def get_schema(self) -> Dict:
        """获取工具的参数模式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters_schema()
        }
    
    @abstractmethod
    def _get_parameters_schema(self) -> Dict:
        """获取参数模式"""
        pass
```

#### 3.2 创建 `autoshell/tools/command.py`

```python
"""
命令执行工具
"""
from typing import Optional
from .base import BaseTool, ToolResult
from ..executor import CommandExecutor


class CommandTool(BaseTool):
    """命令执行工具"""
    
    name = "execute_command"
    description = "Execute a shell command"
    
    def __init__(self, executor: CommandExecutor, ssh_config=None):
        self.executor = executor
        self.ssh_config = ssh_config
    
    def execute(self, command: str, cwd: Optional[str] = None) -> ToolResult:
        """执行命令"""
        try:
            result = self.executor.execute(
                command=command,
                cwd=cwd,
                ssh_config=self.ssh_config
            )
            
            if result["executed"] and result["return_code"] == 0:
                return ToolResult(
                    success=True,
                    output=result["stdout"]
                )
            else:
                return ToolResult(
                    success=False,
                    output=result.get("stdout", ""),
                    error=result.get("stderr", "Execution failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        return "command" in kwargs and isinstance(kwargs["command"], str)
    
    def _get_parameters_schema(self) -> Dict:
        """获取参数模式"""
        return {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
                "required": True
            },
            "cwd": {
                "type": "string",
                "description": "Working directory",
                "required": False
            }
        }
```

#### 3.3 创建 `autoshell/tools/file_read.py`

```python
"""
文件读取工具
"""
import os
from typing import Optional
from .base import BaseTool, ToolResult
from .safety import FileOperationSafety


class FileReadTool(BaseTool):
    """文件读取工具"""
    
    name = "read_file"
    description = "Read content from a file"
    
    def __init__(self, base_dir: str = None, ssh_config=None):
        self.base_dir = base_dir or os.path.expanduser("~")
        self.ssh_config = ssh_config
        self.safety = FileOperationSafety()
    
    def execute(
        self, 
        file_path: str, 
        encoding: str = "utf-8",
        max_lines: Optional[int] = None
    ) -> ToolResult:
        """读取文件内容"""
        try:
            # SSH 模式
            if self.ssh_config:
                return self._read_remote_file(file_path, encoding, max_lines)
            
            # 本地模式
            return self._read_local_file(file_path, encoding, max_lines)
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to read file: {str(e)}"
            )
    
    def _read_local_file(
        self, 
        file_path: str, 
        encoding: str,
        max_lines: Optional[int]
    ) -> ToolResult:
        """读取本地文件"""
        # 展开路径
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        
        # 安全检查
        if not self.safety.validate_path(abs_path, self.base_dir):
            return ToolResult(
                success=False,
                output=None,
                error=f"Access denied: {file_path}"
            )
        
        if not self.safety.validate_file_size(abs_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"File too large: {file_path}"
            )
        
        # 读取文件
        with open(abs_path, 'r', encoding=encoding) as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = ''.join(lines)
            else:
                content = f.read()
        
        return ToolResult(
            success=True,
            output=content
        )
    
    def _read_remote_file(
        self,
        file_path: str,
        encoding: str,
        max_lines: Optional[int]
    ) -> ToolResult:
        """读取远程文件（通过SSH）"""
        # 使用 cat 命令读取
        if max_lines:
            command = f"head -n {max_lines} {file_path}"
        else:
            command = f"cat {file_path}"
        
        # 导入 CommandTool 避免循环依赖
        from .command import CommandTool
        from ..executor import CommandExecutor
        
        cmd_tool = CommandTool(CommandExecutor, self.ssh_config)
        result = cmd_tool.execute(command=command)
        
        return result
    
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        return "file_path" in kwargs
    
    def _get_parameters_schema(self) -> Dict:
        """获取参数模式"""
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read",
                "required": True
            },
            "encoding": {
                "type": "string",
                "description": "File encoding (default: utf-8)",
                "required": False
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to read",
                "required": False
            }
        }
```

#### 3.4 创建 `autoshell/tools/file_write.py`

```python
"""
文件写入工具
"""
import os
from .base import BaseTool, ToolResult
from .safety import FileOperationSafety
from rich.console import Console
from rich.prompt import Confirm

console = Console()


class FileWriteTool(BaseTool):
    """文件写入工具"""
    
    name = "write_file"
    description = "Write content to a file"
    
    def __init__(
        self, 
        base_dir: str = None, 
        ssh_config=None,
        require_confirmation: bool = True
    ):
        self.base_dir = base_dir or os.path.expanduser("~")
        self.ssh_config = ssh_config
        self.require_confirmation = require_confirmation
        self.safety = FileOperationSafety()
    
    def execute(
        self,
        file_path: str,
        content: str,
        mode: str = "w",  # w: 覆盖, a: 追加
        encoding: str = "utf-8"
    ) -> ToolResult:
        """写入文件内容"""
        try:
            # SSH 模式
            if self.ssh_config:
                return self._write_remote_file(file_path, content, mode)
            
            # 本地模式
            return self._write_local_file(file_path, content, mode, encoding)
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to write file: {str(e)}"
            )
    
    def _write_local_file(
        self,
        file_path: str,
        content: str,
        mode: str,
        encoding: str
    ) -> ToolResult:
        """写入本地文件"""
        # 展开路径
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        
        # 安全检查
        if not self.safety.validate_path(abs_path, self.base_dir):
            return ToolResult(
                success=False,
                output=None,
                error=f"Access denied: {file_path}"
            )
        
        if not self.safety.validate_file_type(abs_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"File type not allowed: {file_path}"
            )
        
        # 用户确认
        if self.require_confirmation:
            action = "覆盖" if mode == "w" else "追加"
            if not Confirm.ask(f"确认{action}文件 {file_path}?", default=False):
                return ToolResult(
                    success=False,
                    output=None,
                    error="User cancelled operation"
                )
        
        # 确保目录存在
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        # 写入文件
        with open(abs_path, mode, encoding=encoding) as f:
            f.write(content)
        
        return ToolResult(
            success=True,
            output=f"Successfully wrote {len(content)} bytes to {file_path}"
        )
    
    def _write_remote_file(
        self,
        file_path: str,
        content: str,
        mode: str
    ) -> ToolResult:
        """写入远程文件（通过SSH）"""
        # 使用 echo 或 tee 命令写入
        # 转义内容中的特殊字符
        escaped_content = content.replace("'", "'\\''")
        
        if mode == "a":
            command = f"echo '{escaped_content}' >> {file_path}"
        else:
            command = f"echo '{escaped_content}' > {file_path}"
        
        from .command import CommandTool
        from ..executor import CommandExecutor
        
        cmd_tool = CommandTool(CommandExecutor, self.ssh_config)
        result = cmd_tool.execute(command=command)
        
        if result.success:
            return ToolResult(
                success=True,
                output=f"Successfully wrote to {file_path}"
            )
        else:
            return result
    
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        return "file_path" in kwargs and "content" in kwargs
    
    def _get_parameters_schema(self) -> Dict:
        """获取参数模式"""
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "Content to write",
                "required": True
            },
            "mode": {
                "type": "string",
                "description": "Write mode: 'w' (overwrite) or 'a' (append)",
                "required": False
            },
            "encoding": {
                "type": "string",
                "description": "File encoding (default: utf-8)",
                "required": False
            }
        }
```

#### 3.5 创建 `autoshell/tools/file_edit.py`

```python
"""
文件编辑工具
"""
import os
import re
from .base import BaseTool, ToolResult
from .file_read import FileReadTool
from .file_write import FileWriteTool


class FileEditTool(BaseTool):
    """文件编辑工具（搜索和替换）"""
    
    name = "edit_file"
    description = "Edit file using search and replace"
    
    def __init__(self, base_dir: str = None, ssh_config=None):
        self.base_dir = base_dir or os.path.expanduser("~")
        self.ssh_config = ssh_config
        self.read_tool = FileReadTool(base_dir, ssh_config)
        self.write_tool = FileWriteTool(base_dir, ssh_config)
    
    def execute(
        self,
        file_path: str,
        search_pattern: str,
        replacement: str,
        regex: bool = False,
        count: int = -1  # -1 表示替换所有
    ) -> ToolResult:
        """编辑文件内容"""
        try:
            # 读取文件
            read_result = self.read_tool.execute(file_path=file_path)
            if not read_result.success:
                return read_result
            
            content = read_result.output
            
            # 执行替换
            if regex:
                new_content, num_replacements = re.subn(
                    search_pattern,
                    replacement,
                    content,
                    count=count if count > 0 else 0
                )
            else:
                if count == -1:
                    new_content = content.replace(search_pattern, replacement)
                    num_replacements = content.count(search_pattern)
                else:
                    new_content = content.replace(search_pattern, replacement, count)
                    num_replacements = min(count, content.count(search_pattern))
            
            # 检查是否有变化
            if new_content == content:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Pattern not found: {search_pattern}"
                )
            
            # 写入文件
            write_result = self.write_tool.execute(
                file_path=file_path,
                content=new_content,
                mode="w"
            )
            
            if write_result.success:
                return ToolResult(
                    success=True,
                    output=f"Replaced {num_replacements} occurrence(s) in {file_path}"
                )
            else:
                return write_result
                
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to edit file: {str(e)}"
            )
    
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        required = ["file_path", "search_pattern", "replacement"]
        return all(k in kwargs for k in required)
    
    def _get_parameters_schema(self) -> Dict:
        """获取参数模式"""
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
                "required": True
            },
            "search_pattern": {
                "type": "string",
                "description": "Pattern to search for",
                "required": True
            },
            "replacement": {
                "type": "string",
                "description": "Replacement text",
                "required": True
            },
            "regex": {
                "type": "boolean",
                "description": "Use regex for pattern matching",
                "required": False
            },
            "count": {
                "type": "integer",
                "description": "Number of replacements (-1 for all)",
                "required": False
            }
        }
```

#### 3.6 创建 `autoshell/tools/condition.py`

```python
"""
条件判断工具
"""
from .base import BaseTool, ToolResult
from typing import Dict, Any


class ConditionTool(BaseTool):
    """条件判断工具"""
    
    name = "check_condition"
    description = "Evaluate a condition based on context"
    
    def execute(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> ToolResult:
        """评估条件"""
        try:
            # 创建安全的评估环境
            safe_dict = {
                **context,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool
            }
            
            # 评估条件
            result = eval(condition, {"__builtins__": {}}, safe_dict)
            
            return ToolResult(
                success=True,
                output=bool(result)
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=False,
                error=f"Failed to evaluate condition: {str(e)}"
            )
    
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        return "condition" in kwargs and "context" in kwargs
    
    def _get_parameters_schema(self) -> Dict:
        """获取参数模式"""
        return {
            "condition": {
                "type": "string",
                "description": "Condition expression to evaluate",
                "required": True
            },
            "context": {
                "type": "object",
                "description": "Context variables for evaluation",
                "required": True
            }
        }
```

#### 3.7 创建 `autoshell/tools/safety.py`

```python
"""
文件操作安全检查
"""
import os


class FileOperationSafety:
    """文件操作安全检查"""
    
    FORBIDDEN_PATHS = [
        "/etc", "/sys", "/proc", "/dev",
        "/boot", "/root", 
        "C:\\Windows", "C:\\System32",
        "/bin", "/sbin", "/usr/bin", "/usr/sbin"
    ]
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    ALLOWED_EXTENSIONS = [
        ".sh", ".bash", ".py", ".js", ".ts",
        ".txt", ".md", ".json", ".yaml", ".yml",
        ".conf", ".cfg", ".ini", ".toml",
        ".xml", ".html", ".css", ".sql",
        ".log", ".csv", ".env"
    ]
    
    def validate_path(self, file_path: str, base_dir: str) -> bool:
        """验证文件路径安全性"""
        try:
            # 解析绝对路径
            abs_path = os.path.abspath(file_path)
            abs_base = os.path.abspath(base_dir)
            
            # 检查是否在允许的基础目录内
            if not abs_path.startswith(abs_base):
                return False
            
            # 检查是否访问禁止目录
            for forbidden in self.FORBIDDEN_PATHS:
                if abs_path.startswith(forbidden):
                    return False
            
            # 检查路径遍历
            if ".." in file_path:
                return False
            
            return True
        except Exception:
            return False
    
    def validate_file_size(self, file_path: str) -> bool:
        """验证文件大小"""
        try:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                return size <= self.MAX_FILE_SIZE
            return True
        except Exception:
            return False
    
    def validate_file_type(self, file_path: str) -> bool:
        """验证文件类型"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            # 允许无扩展名的文件（如配置文件）
            if not ext:
                return True
            return ext in self.ALLOWED_EXTENSIONS
        except Exception:
            return False
```

#### 3.8 创建 `autoshell/tools/__init__.py`

```python
"""
工具系统
"""
from .base import BaseTool, ToolResult
from .command import CommandTool
from .file_read import FileReadTool
from .file_write import FileWriteTool
from .file_edit import FileEditTool
from .condition import ConditionTool
from .safety import FileOperationSafety

__all__ = [
    'BaseTool',
    'ToolResult',
    'CommandTool',
    'FileReadTool',
    'FileWriteTool',
    'FileEditTool',
    'ConditionTool',
    'FileOperationSafety'
]
```

### 步骤 4：实现任务规划器（2天）

#### 4.1 创建 `autoshell/adaptive/planner.py`

```python
"""
任务规划器
"""
import json
from typing import Dict, Optional
from rich.console import Console
from .models import TaskPlan, TaskPhase
from ..llm import LLMClient

console = Console()


class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.current_plan: Optional[TaskPlan] = None
    
    def analyze_task(self, user_query: str, context_str: str) -> TaskPlan:
        """分析任务并生成计划"""
        console.print("[dim]正在分析任务...[/dim]")
        
        prompt = self._build_planning_prompt(user_query, context_str)
        
        try:
            # 调用 LLM
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            plan_data = json.loads(self.llm._clean_json_response(content))
            
            # 构建 TaskPlan
            phases = [
                TaskPhase(
                    phase=p["phase"],
                    goal=p["goal"],
                    description=p["description"],
                    dependencies=p.get("dependencies", []),
                    success_criteria=p.get("success_criteria", "")
                )
                for p in plan_data["phases"]
            ]
            
            plan = TaskPlan(
                task_type=plan_data.get("task_type", "unknown"),
                complexity=plan_data.get("complexity", "medium"),
                phases=phases,
                estimated_steps=plan_data.get("estimated_steps", 0),
                potential_challenges=plan_data.get("potential_challenges", [])
            )
            
            self.current_plan = plan
            return plan
            
        except Exception as e:
            console.print(f"[red]任务规划失败: {e}[/red]")
            raise
    
    def should_continue(self) -> bool:
        """判断任务是否需要继续"""
        if not self.current_plan:
            return False
        return not self.current_plan.is_completed()
    
    def get_current_phase(self) -> Optional[TaskPhase]:
        """获取当前阶段"""
        if not self.current_plan:
            return None
        return self.current_plan.get_current_phase()
    
    def mark_phase_completed(self, phase: TaskPhase):
        """标记阶段完成"""
        phase.mark_completed()
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个智能任务规划助手。

你的职责是分析用户的复杂任务，并将其分解为清晰的执行阶段。

每个阶段应该：
1. 有明确的目标
2. 可以独立执行
3. 有清晰的成功标准
4. 考虑依赖关系

请以 JSON 格式返回计划。"""
    
    def _build_planning_prompt(self, user_query: str, context_str: str) -> str:
        """构建规划提示"""
        return f"""请分析以下任务并生成执行计划：

用户任务：{user_query}

执行环境：
{context_str}

请将任务分解为多个阶段，每个阶段包含：
- phase: 阶段编号
- goal: 阶段目标
- description: 详细描述
- dependencies: 依赖的前置阶段输出
- success_criteria: 成功标准

返回 JSON 格式：
{{
  "task_type": "任务类型",
  "complexity": "simple|medium|complex",
  "phases": [
    {{
      "phase": 1,
      "goal": "阶段目标",
      "description": "详细描述",
      "dependencies": [],
      "success_criteria": "成功标准"
    }}
  ],
  "estimated_steps": 估计步骤数,
  "potential_challenges": ["挑战1", "挑战2"]
}}"""
```

### 步骤 5：实现步骤生成器（2-3天）

#### 5.1 创建 `autoshell/adaptive/generator.py`

```python
"""
步骤生成器
"""
import json
from typing import List, Dict
from rich.console import Console
from .models import Step, TaskPhase
from .context import ExecutionContext
from ..llm import LLMClient

console = Console()


class StepGenerator:
    """步骤生成器"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.available_tools = [
            "execute_command",
            "read_file",
            "write_file",
            "edit_file",
            "check_condition"
        ]
    
    def generate_next_steps(
        self,
        phase: TaskPhase,
        context: ExecutionContext,
        max_steps: int = 3
    ) -> List[Step]:
        """生成接下来的步骤"""
        console.print(f"[dim]正在生成步骤（阶段 {phase.phase}: {phase.goal}）...[/dim]")
        
        prompt = self._build_generation_prompt(phase, context, max_steps)
        
        try:
            # 调用 LLM
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            content = response.choices[0].message.content
            steps_data = json.loads(self.llm._clean_json_response(content))
            
            # 构建 Step 对象
            steps = [
                Step(
                    tool=s["tool"],
                    description=s["description"],
                    parameters=s["parameters"],
                    save_output_as=s.get("save_output_as"),
                    condition=s.get("condition")
                )
                for s in steps_data["steps"]
            ]
            
            return steps
            
        except Exception as e:
            console.print(f"[red]步骤生成失败: {e}[/red]")
            raise
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return f"""你是一个智能步骤生成助手，可以使用以下工具：

可用工具：
1. execute_command - 执行 shell 命令
   参数: command (必需), cwd (可选)

2. read_file - 读取文件内容
   参数: file_path (必需), encoding (可选), max_lines (可选)

3. write_file - 写入文件内容
   参数: file_path (必需), content (必需), mode (可选: w/a), encoding (可选)

4. edit_file - 编辑文件（搜索替换）
   参数: file_path (必需), search_pattern (必需), replacement (必需), regex (可选), count (可选)

5. check_condition - 条件判断
   参数: condition (必需), context (必需)

你的职责：
1. 根据当前阶段目标生成1-3个步骤
2. 选择合适的工具
3. 考虑执行历史和上下文
4. 处理条件分支
5. 提供清晰的描述

返回 JSON 格式：
{{
  "reasoning": "你的思考过程",
  "steps": [
    {{
      "tool": "工具名称",
      "description": "步骤描述",
      "parameters": {{}},
      "save_output_as": "变量名（可选）",
      "condition": "执行条件（可选）"
    }}
  ],
  "expected_outcome": "预期结果"
}}"""
    
    def _build_generation_prompt(
        self,
        phase: TaskPhase,
        context: ExecutionContext,
        max_steps: int
    ) -> str:
        """构建生成提示"""
        context_summary = context.get_context_summary()
        
        return f"""当前阶段目标：{phase.goal}
阶段描述：{phase.description}
成功标准：{phase.success_criteria}

{context_summary}

请生成接下来的 {max_steps} 个步骤（或更少，如果阶段即将完成）。

注意：
1. 每个步骤必须指定工具和参数
2. 如果需要保存输出供后续使用，设置 save_output_as
3. 如果步骤有执行条件，设置 condition
4. 考虑已执行的步骤，避免重复

返回 JSON 格式的步骤列表。"""
```

### 步骤 6：集成到 Agent（2天）

#### 6.1 修改 `autoshell/agent.py`

在现有的 `AutoShellAgent` 类中添加自适应执行模式：

```python
# 在 AutoShellAgent 类中添加

def run_adaptive(self, user_query: str):
    """自适应执行模式"""
    from .adaptive import TaskPlanner, StepGenerator, ExecutionContext
    from .tools import (
        CommandTool, FileReadTool, FileWriteTool,
        FileEditTool, ConditionTool
    )
    
    # 初始化组件
    planner = TaskPlanner(self.llm)
    generator = StepGenerator(self.llm)
    context = ExecutionContext()
    
    # 初始化工具
    tools = {
        "execute_command": CommandTool(self.executor, self.ssh_config),
        "read_file": FileReadTool(ssh_config=self.ssh_config),
        "write_file": FileWriteTool(ssh_config=self.ssh_config),
        "edit_file": FileEditTool(ssh_config=self.ssh_config),
        "check_condition": ConditionTool()
    }
    
    # 生成任务计划
    context_str = ContextManager.get_context_string()
    plan = planner.analyze_task(user_query, context_str)
    
    # 显示计划
    self._print_task_plan(plan)
    
    # 执行循环
    max_iterations = 50
    iteration = 0
    
    while planner.should_continue() and iteration < max_iterations:
        iteration += 1
        
        # 获取当前阶段
        phase = planner.get_current_phase()
        if not phase:
            break
        
        console.print(f"\n[bold cyan]阶段 {phase.phase}: {phase.goal}[/bold cyan]")
        
        # 生成步骤
        try:
            steps = generator.generate_next_steps(phase, context, max_steps=3)
        except Exception as e:
            console.print(f"[red]步骤生成失败: {e}[/red]")
            break
        
        # 执行步骤
        all_success = True
        for step in steps:
            # 检查条件
            if not step.should_execute(context):
                console.print(f"[yellow]跳过步骤（条件不满足）: {step.description}[/yellow]")
                continue
            
            console.print(f"\n[bold]执行: {step.description}[/bold]")
            console.print(f"[dim]工具: {step.tool}[/dim]")
            
            # 执行工具
            tool = tools.get(step.tool)
            if not tool:
                console.print(f"[red]未知工具: {step.tool}[/red]")
                all_success = False
                break
            
            result = tool.execute(**step.parameters)
            
            # 创建步骤结果
            from .adaptive.models import StepResult
            step_result = StepResult(
                step=step,
                success=result.success,
                output=result.output,
                error=result.error
            )
            
            # 更新上下文
            context.add_step_result(step_result)
            phase.add_step_result(step_result)
            
            # 显示结果
            if result.success:
                console.print(f"[green]✓ 成功[/green]")
                if result.output:
                    output_str = str(result.output)[:200]
                    console.print(f"[dim]输出: {output_str}[/dim]")
            else:
                console.print(f"[red]✗ 失败: {result.error}[/red]")
                all_success = False
                break
        
        # 检查阶段是否完成
        if all_success:
            # 询问 LLM 阶段是否完成
            if self._check_phase_completion(phase, context):
                planner.mark_phase_completed(phase)
                console.print(f"[green]✓ 阶段 {phase.phase} 完成[/green]")
    
    # 任务完成
    if plan.is_completed():
        console.print("\n[bold green]✓ 任务完成！[/bold green]")
    else:
        console.print("\n[yellow]任务未完全完成[/yellow]")
    
    # 显示摘要
    self._print_execution_summary(plan, context)

def _print_task_plan(self, plan: TaskPlan):
    """显示任务计划"""
    from rich.table import Table
    
    table = Table(title="任务计划", show_header=True)
    table.add_column("阶段", style="cyan")
    table.add_column("目标", style="green")
    table.add_column("描述")
    
    for phase in plan.phases:
        table.add_row(
            str(phase.phase),
            phase.goal,
            phase.description
        )
    
    console.print(table)

def _check_phase_completion(self, phase: TaskPhase, context: ExecutionContext) -> bool:
    """检查阶段是否完成"""
    # 简单实现：如果有成功标准，检查是否满足
    # 更复杂的实现可以询问 LLM
    if not phase.success_criteria:
        return True
    
    # 这里可以实现更智能的检查逻辑
    return len(phase.steps_executed) > 0

def _print_execution_summary(self, plan: TaskPlan, context: ExecutionContext):
    """显示执行摘要"""
    console.print("\n[bold]执行摘要:[/bold]")
    console.print(f"任务类型: {plan.task_type}")
    console.print(f"复杂度: {plan.complexity}")
    console.print(f"完成阶段: {sum(1 for p in plan.phases if p.completed)}/{len(plan.phases)}")
    console.print(f"总步骤数: {len(context.history)}")
```

### 步骤 7：修改配置和入口（1天）

#### 7.1 修改 `autoshell/config.py`

```python
# 添加自适应执行配置
ADAPTIVE_MODE = os.getenv("ADAPTIVE_MODE", "false").lower() == "true"
MAX_EXECUTION_STEPS = int(os.getenv("MAX_EXECUTION_STEPS", "50"))
STEP_GENERATION_BATCH = int(os.getenv("STEP_GENERATION_BATCH", "3"))
ENABLE_FILE_OPERATIONS = os.getenv("ENABLE_FILE_OPERATIONS", "true").lower() == "true"
FILE_OPERATION_BASE_DIR = os.getenv("FILE_OPERATION_BASE_DIR", os.path.expanduser("~"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
```

#### 7.2 修改 `main.py`

```python
# 在 main() 函数中添加模式选择

# 一次性执行模式
if args.command:
    # 检查是否启用自适应模式
    if Config.ADAPTIVE_MODE:
        agent.run_adaptive(args.command)
    else:
        agent.run(args.command)
    return
```

### 步骤 8：测试（3-4天）

创建测试文件 `tests/test_adaptive.py`：

```python
"""
自适应执行测试
"""
import pytest
from autoshell.adaptive import ExecutionContext, TaskPlanner, StepGenerator
from autoshell.adaptive.models import Step, StepResult
from autoshell.tools import CommandTool, FileReadTool, ConditionTool


def test_execution_context():
    """测试执行上下文"""
    context = ExecutionContext()
    
    # 设置变量
    context.set_variable("test_var", "value")
    assert context.get_variable("test_var") == "value"
    
    # 评估条件
    assert context.evaluate_condition("test_var == 'value'")
    assert not context.evaluate_condition("test_var == 'other'")


def test_step_execution():
    """测试步骤执行"""
    step = Step(
        tool="execute_command",
        description="测试命令",
        parameters={"command": "echo hello"}
    )
    
    # 测试条件执行
    context = ExecutionContext()
    assert step.should_execute(context)  # 无条件，应该执行
    
    step_with_condition = Step(
        tool="execute_command",
        description="条件命令",
        parameters={"command": "echo test"},
        condition="test_var == 'yes'"
    )
    
    assert not step_with_condition.should_execute(context)  # 条件不满足
    
    context.set_variable("test_var", "yes")
    assert step_with_condition.should_execute(context)  # 条件满足


def test_file_operations():
    """测试文件操作"""
    # 这里添加文件操作的测试
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## 总结

本实现指南提供了完整的代码框架和实施步骤。关键点：

1. **模块化设计**：清晰的模块划分，易于维护
2. **工具系统**：可扩展的工具架构
3. **安全机制**：文件操作的安全检查
4. **渐进式执行**：根据反馈动态调整
5. **完整测试**：确保功能正确性

实施完成后，AutoShell 将具备强大的自适应执行能力，能够处理复杂的多步骤任务。
