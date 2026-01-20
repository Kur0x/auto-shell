import os
import platform
import getpass
import shutil

class ContextManager:
    """
    负责感知当前运行环境的上下文信息。
    """
    
    @staticmethod
    def get_os_info() -> str:
        """获取操作系统信息 (Windows/Linux/Darwin)"""
        return platform.system()

    @staticmethod
    def get_shell_type() -> str:
        """
        获取当前 Shell 类型。
        注意：在 Python 中准确获取父 Shell 比较复杂，
        这里使用简单的环境变量推断或默认值。
        """
        # 尝试通过环境变量 SHELL (Linux/Mac) 或 COMSPEC (Windows) 判断
        if platform.system() == "Windows":
             # 简单判断 PowerShell 还是 CMD
             # 通常 PSModulePath 存在则很大可能是 PowerShell 环境，但也不绝对
             # 这里返回通用 'powershell/cmd' 提示 LLM 兼容两者，或者更倾向于 powershell
             if "PSModulePath" in os.environ:
                 return "powershell"
             return "cmd"
        else:
            shell_env = os.environ.get("SHELL")
            if shell_env:
                return os.path.basename(shell_env)
            return "bash" # Default fallback

    @staticmethod
    def get_cwd() -> str:
        """获取当前工作目录"""
        return os.getcwd()

    @staticmethod
    def get_user() -> str:
        """获取当前用户名"""
        return getpass.getuser()

    @classmethod
    def get_full_context(cls) -> dict:
        """获取所有上下文信息的汇总"""
        return {
            "os": cls.get_os_info(),
            "shell": cls.get_shell_type(),
            "cwd": cls.get_cwd(),
            "user": cls.get_user()
        }

    @classmethod
    def get_context_string(cls) -> str:
        """获取格式化的上下文描述字符串，用于 Prompt"""
        ctx = cls.get_full_context()
        return (
            f"- OS: {ctx['os']}\n"
            f"- Shell: {ctx['shell']}\n"
            f"- Current Working Directory: {ctx['cwd']}\n"
            f"- User: {ctx['user']}"
        )
