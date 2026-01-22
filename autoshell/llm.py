import json
import re
import time
from openai import OpenAI
from rich.console import Console
from .config import Config

console = Console()

class LLMClient:
    def __init__(self):
        Config.validate()
        
        # 检测提供商类型
        self.is_ollama = Config.is_ollama()
        provider_name = "Ollama (Local)" if self.is_ollama else "OpenAI Compatible"
        
        console.print(f"[dim][DEBUG] Initializing LLM Client...[/dim]")
        console.print(f"[dim][DEBUG] Provider: {provider_name}[/dim]")
        console.print(f"[dim][DEBUG] API Base URL: {Config.OPENAI_BASE_URL}[/dim]")
        console.print(f"[dim][DEBUG] Model: {Config.LLM_MODEL}[/dim]")
        
        # 安全显示API Key（如果存在且不是 Ollama）
        if not self.is_ollama and Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != "not-needed":
            masked_key = f"{Config.OPENAI_API_KEY[:10]}...{Config.OPENAI_API_KEY[-4:]}"
            console.print(f"[dim][DEBUG] API Key: {masked_key}[/dim]")
        
        try:
            self.client = OpenAI(
                api_key=Config.OPENAI_API_KEY,
                base_url=Config.OPENAI_BASE_URL,
                timeout=30.0  # 添加30秒超时
            )
            console.print(f"[dim][DEBUG] Client initialized successfully[/dim]")
        except Exception as e:
            console.print(f"[bold red][DEBUG] Failed to initialize client: {str(e)}[/bold red]")
            raise
        
        self.model = Config.LLM_MODEL

    def _clean_json_response(self, content: str) -> str:
        """
        清理 LLM 可能返回的 Markdown 代码块标记，提取纯 JSON 字符串。
        支持多种格式的响应。
        """
        content = content.strip()
        
        # 1. 移除 ```json ... ``` 或 ``` ... ``` 包裹
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            content = match.group(1).strip()
        
        # 2. 提取第一个完整的JSON对象 {...}
        # 使用更精确的方法：找到第一个{，然后匹配对应的}
        first_brace = content.find('{')
        if first_brace == -1:
            return content
        
        # 从第一个{开始，计数括号来找到匹配的}
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(first_brace, len(content)):
            char = content[i]
            
            # 处理字符串中的引号
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            # 只在非字符串中计数括号
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # 找到匹配的}，提取完整的JSON对象
                        return content[first_brace:i+1]
        
        # 如果没有找到匹配的}，返回从第一个{到最后一个}
        last_brace = content.rfind('}')
        if last_brace > first_brace:
            return content[first_brace:last_brace+1]
        
        return content.strip()

    def generate_plan(self, user_query: str, context_str: str, error_history: list | None = None) -> dict:
        """
        根据用户查询和环境上下文生成 Shell 命令计划。
        
        :param user_query: 用户的自然语言指令
        :param context_str: 格式化后的系统环境信息
        :param error_history: 之前的错误历史，用于重试/自愈逻辑
        :return: 解析后的 JSON 字典 {"thought": ..., "steps": [{"description":..., "command":...}, ...]}
        """
        
        console.print(f"[dim][DEBUG] Starting plan generation for query: {user_query[:50]}...[/dim]")
        start_time = time.time()
        
        system_prompt = f"""
You are an expert system engineer and command-line wizard.
Your goal is to translate natural language instructions into a SERIES of precise, efficient, and safe Shell commands.

Current Execution Environment:
{context_str}

⚠️ CRITICAL JSON FORMAT REQUIREMENTS ⚠️

YOU MUST RESPOND WITH **ONLY** A VALID JSON OBJECT IN THIS **EXACT** FORMAT:

{{
   "thought": "Brief explanation of the plan",
   "steps": [
      {{
         "description": "Step description",
         "command": "shell command"
      }}
   ]
}}

🚫 FORBIDDEN:
- NO text before or after the JSON
- NO markdown code blocks (no ```)
- NO explanations outside the JSON
- NO conversational text
- NO other JSON structures (like {{"type":"shell"}} or {{"args":[]}})

✅ REQUIRED FIELDS:
- "thought": string - Your reasoning (required)
- "steps": array - List of command steps (required, must have at least 1 step)
  - Each step MUST have:
    - "description": string - What this step does
    - "command": string - The shell command to execute

📋 EXAMPLES:

Example 1 - Simple command "show current directory":
{{
   "thought": "Execute pwd command to show current working directory",
   "steps": [
      {{
         "description": "Display current directory",
         "command": "pwd"
      }}
   ]
}}

Example 2 - Multiple steps "list files and count them":
{{
   "thought": "First list all files, then count the number of files",
   "steps": [
      {{
         "description": "List all files in current directory",
         "command": "ls -la"
      }},
      {{
         "description": "Count number of files",
         "command": "ls -1 | wc -l"
      }}
   ]
}}

🔧 EXECUTION RULES:
1. Analyze the user's request based on the current OS and Shell
2. Break down the task into sequential logical steps
3. For each step, formulate a valid shell command for the detected Shell type
4. Use Windows commands (like 'dir', 'cd') for Windows/PowerShell
5. Use Unix commands (like 'ls', 'pwd') for Unix/Linux/Mac
6. 'cd' commands will be handled specially by the execution engine

⚠️ REMEMBER: Output ONLY the JSON object - absolutely nothing else!
"""

        user_message = f"""User Request: {user_query}

IMPORTANT: You MUST respond with ONLY a JSON object in this exact format:
{{
   "thought": "your reasoning here",
   "steps": [
      {{"description": "step description", "command": "shell command"}}
   ]
}}

Do NOT include any other text, explanations, or markdown. ONLY the JSON object."""

        if error_history:
            # error_history 结构: [{"step_index": int, "command": str, "error": str}, ...]
            error_context = "\n".join([f"Previous failure at step {e.get('step_index', '?')}:\nCommand: {e['command']}\nError: {e['error']}" for e in error_history])
            user_message += f"\n\nPREVIOUS EXECUTION FAILED. Please analyze the errors and provide a FIXED plan (you can adjust the remaining steps):\n{error_context}"

        raw_content = None  # 初始化变量以避免未绑定警告
        
        try:
            console.print(f"[dim][DEBUG] Calling LLM API with model: {self.model}[/dim]")
            
            # 构建API调用参数
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
            }
            
            # 处理 JSON 模式
            response = None
            
            if self.is_ollama:
                # Ollama: 不使用 JSON 模式，依赖 prompt engineering
                console.print(f"[dim][DEBUG] Using Ollama, relying on prompt for JSON output[/dim]")
                response = self.client.chat.completions.create(**api_params)
            else:
                # 非 Ollama: 尝试使用 JSON 模式
                json_mode_failed = False
                
                try:
                    api_params["response_format"] = {"type": "json_object"}
                    console.print(f"[dim][DEBUG] Attempting to enable JSON mode for model: {self.model}[/dim]")
                    response = self.client.chat.completions.create(**api_params)
                except Exception as e:
                    error_msg = str(e)
                    if "response_format" in error_msg or "400" in error_msg:
                        console.print(f"[dim][DEBUG] JSON mode not supported by this API, retrying without it...[/dim]")
                        json_mode_failed = True
                    else:
                        # 其他错误，直接抛出
                        raise
                
                # 如果JSON模式失败，重试不带JSON模式
                if json_mode_failed:
                    api_params.pop("response_format", None)
                    console.print(f"[dim][DEBUG] Calling API without JSON mode...[/dim]")
                    response = self.client.chat.completions.create(**api_params)
            
            elapsed = time.time() - start_time
            console.print(f"[dim][DEBUG] LLM API responded in {elapsed:.2f}s[/dim]")
            
            # 确保response不为None
            if response is None:
                raise RuntimeError("API call succeeded but response is None")
            
            raw_content = response.choices[0].message.content
            
            if not raw_content:
                console.print(f"[bold red][DEBUG] WARNING: LLM returned None or empty content![/bold red]")
                raise ValueError("LLM returned empty response")
            
            # 只在出错时显示详细日志
            # console.print(f"[dim][DEBUG] Raw response: {raw_content[:200]}...[/dim]")
            
            cleaned_content = self._clean_json_response(raw_content)
            
            result = json.loads(cleaned_content)
            # console.print(f"[dim][DEBUG] Successfully parsed JSON with {len(result.get('steps', []))} steps[/dim]")
            
            # 验证JSON格式是否符合预期
            if not isinstance(result, dict):
                console.print(f"[bold red][ERROR] LLM returned invalid format: Expected dict, got {type(result)}[/bold red]")
                console.print(f"[yellow]Raw response:[/yellow]\n{raw_content}")
                raise ValueError(f"LLM returned invalid format: Expected dict, got {type(result)}")
            
            if "steps" not in result:
                console.print(f"[bold red][ERROR] LLM returned JSON without 'steps' field![/bold red]")
                console.print(f"[yellow]Received JSON structure:[/yellow] {list(result.keys())}")
                console.print(f"[yellow]Full response:[/yellow]\n{raw_content}")
                raise ValueError(f"LLM returned JSON without required 'steps' field. Got keys: {list(result.keys())}")
            
            if not isinstance(result.get("steps"), list):
                console.print(f"[bold red][ERROR] 'steps' field is not a list![/bold red]")
                console.print(f"[yellow]Full response:[/yellow]\n{raw_content}")
                raise ValueError(f"'steps' field must be a list, got {type(result.get('steps'))}")
            
            if len(result.get("steps", [])) == 0:
                console.print(f"[bold red][ERROR] LLM returned empty 'steps' list![/bold red]")
                console.print(f"[yellow]Full response:[/yellow]\n{raw_content}")
                raise ValueError("LLM returned empty 'steps' list")
            
            # 验证每个step的格式
            for i, step in enumerate(result["steps"]):
                if not isinstance(step, dict):
                    console.print(f"[bold red][ERROR] Step {i+1} is not a dict![/bold red]")
                    raise ValueError(f"Step {i+1} must be a dict, got {type(step)}")
                if "command" not in step:
                    console.print(f"[bold red][ERROR] Step {i+1} missing 'command' field![/bold red]")
                    console.print(f"[yellow]Step content:[/yellow] {step}")
                    raise ValueError(f"Step {i+1} missing required 'command' field")
            
            return result
            
        except json.JSONDecodeError as e:
            console.print(f"[bold red][DEBUG] JSON Parse Error: {str(e)}[/bold red]")
            console.print(f"[dim][DEBUG] Raw content: {raw_content or 'N/A'}[/dim]")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            elapsed = time.time() - start_time
            console.print(f"[bold red][DEBUG] LLM API Error after {elapsed:.2f}s: {type(e).__name__}: {str(e)}[/bold red]")
            import traceback
            console.print(f"[dim][DEBUG] Traceback:\n{traceback.format_exc()}[/dim]")
            raise RuntimeError(f"LLM API Error: {str(e)}")
    
    def generate_next_steps(
        self,
        user_goal: str,
        context_str: str,
        execution_history: list,
        max_steps: int = 3
    ) -> dict:
        """
        根据当前状态生成接下来的步骤（渐进式执行）
        
        :param user_goal: 用户的总体目标
        :param context_str: 系统环境信息
        :param execution_history: 已执行的步骤历史 [{"description": ..., "command": ..., "output": ..., "success": ...}, ...]
        :param max_steps: 最多生成几个步骤
        :return: {"thought": ..., "steps": [...], "is_complete": bool}
        """
        
        console.print(f"[dim][DEBUG] Generating next steps (max: {max_steps})...[/dim]")
        start_time = time.time()
        
        # 构建执行历史摘要
        history_summary = self._build_history_summary(execution_history)
        
        system_prompt = f"""
You are an expert system engineer with the ability to break down complex tasks into steps and adapt based on execution results.

Current Execution Environment:
{context_str}

⚠️ CRITICAL JSON FORMAT REQUIREMENTS ⚠️

YOU MUST RESPOND WITH **ONLY** A VALID JSON OBJECT IN THIS **EXACT** FORMAT:

{{
   "thought": "Your reasoning about what to do next",
   "steps": [
      {{
         "description": "Step description",
         "command": "shell command"
      }}
   ],
   "is_complete": false
}}

IMPORTANT RULES:
1. Generate 1-{max_steps} steps based on the current situation
2. Consider the execution history and previous outputs
3. Use shell commands for ALL operations (cat, sed, grep, awk, etc.)
4. Set "is_complete": true ONLY when the entire goal is achieved
5. Each step should be atomic and clear
6. Use command substitution and pipes when needed

EXAMPLES OF GOOD COMMANDS:
- Read file: cat ~/test/a.sh
- Check output: if [ "$(cat file.txt)" = "1" ]; then echo "match"; fi
- Edit file: sed -i 's/echo 1/echo 2/g' ~/test/a.sh
- Conditional: [ "$(command)" = "expected" ] && next_command || alternative_command

Remember: Output ONLY the JSON object - absolutely nothing else!
"""

        user_message = f"""User Goal: {user_goal}

{history_summary}

Based on the execution history above, generate the next 1-{max_steps} steps to achieve the goal.

IMPORTANT: You MUST respond with ONLY a JSON object in this exact format:
{{
   "thought": "your reasoning here",
   "steps": [
      {{"description": "step description", "command": "shell command"}}
   ],
   "is_complete": false
}}

Do NOT include any other text, explanations, or markdown. ONLY the JSON object."""

        raw_content = None
        
        try:
            console.print(f"[dim][DEBUG] Calling LLM API for next steps...[/dim]")
            
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.5  # 稍低的温度以获得更确定的输出
            }
            
            # 处理 JSON 模式
            response = None
            
            if self.is_ollama:
                # Ollama: 直接调用
                console.print(f"[dim][DEBUG] Using Ollama for adaptive execution[/dim]")
                response = self.client.chat.completions.create(**api_params)
            else:
                # 非 Ollama: 尝试 JSON 模式
                json_mode_failed = False
                
                try:
                    api_params["response_format"] = {"type": "json_object"}
                    response = self.client.chat.completions.create(**api_params)
                except Exception as e:
                    error_msg = str(e)
                    if "response_format" in error_msg or "400" in error_msg:
                        console.print(f"[dim][DEBUG] JSON mode not supported, retrying without it...[/dim]")
                        json_mode_failed = True
                    else:
                        raise
                
                if json_mode_failed:
                    api_params.pop("response_format", None)
                    response = self.client.chat.completions.create(**api_params)
            
            elapsed = time.time() - start_time
            console.print(f"[dim][DEBUG] LLM API responded in {elapsed:.2f}s[/dim]")
            
            if response is None:
                raise RuntimeError("API call succeeded but response is None")
            
            raw_content = response.choices[0].message.content
            
            if not raw_content:
                raise ValueError("LLM returned empty response")
            
            cleaned_content = self._clean_json_response(raw_content)
            result = json.loads(cleaned_content)
            
            # 验证格式
            if not isinstance(result, dict):
                raise ValueError(f"Expected dict, got {type(result)}")
            
            if "steps" not in result:
                raise ValueError(f"Missing 'steps' field. Got keys: {list(result.keys())}")
            
            if not isinstance(result.get("steps"), list):
                raise ValueError(f"'steps' must be a list, got {type(result.get('steps'))}")
            
            # 验证每个step
            for i, step in enumerate(result["steps"]):
                if not isinstance(step, dict):
                    raise ValueError(f"Step {i+1} must be a dict, got {type(step)}")
                if "command" not in step:
                    raise ValueError(f"Step {i+1} missing 'command' field")
            
            # 确保 is_complete 字段存在
            if "is_complete" not in result:
                result["is_complete"] = False
            
            return result
            
        except json.JSONDecodeError as e:
            console.print(f"[bold red][DEBUG] JSON Parse Error: {str(e)}[/bold red]")
            console.print(f"[dim][DEBUG] Raw content: {raw_content or 'N/A'}[/dim]")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            elapsed = time.time() - start_time
            console.print(f"[bold red][DEBUG] LLM API Error after {elapsed:.2f}s: {type(e).__name__}: {str(e)}[/bold red]")
            import traceback
            console.print(f"[dim][DEBUG] Traceback:\n{traceback.format_exc()}[/dim]")
            raise RuntimeError(f"LLM API Error: {str(e)}")
    
    def _build_history_summary(self, execution_history: list) -> str:
        """构建执行历史摘要"""
        if not execution_history:
            return "Execution History: None (this is the first step)"
        
        summary_parts = ["Execution History:"]
        for i, step in enumerate(execution_history[-10:], 1):  # 只保留最近10步
            status = "✓" if step.get("success") else "✗"
            desc = step.get("description", "Unknown")
            cmd = step.get("command", "")
            output = step.get("output", "")
            
            # 限制输出长度
            if output:
                output_preview = output[:200] + "..." if len(output) > 200 else output
                summary_parts.append(f"{i}. {status} {desc}")
                summary_parts.append(f"   Command: {cmd}")
                summary_parts.append(f"   Output: {output_preview}")
            else:
                summary_parts.append(f"{i}. {status} {desc} (Command: {cmd})")
        
        return "\n".join(summary_parts)
