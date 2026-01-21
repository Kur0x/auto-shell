import json
import re
from openai import OpenAI
from .config import Config

class LLMClient:
    def __init__(self):
        Config.validate()
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        self.model = Config.LLM_MODEL

    def _clean_json_response(self, content: str) -> str:
        """
        清理 LLM 可能返回的 Markdown 代码块标记，提取纯 JSON 字符串。
        """
        content = content.strip()
        # 移除 ```json ... ``` 或 ``` ... ``` 包裹
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            return match.group(1)
        return content

    def generate_plan(self, user_query: str, context_str: str, error_history: list = None) -> dict:
        """
        根据用户查询和环境上下文生成 Shell 命令计划。
        
        :param user_query: 用户的自然语言指令
        :param context_str: 格式化后的系统环境信息
        :param error_history: 之前的错误历史，用于重试/自愈逻辑
        :return: 解析后的 JSON 字典 {"thought": ..., "steps": [{"description":..., "command":...}, ...]}
        """
        
        system_prompt = f"""
You are an expert system engineer and command-line wizard.
Your goal is to translate natural language instructions into a SERIES of precise, efficient, and safe Shell commands.

Current Execution Environment:
{context_str}

Protocol:
1. Analyze the user's request based on the current OS and Shell.
2. Break down the task into sequential logical steps (Plan).
3. For each step, formulate a valid shell command.
4. Output MUST be a strictly valid JSON object with the following structure:
   {{
      "thought": "Brief explanation of the plan...",
      "steps": [
         {{
            "description": "Step 1 description",
            "command": "actual shell command"
         }},
         ...
      ]
   }}

Constraints:
- Do NOT output any text outside the JSON object.
- Use explicit commands. For example, use 'cd target && ls' logic or separate 'cd target' as a step if the user implies state change. Note that 'cd' commands will be handled by the execution engine to maintain state across steps.
- Ensure commands are valid for the detected Shell type.
"""

        user_message = f"User Request: {user_query}"

        if error_history:
            # error_history 结构: [{"step_index": int, "command": str, "error": str}, ...]
            error_context = "\n".join([f"Previous failure at step {e.get('step_index', '?')}:\nCommand: {e['command']}\nError: {e['error']}" for e in error_history])
            user_message += f"\n\nPREVIOUS EXECUTION FAILED. Please analyze the errors and provide a FIXED plan (you can adjust the remaining steps):\n{error_context}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2
            )
            
            raw_content = response.choices[0].message.content
            cleaned_content = self._clean_json_response(raw_content)
            
            return json.loads(cleaned_content)
            
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {raw_content}")
        except Exception as e:
            raise RuntimeError(f"LLM API Error: {str(e)}")
