import os
import platform
import getpass
import shutil
import subprocess
import re

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
    
    # ========== 新增：详细系统信息收集功能 ==========
    
    @staticmethod
    def _read_file_safe(filepath: str) -> str:
        """安全读取文件内容"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    @staticmethod
    def _run_command_safe(command: str) -> str:
        """安全执行命令并返回输出"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    @staticmethod
    def _parse_os_release(content: str) -> dict:
        """解析 /etc/os-release 文件内容"""
        info = {}
        for line in content.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                # 移除引号
                value = value.strip('"').strip("'")
                info[key] = value
        return info
    
    @staticmethod
    def _detect_package_manager() -> str:
        """检测Linux包管理器"""
        managers = {
            'apt': 'apt',
            'apt-get': 'apt',
            'yum': 'yum',
            'dnf': 'dnf',
            'pacman': 'pacman',
            'zypper': 'zypper',
            'apk': 'apk'
        }
        
        for cmd, name in managers.items():
            if shutil.which(cmd):
                return name
        
        return "unknown"
    
    @staticmethod
    def _get_linux_distro_info() -> dict:
        """获取Linux发行版详细信息"""
        info = {}
        
        # 尝试读取 /etc/os-release
        os_release_content = ContextManager._read_file_safe('/etc/os-release')
        if os_release_content:
            parsed = ContextManager._parse_os_release(os_release_content)
            info['distro_name'] = parsed.get('NAME', 'Unknown')
            info['distro_id'] = parsed.get('ID', 'unknown')
            info['distro_version'] = parsed.get('VERSION_ID', 'unknown')
            info['distro_pretty_name'] = parsed.get('PRETTY_NAME', 'Unknown Linux')
        else:
            # 降级方案：尝试其他文件
            redhat_release = ContextManager._read_file_safe('/etc/redhat-release')
            if redhat_release:
                info['distro_pretty_name'] = redhat_release.strip()
            else:
                info['distro_pretty_name'] = 'Unknown Linux'
        
        return info
    
    @staticmethod
    def _get_powershell_version() -> str:
        """获取PowerShell版本"""
        version = ContextManager._run_command_safe('powershell -Command "$PSVersionTable.PSVersion.ToString()"')
        if not version:
            version = ContextManager._run_command_safe('pwsh -Command "$PSVersionTable.PSVersion.ToString()"')
        return version or "unknown"
    
    @staticmethod
    def _get_macos_release_name() -> str:
        """获取macOS版本名称"""
        version = platform.mac_ver()[0]
        if not version:
            return "Unknown"
        
        # 简单的版本映射
        try:
            major = int(version.split('.')[0])
            names = {
                14: "Sonoma",
                13: "Ventura",
                12: "Monterey",
                11: "Big Sur",
                10: "Catalina"
            }
            return names.get(major, f"macOS {version}")
        except:
            return f"macOS {version}"
    
    @staticmethod
    def get_detailed_os_info() -> dict:
        """获取详细的操作系统信息（本地）"""
        os_type = platform.system()
        
        info = {
            "os_type": os_type,
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node()
        }
        
        if os_type == "Linux":
            # Linux详细信息
            distro_info = ContextManager._get_linux_distro_info()
            info.update(distro_info)
            info["kernel"] = platform.release()
            info["package_manager"] = ContextManager._detect_package_manager()
            
            # 检查sudo权限（非阻塞）
            has_sudo = ContextManager._run_command_safe('sudo -n true 2>/dev/null && echo "yes" || echo "no"')
            info["has_sudo"] = has_sudo == "yes"
            
        elif os_type == "Windows":
            info["windows_version"] = platform.version()
            info["windows_release"] = platform.release()
            info["powershell_version"] = ContextManager._get_powershell_version()
            
        elif os_type == "Darwin":
            info["macos_version"] = platform.mac_ver()[0]
            info["macos_release"] = ContextManager._get_macos_release_name()
            # 检查Homebrew
            info["has_homebrew"] = bool(shutil.which('brew'))
        
        return info
    
    @classmethod
    def get_enhanced_context_string(cls, detailed_info: dict = None) -> str:
        """获取增强的上下文字符串"""
        if detailed_info is None:
            detailed_info = cls.get_detailed_os_info()
        
        os_type = detailed_info.get("os_type", "Unknown")
        
        # 基础信息
        lines = []
        
        if os_type == "Linux":
            distro = detailed_info.get("distro_pretty_name", "Unknown Linux")
            kernel = detailed_info.get("kernel", "unknown")
            arch = detailed_info.get("architecture", "unknown")
            pkg_mgr = detailed_info.get("package_manager", "unknown")
            
            lines.append(f"- OS: {distro}")
            lines.append(f"- Architecture: {arch}")
            lines.append(f"- Kernel: {kernel}")
            lines.append(f"- Package Manager: {pkg_mgr}")
            lines.append(f"- Shell: {cls.get_shell_type()}")
            
            if detailed_info.get("has_sudo"):
                lines.append("- Sudo Access: Available")
            
        elif os_type == "Windows":
            win_ver = detailed_info.get("windows_release", "Unknown")
            ps_ver = detailed_info.get("powershell_version", "unknown")
            arch = detailed_info.get("architecture", "unknown")
            
            lines.append(f"- OS: Windows {win_ver}")
            lines.append(f"- Architecture: {arch}")
            lines.append(f"- PowerShell Version: {ps_ver}")
            lines.append(f"- Shell: {cls.get_shell_type()}")
            
        elif os_type == "Darwin":
            macos_release = detailed_info.get("macos_release", "Unknown")
            macos_ver = detailed_info.get("macos_version", "unknown")
            arch = detailed_info.get("architecture", "unknown")
            
            lines.append(f"- OS: macOS {macos_release} ({macos_ver})")
            lines.append(f"- Architecture: {arch}")
            lines.append(f"- Shell: {cls.get_shell_type()}")
            
            if detailed_info.get("has_homebrew"):
                lines.append("- Package Manager: Homebrew")
        
        # 通用信息
        lines.append(f"- Current Working Directory: {cls.get_cwd()}")
        lines.append(f"- User: {cls.get_user()}")
        lines.append(f"- Python Version: {detailed_info.get('python_version', 'unknown')}")
        
        return "\n".join(lines)
