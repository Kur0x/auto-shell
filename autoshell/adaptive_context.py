"""
自适应执行的上下文管理模块
提供增强的执行历史、变量管理和状态追踪
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class ExecutionStep:
    """执行步骤记录"""
    description: str
    command: str
    output: str
    success: bool
    status: StepStatus = StepStatus.SUCCESS
    error_message: Optional[str] = None
    retry_count: int = 0
    execution_time: float = 0.0
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_summary(self, max_output_len: int = 200) -> str:
        """获取步骤摘要"""
        status_icon = "✓" if self.success else "✗"
        output_preview = self.output[:max_output_len] if self.output else ""
        if len(self.output) > max_output_len:
            output_preview += "..."
        
        summary = f"{status_icon} {self.description}"
        if output_preview:
            summary += f"\n   Output: {output_preview}"
        if self.error_message:
            summary += f"\n   Error: {self.error_message}"
        
        return summary
    
    def extract_key_info(self) -> Dict[str, Any]:
        """从输出中提取关键信息"""
        if not self.output:
            return {}
        
        extracted = {}
        
        # 提取数字
        numbers = re.findall(r'\b\d+\.?\d*\b', self.output)
        if numbers:
            extracted['numbers'] = numbers[:5]  # 最多保留5个
        
        # 提取路径
        paths = re.findall(r'[/~][\w/.-]+', self.output)
        if paths:
            extracted['paths'] = paths[:5]
        
        # 提取IP地址
        ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', self.output)
        if ips:
            extracted['ips'] = ips
        
        # 提取状态关键词
        status_keywords = ['success', 'failed', 'error', 'warning', 'complete', 'running']
        found_keywords = [kw for kw in status_keywords if kw.lower() in self.output.lower()]
        if found_keywords:
            extracted['status_keywords'] = found_keywords
        
        self.extracted_data = extracted
        return extracted


@dataclass
class TaskPhase:
    """任务阶段"""
    phase_id: int
    name: str
    goal: str
    status: StepStatus = StepStatus.PENDING
    steps: List[ExecutionStep] = field(default_factory=list)
    dependencies: List[int] = field(default_factory=list)  # 依赖的阶段ID
    success_criteria: Optional[str] = None
    max_retries: int = 3
    
    def add_step(self, step: ExecutionStep):
        """添加步骤"""
        self.steps.append(step)
    
    def is_complete(self) -> bool:
        """判断阶段是否完成"""
        if not self.steps:
            return False
        return self.status == StepStatus.SUCCESS
    
    def has_failed(self) -> bool:
        """判断阶段是否失败"""
        return self.status == StepStatus.FAILED
    
    def get_summary(self) -> str:
        """获取阶段摘要"""
        status_icons = {
            StepStatus.PENDING: "⧗",
            StepStatus.RUNNING: "▶",
            StepStatus.SUCCESS: "✓",
            StepStatus.FAILED: "✗",
            StepStatus.SKIPPED: "⊘"
        }
        icon = status_icons.get(self.status, "?")
        return f"{icon} Phase {self.phase_id}: {self.name} ({len(self.steps)} steps)"


class AdaptiveExecutionContext:
    """自适应执行上下文管理器"""
    
    def __init__(self, max_history_length: int = 50):
        self.phases: List[TaskPhase] = []
        self.current_phase: Optional[TaskPhase] = None
        self.variables: Dict[str, Any] = {}
        self.max_history_length = max_history_length
        self.total_steps = 0
        self.successful_steps = 0
        self.failed_steps = 0
        
    def create_phase(
        self,
        phase_id: int,
        name: str,
        goal: str,
        dependencies: Optional[List[int]] = None,
        success_criteria: Optional[str] = None
    ) -> TaskPhase:
        """创建新阶段"""
        phase = TaskPhase(
            phase_id=phase_id,
            name=name,
            goal=goal,
            dependencies=dependencies or [],
            success_criteria=success_criteria
        )
        self.phases.append(phase)
        return phase
    
    def set_current_phase(self, phase: TaskPhase):
        """设置当前阶段"""
        self.current_phase = phase
        phase.status = StepStatus.RUNNING
    
    def add_step_to_current_phase(self, step: ExecutionStep):
        """添加步骤到当前阶段"""
        if not self.current_phase:
            raise ValueError("No current phase set")
        
        self.current_phase.add_step(step)
        self.total_steps += 1
        
        if step.success:
            self.successful_steps += 1
        else:
            self.failed_steps += 1
        
        # 提取关键信息
        step.extract_key_info()
    
    def complete_current_phase(self, success: bool = True):
        """完成当前阶段"""
        if self.current_phase:
            self.current_phase.status = StepStatus.SUCCESS if success else StepStatus.FAILED
    
    def get_all_steps(self) -> List[ExecutionStep]:
        """获取所有步骤"""
        all_steps = []
        for phase in self.phases:
            all_steps.extend(phase.steps)
        return all_steps
    
    def get_recent_steps(self, count: int = 10) -> List[ExecutionStep]:
        """获取最近的步骤"""
        all_steps = self.get_all_steps()
        return all_steps[-count:] if all_steps else []
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式"""
        try:
            # 创建安全的评估环境
            safe_dict = {
                **self.variables,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'any': any,
                'all': all
            }
            
            # 评估条件
            result = eval(condition, {"__builtins__": {}}, safe_dict)
            return bool(result)
        except Exception as e:
            print(f"条件评估失败: {condition}, 错误: {e}")
            return False
    
    def get_context_summary(self, max_steps: int = 5, include_phases: bool = True) -> str:
        """获取上下文摘要（用于传递给 LLM）"""
        parts = []
        
        # 阶段摘要
        if include_phases and self.phases:
            parts.append("## 任务阶段:")
            for phase in self.phases:
                parts.append(f"  {phase.get_summary()}")
        
        # 最近的步骤
        recent_steps = self.get_recent_steps(max_steps)
        if recent_steps:
            parts.append("\n## 最近执行的步骤:")
            for i, step in enumerate(recent_steps, 1):
                parts.append(f"{i}. {step.get_summary()}")
        
        # 当前变量
        if self.variables:
            parts.append("\n## 上下文变量:")
            for name, value in list(self.variables.items())[:10]:  # 最多显示10个
                value_str = str(value)[:100]  # 限制长度
                parts.append(f"  - {name} = {value_str}")
        
        # 统计信息
        parts.append(f"\n## 执行统计:")
        parts.append(f"  - 总步骤数: {self.total_steps}")
        parts.append(f"  - 成功: {self.successful_steps}")
        parts.append(f"  - 失败: {self.failed_steps}")
        
        return "\n".join(parts) if parts else "无执行历史"
    
    def get_last_output(self) -> Optional[str]:
        """获取最后一步的输出"""
        recent = self.get_recent_steps(1)
        return recent[0].output if recent else None
    
    def get_last_error(self) -> Optional[Tuple[str, str]]:
        """获取最后一个错误（命令，错误信息）"""
        all_steps = self.get_all_steps()
        for step in reversed(all_steps):
            if not step.success and step.error_message:
                return (step.command, step.error_message)
        return None
    
    def has_recent_failures(self, count: int = 3) -> bool:
        """检查最近是否有连续失败"""
        recent = self.get_recent_steps(count)
        if len(recent) < count:
            return False
        return all(not step.success for step in recent)
    
    def get_phase_by_id(self, phase_id: int) -> Optional[TaskPhase]:
        """根据ID获取阶段"""
        for phase in self.phases:
            if phase.phase_id == phase_id:
                return phase
        return None
    
    def can_start_phase(self, phase: TaskPhase) -> bool:
        """检查阶段是否可以开始（依赖是否满足）"""
        if not phase.dependencies:
            return True
        
        for dep_id in phase.dependencies:
            dep_phase = self.get_phase_by_id(dep_id)
            if not dep_phase or not dep_phase.is_complete():
                return False
        
        return True
    
    def get_next_phase(self) -> Optional[TaskPhase]:
        """获取下一个可执行的阶段"""
        for phase in self.phases:
            if phase.status == StepStatus.PENDING and self.can_start_phase(phase):
                return phase
        return None
    
    def clear(self):
        """清空上下文"""
        self.phases.clear()
        self.current_phase = None
        self.variables.clear()
        self.total_steps = 0
        self.successful_steps = 0
        self.failed_steps = 0
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）"""
        return {
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "name": p.name,
                    "goal": p.goal,
                    "status": p.status.value,
                    "steps_count": len(p.steps)
                }
                for p in self.phases
            ],
            "variables": self.variables,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps
        }
