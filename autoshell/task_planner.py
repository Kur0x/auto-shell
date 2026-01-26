"""
任务规划器模块
负责将复杂任务分解为多个阶段，并管理阶段依赖关系
"""
from typing import Dict, List, Optional
import json
from rich.console import Console
from rich.table import Table

from .adaptive_context import AdaptiveExecutionContext, TaskPhase, StepStatus
from .llm import LLMClient

console = Console()


class TaskPlanner:
    """任务规划器 - 将复杂任务分解为阶段"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.context: Optional[AdaptiveExecutionContext] = None
    
    def analyze_and_plan(
        self,
        user_goal: str,
        system_context: str,
        user_context: str = ""
    ) -> AdaptiveExecutionContext:
        """
        分析用户目标并生成任务计划
        
        :param user_goal: 用户的总体目标
        :param system_context: 系统环境信息
        :param user_context: 用户提供的上下文
        :return: 包含任务阶段的执行上下文
        """
        console.print("[dim]正在分析任务并生成执行计划...[/dim]")
        
        # 创建执行上下文
        self.context = AdaptiveExecutionContext()
        
        # 调用 LLM 生成任务计划
        plan_data = self._generate_task_plan(user_goal, system_context, user_context)
        
        # 解析计划并创建阶段
        self._create_phases_from_plan(plan_data)
        
        # 显示计划
        self._display_plan()
        
        return self.context
    
    def _generate_task_plan(
        self,
        user_goal: str,
        system_context: str,
        user_context: str
    ) -> Dict:
        """调用 LLM 生成任务计划"""
        
        system_prompt = f"""你是一个智能任务规划助手。

你的职责是分析用户的复杂任务，并将其分解为清晰的执行阶段。

当前执行环境：
{system_context}

{user_context}

任务分解原则：
1. 将复杂任务分解为 2-5 个逻辑阶段
2. 每个阶段应该有明确的目标和成功标准
3. 考虑阶段之间的依赖关系
4. 每个阶段应该是可独立验证的
5. 阶段应该按照逻辑顺序排列

你必须返回 JSON 格式的计划：
{{
  "task_analysis": "对任务的分析和理解",
  "complexity": "simple|medium|complex",
  "estimated_steps": 估计的总步骤数,
  "phases": [
    {{
      "phase_id": 1,
      "name": "阶段名称",
      "goal": "阶段目标",
      "description": "详细描述",
      "dependencies": [],
      "success_criteria": "成功标准"
    }}
  ],
  "potential_challenges": ["可能的挑战1", "可能的挑战2"]
}}

注意：
- phase_id 从 1 开始递增
- dependencies 是依赖的阶段 ID 列表（如果阶段 3 依赖阶段 1，则 dependencies: [1]）
- success_criteria 描述如何判断阶段成功完成
"""

        user_message = f"""用户目标：{user_goal}

请分析这个任务并生成执行计划。将任务分解为合理的阶段，每个阶段都有明确的目标。

返回 JSON 格式的计划。"""

        try:
            # 调用 LLM
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty response")
            cleaned_content = self.llm._clean_json_response(content)
            plan_data = json.loads(cleaned_content)
            
            return plan_data
            
        except Exception as e:
            console.print(f"[red]任务规划失败: {e}[/red]")
            # 返回默认的单阶段计划
            return {
                "task_analysis": "无法生成详细计划，将作为单阶段任务执行",
                "complexity": "simple",
                "estimated_steps": 5,
                "phases": [
                    {
                        "phase_id": 1,
                        "name": "执行任务",
                        "goal": user_goal,
                        "description": "执行用户请求的任务",
                        "dependencies": [],
                        "success_criteria": "任务完成"
                    }
                ],
                "potential_challenges": []
            }
    
    def _create_phases_from_plan(self, plan_data: Dict):
        """从计划数据创建任务阶段"""
        if not self.context:
            return
        
        phases_data = plan_data.get("phases", [])
        
        for phase_data in phases_data:
            phase = self.context.create_phase(
                phase_id=phase_data.get("phase_id", 1),
                name=phase_data.get("name", "未命名阶段"),
                goal=phase_data.get("goal", ""),
                dependencies=phase_data.get("dependencies", []),
                success_criteria=phase_data.get("success_criteria")
            )
    
    def _display_plan(self):
        """显示任务计划"""
        if not self.context or not self.context.phases:
            return
        
        table = Table(title="任务执行计划", show_header=True, header_style="bold magenta")
        table.add_column("阶段", style="cyan", width=6)
        table.add_column("名称", style="green", width=20)
        table.add_column("目标", width=40)
        table.add_column("依赖", style="yellow", width=10)
        
        for phase in self.context.phases:
            deps_str = ", ".join(str(d) for d in phase.dependencies) if phase.dependencies else "-"
            table.add_row(
                str(phase.phase_id),
                phase.name,
                phase.goal,
                deps_str
            )
        
        console.print(table)
    
    def get_next_executable_phase(self) -> Optional[TaskPhase]:
        """获取下一个可执行的阶段"""
        if not self.context:
            return None
        return self.context.get_next_phase()
    
    def is_plan_complete(self) -> bool:
        """检查计划是否全部完成"""
        if not self.context:
            return False
        return all(phase.is_complete() for phase in self.context.phases)
    
    def has_failed_phases(self) -> bool:
        """检查是否有失败的阶段"""
        if not self.context:
            return False
        return any(phase.has_failed() for phase in self.context.phases)
    
    def get_progress(self) -> float:
        """获取任务进度（0-1）"""
        if not self.context or not self.context.phases:
            return 0.0
        
        completed = sum(1 for p in self.context.phases if p.is_complete())
        return completed / len(self.context.phases)
    
    def display_progress(self):
        """显示任务进度"""
        if not self.context:
            return
        
        console.print("\n[bold]任务进度:[/bold]")
        for phase in self.context.phases:
            console.print(f"  {phase.get_summary()}")
        
        progress = self.get_progress()
        console.print(f"\n总体进度: {progress*100:.0f}%")
