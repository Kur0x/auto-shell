"""
错误恢复和重试机制模块
提供智能的错误分类、恢复策略和重试逻辑
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re
from rich.console import Console

console = Console()


class ErrorType(Enum):
    """错误类型分类"""
    COMMAND_NOT_FOUND = "command_not_found"
    PERMISSION_DENIED = "permission_denied"
    FILE_NOT_FOUND = "file_not_found"
    NETWORK_ERROR = "network_error"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    LOGIC_ERROR = "logic_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY_WITH_SUDO = "retry_with_sudo"
    RETRY_WITH_DIFFERENT_COMMAND = "retry_with_different_command"
    SKIP_AND_CONTINUE = "skip_and_continue"
    ASK_LLM_FOR_FIX = "ask_llm_for_fix"
    ABORT = "abort"
    RETRY_SAME = "retry_same"


@dataclass
class ErrorAnalysis:
    """错误分析结果"""
    error_type: ErrorType
    error_message: str
    command: str
    suggested_strategy: RecoveryStrategy
    retry_command: Optional[str] = None
    explanation: str = ""
    can_recover: bool = True


class ErrorClassifier:
    """错误分类器 - 分析错误类型"""
    
    # 错误模式匹配规则
    ERROR_PATTERNS = {
        ErrorType.COMMAND_NOT_FOUND: [
            r"command not found",
            r"not found",
            r"is not recognized",
            r"No such file or directory.*bin",
        ],
        ErrorType.PERMISSION_DENIED: [
            r"permission denied",
            r"access denied",
            r"operation not permitted",
            r"insufficient privileges",
            r"must be root",
            r"requires root",
        ],
        ErrorType.FILE_NOT_FOUND: [
            r"no such file or directory",
            r"cannot find",
            r"does not exist",
            r"file not found",
        ],
        ErrorType.NETWORK_ERROR: [
            r"connection refused",
            r"network unreachable",
            r"timeout",
            r"could not resolve host",
            r"connection timed out",
        ],
        ErrorType.SYNTAX_ERROR: [
            r"syntax error",
            r"unexpected token",
            r"invalid syntax",
            r"parse error",
        ],
        ErrorType.RESOURCE_UNAVAILABLE: [
            r"no space left",
            r"out of memory",
            r"resource temporarily unavailable",
            r"too many open files",
        ],
    }
    
    @classmethod
    def classify(cls, error_message: str, command: str) -> ErrorType:
        """分类错误类型"""
        error_lower = error_message.lower()
        
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return error_type
        
        return ErrorType.UNKNOWN
    
    @classmethod
    def analyze(cls, error_message: str, command: str, return_code: int) -> ErrorAnalysis:
        """分析错误并提供恢复建议"""
        error_type = cls.classify(error_message, command)
        
        # 根据错误类型确定恢复策略
        if error_type == ErrorType.PERMISSION_DENIED:
            # 权限错误：尝试使用 sudo
            if not command.strip().startswith("sudo"):
                return ErrorAnalysis(
                    error_type=error_type,
                    error_message=error_message,
                    command=command,
                    suggested_strategy=RecoveryStrategy.RETRY_WITH_SUDO,
                    retry_command=f"sudo {command}",
                    explanation="权限不足，尝试使用 sudo 重试",
                    can_recover=True
                )
            else:
                return ErrorAnalysis(
                    error_type=error_type,
                    error_message=error_message,
                    command=command,
                    suggested_strategy=RecoveryStrategy.ASK_LLM_FOR_FIX,
                    explanation="即使使用 sudo 仍然权限不足，需要 LLM 分析",
                    can_recover=True
                )
        
        elif error_type == ErrorType.COMMAND_NOT_FOUND:
            # 命令不存在：让 LLM 提供替代命令
            return ErrorAnalysis(
                error_type=error_type,
                error_message=error_message,
                command=command,
                suggested_strategy=RecoveryStrategy.ASK_LLM_FOR_FIX,
                explanation="命令不存在，需要 LLM 提供替代方案",
                can_recover=True
            )
        
        elif error_type == ErrorType.FILE_NOT_FOUND:
            # 文件不存在：让 LLM 分析路径或创建文件
            return ErrorAnalysis(
                error_type=error_type,
                error_message=error_message,
                command=command,
                suggested_strategy=RecoveryStrategy.ASK_LLM_FOR_FIX,
                explanation="文件不存在，需要 LLM 分析路径或创建文件",
                can_recover=True
            )
        
        elif error_type == ErrorType.NETWORK_ERROR:
            # 网络错误：可以重试
            return ErrorAnalysis(
                error_type=error_type,
                error_message=error_message,
                command=command,
                suggested_strategy=RecoveryStrategy.RETRY_SAME,
                retry_command=command,
                explanation="网络错误，可以重试",
                can_recover=True
            )
        
        elif error_type == ErrorType.SYNTAX_ERROR:
            # 语法错误：让 LLM 修复
            return ErrorAnalysis(
                error_type=error_type,
                error_message=error_message,
                command=command,
                suggested_strategy=RecoveryStrategy.ASK_LLM_FOR_FIX,
                explanation="命令语法错误，需要 LLM 修复",
                can_recover=True
            )
        
        elif error_type == ErrorType.RESOURCE_UNAVAILABLE:
            # 资源不可用：可能无法恢复
            return ErrorAnalysis(
                error_type=error_type,
                error_message=error_message,
                command=command,
                suggested_strategy=RecoveryStrategy.ABORT,
                explanation="系统资源不足，建议中止任务",
                can_recover=False
            )
        
        else:
            # 未知错误：让 LLM 分析
            return ErrorAnalysis(
                error_type=error_type,
                error_message=error_message,
                command=command,
                suggested_strategy=RecoveryStrategy.ASK_LLM_FOR_FIX,
                explanation="未知错误，需要 LLM 分析",
                can_recover=True
            )


class RetryManager:
    """重试管理器 - 管理重试逻辑和策略"""
    
    def __init__(self, max_retries: int = 3, max_consecutive_failures: int = 5):
        self.max_retries = max_retries
        self.max_consecutive_failures = max_consecutive_failures
        self.retry_counts: Dict[str, int] = {}  # 命令 -> 重试次数
        self.consecutive_failures = 0
    
    def can_retry(self, command: str) -> bool:
        """检查是否可以重试"""
        current_retries = self.retry_counts.get(command, 0)
        return current_retries < self.max_retries
    
    def record_retry(self, command: str):
        """记录重试"""
        self.retry_counts[command] = self.retry_counts.get(command, 0) + 1
    
    def record_failure(self):
        """记录失败"""
        self.consecutive_failures += 1
    
    def record_success(self):
        """记录成功"""
        self.consecutive_failures = 0
    
    def should_abort(self) -> bool:
        """检查是否应该中止"""
        return self.consecutive_failures >= self.max_consecutive_failures
    
    def get_retry_count(self, command: str) -> int:
        """获取重试次数"""
        return self.retry_counts.get(command, 0)
    
    def reset(self):
        """重置状态"""
        self.retry_counts.clear()
        self.consecutive_failures = 0


class ErrorRecoveryManager:
    """错误恢复管理器 - 协调错误分析和恢复"""
    
    def __init__(self, max_retries: int = 3):
        self.classifier = ErrorClassifier()
        self.retry_manager = RetryManager(max_retries=max_retries)
    
    def analyze_error(
        self,
        command: str,
        error_message: str,
        return_code: int
    ) -> ErrorAnalysis:
        """分析错误"""
        return self.classifier.analyze(error_message, command, return_code)
    
    def should_retry(
        self,
        command: str,
        error_analysis: ErrorAnalysis
    ) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该重试
        
        :return: (是否重试, 重试命令)
        """
        # 检查是否达到最大连续失败次数
        if self.retry_manager.should_abort():
            console.print("[red]达到最大连续失败次数，建议中止任务[/red]")
            return False, None
        
        # 检查错误是否可恢复
        if not error_analysis.can_recover:
            console.print(f"[red]错误不可恢复: {error_analysis.explanation}[/red]")
            return False, None
        
        # 检查是否达到最大重试次数
        if not self.retry_manager.can_retry(command):
            console.print(f"[yellow]命令已达到最大重试次数 ({self.retry_manager.max_retries})[/yellow]")
            return False, None
        
        # 根据恢复策略决定
        strategy = error_analysis.suggested_strategy
        
        if strategy == RecoveryStrategy.RETRY_WITH_SUDO:
            self.retry_manager.record_retry(command)
            return True, error_analysis.retry_command
        
        elif strategy == RecoveryStrategy.RETRY_SAME:
            self.retry_manager.record_retry(command)
            return True, command
        
        elif strategy == RecoveryStrategy.ASK_LLM_FOR_FIX:
            # 需要 LLM 介入
            return True, None  # None 表示需要 LLM 生成新命令
        
        elif strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
            return False, None
        
        elif strategy == RecoveryStrategy.ABORT:
            return False, None
        
        else:
            return False, None
    
    def record_execution_result(self, success: bool):
        """记录执行结果"""
        if success:
            self.retry_manager.record_success()
        else:
            self.retry_manager.record_failure()
    
    def get_recovery_prompt(self, error_analysis: ErrorAnalysis) -> str:
        """生成用于 LLM 的恢复提示"""
        return f"""上一步执行失败，需要修复：

错误类型: {error_analysis.error_type.value}
失败命令: {error_analysis.command}
错误信息: {error_analysis.error_message}
分析: {error_analysis.explanation}

请分析错误原因并生成修复后的命令。考虑以下几点：
1. 是否需要使用不同的命令或工具
2. 是否需要调整参数或路径
3. 是否需要先执行其他准备步骤
4. 是否需要检查系统环境或依赖

生成新的步骤来解决这个问题。"""
    
    def reset(self):
        """重置状态"""
        self.retry_manager.reset()
