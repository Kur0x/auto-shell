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

    def generate_command(self, user_query: str, context_str: str, error_history: list = None) -> dict:
        """
        根据用户查询和环境上下文生成 Shell 命令。
        
        :param user_query: 用户的自然语言指令
        :param context_str: 格式化后的系统环境信息
        :param error_history: 之前的错误历史，用于重试/自愈逻辑
        :return: 解析后的 JSON 字典 {"thought": ..., "command": ...}
        """
        
        system_prompt = f"""
You are an expert system engineer and command-line wizard.
Your goal is to translate natural language instructions into precise, efficient, and safe Shell commands.

Current Execution Environment:
{context_str}

Protocol:
1. Analyze the user's request based on the current OS and Shell.
2. Formulate a SINGLE line shell command to accomplish the task.
3. If the task is complex, chain commands using `&&` or `|` operators appropriate for the shell.
4. Output MUST be a strictly valid JSON object with exactly two keys:
   - "thought": A brief explanation of your reasoning (string).
   - "command": The actual shell command to execute (string).

Constraints:
- Do NOT output any text outside the JSON object.
- Do NOT use markdown formatting (like ```json) unless absolutely necessary, but preferably just raw JSON.
- The command must be valid for the detected Shell type.
"""

        user_message = f"User Request: {user_query}"

        if error_history:
            # 如果有错误历史，将其附加到 Prompt 中，触发自愈逻辑
            error_context = "\n".join([f"Attempt {i+1} Failed:\nCommand: {e['command']}\nError: {e['error']}" for i, e in enumerate(error_history)])
            user_message += f"\n\nPREVIOUS ATTEMPTS FAILED. Please analyze the following errors and provide a FIXED command:\n{error_context}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2 # 低温度以保证确定性
            )
            
            raw_content = response.choices[0].message.content
            cleaned_content = self._clean_json_response(raw_content)
            
            return json.loads(cleaned_content)
            
        except json.JSONDecodeError:
            # 简单的重试或回退逻辑，这里暂且抛出异常，由上层处理或再次重试
            raise ValueError(f"LLM returned invalid JSON: {raw_content}")
        except Exception as e:
            raise RuntimeError(f"LLM API Error: {str(e)}")
