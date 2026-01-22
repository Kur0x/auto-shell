"""SSH模式下的远程系统信息收集"""

import os
from typing import Dict, Optional, Any
from rich.console import Console
from .config import Config

console = Console()

# 尝试导入paramiko
try:
    import paramiko
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False
    paramiko = None


class SSHContextManager:
    """SSH模式下的远程系统信息收集"""
    
    @staticmethod
    def test_connection(ssh_config: Dict[str, Any], timeout: int = 10) -> tuple[bool, str]:
        """
        测试SSH连接是否可用
        
        :param ssh_config: SSH配置字典
        :param timeout: 连接超时时间（秒）
        :return: (是否成功, 错误信息或成功消息)
        """
        if not SSH_AVAILABLE:
            return False, "paramiko not installed. Please install it: pip install paramiko"
        
        try:
            # 解析SSH配置
            host_str = ssh_config.get('host', '')
            if '@' in host_str:
                username, hostname = host_str.split('@', 1)
            else:
                username = None
                hostname = host_str
            
            if not hostname:
                return False, "Invalid SSH host configuration"
            
            port = ssh_config.get('port', 22)
            password = ssh_config.get('password')
            key_filename = ssh_config.get('key_filename')
            
            # 创建SSH客户端
            client = paramiko.SSHClient()  # type: ignore
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # type: ignore
            
            # 加载SSH配置文件
            ssh_config_obj = paramiko.SSHConfig()  # type: ignore
            ssh_config_path = os.path.expanduser('~/.ssh/config')
            if os.path.exists(ssh_config_path):
                try:
                    with open(ssh_config_path) as f:
                        ssh_config_obj.parse(f)
                    
                    # 查找主机配置
                    host_config = ssh_config_obj.lookup(hostname)
                    
                    # 从配置文件获取实际的主机名和其他参数
                    hostname = host_config.get('hostname', hostname)
                    if not username and 'user' in host_config:
                        username = host_config['user']
                    if not key_filename and 'identityfile' in host_config:
                        key_filename = host_config['identityfile'][0] if isinstance(host_config['identityfile'], list) else host_config['identityfile']
                    if 'port' in host_config:
                        port = int(host_config['port'])
                except Exception as e:
                    if Config.DEBUG:
                        console.print(f"[dim][DEBUG] Failed to parse SSH config: {e}[/dim]")
            
            # 连接参数
            connect_kwargs = {
                'hostname': hostname,
                'port': port,
                'timeout': timeout
            }
            
            if username:
                connect_kwargs['username'] = username
            
            if key_filename:
                key_filename = os.path.expanduser(key_filename)
                if not os.path.exists(key_filename):
                    return False, f"SSH key file not found: {key_filename}"
                connect_kwargs['key_filename'] = key_filename
            elif password:
                connect_kwargs['password'] = password
            elif not username:
                return False, "No authentication method provided (username, password, or key)"
            
            # 尝试连接
            try:
                client.connect(**connect_kwargs)
                
                # 执行简单命令测试连接
                stdin, stdout, stderr = client.exec_command("echo 'connection_test'", timeout=5)
                output = stdout.read().decode('utf-8').strip()
                
                client.close()
                
                if output == 'connection_test':
                    return True, f"Successfully connected to {username}@{hostname}:{port}"
                else:
                    return False, "Connection established but command execution failed"
                    
            except paramiko.AuthenticationException:  # type: ignore
                return False, f"Authentication failed for {username}@{hostname}:{port}"
            except paramiko.SSHException as e:  # type: ignore
                return False, f"SSH error: {str(e)}"
            except TimeoutError:
                return False, f"Connection timeout to {hostname}:{port}"
            except Exception as e:
                return False, f"Connection failed: {str(e)}"
                
        except Exception as e:
            return False, f"Failed to initialize SSH connection: {str(e)}"
    
    @staticmethod
    def _execute_ssh_command(ssh_client, command: str, timeout: int = 5) -> str:
        """通过SSH执行命令并返回输出"""
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8').strip()
            return output
        except Exception as e:
            if Config.DEBUG:
                console.print(f"[dim][DEBUG] SSH command failed: {command} - {e}[/dim]")
            return ""
    
    @staticmethod
    def _parse_os_release(content: str) -> dict:
        """解析 /etc/os-release 文件内容"""
        info = {}
        for line in content.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                info[key] = value
        return info
    
    @staticmethod
    def get_remote_system_info(ssh_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        收集远程系统详细信息
        
        :param ssh_config: SSH配置字典
        :return: 系统信息字典
        """
        if not SSH_AVAILABLE:
            return {
                "os_type": "Linux",
                "distro_pretty_name": "Unknown Linux (SSH unavailable)",
                "error": "paramiko not installed"
            }
        
        # 默认信息
        default_info = {
            "os_type": "Linux",
            "distro_pretty_name": "Unknown Linux",
            "architecture": "x86_64",
            "kernel": "unknown",
            "package_manager": "unknown"
        }
        
        try:
            # 解析SSH配置
            host_str = ssh_config.get('host', '')
            if '@' in host_str:
                username, hostname = host_str.split('@', 1)
            else:
                username = None
                hostname = host_str
            
            port = ssh_config.get('port', 22)
            password = ssh_config.get('password')
            key_filename = ssh_config.get('key_filename')
            
            # 创建SSH客户端
            client = paramiko.SSHClient()  # type: ignore
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # type: ignore
            
            # 加载SSH配置文件
            ssh_config_obj = paramiko.SSHConfig()  # type: ignore
            ssh_config_path = os.path.expanduser('~/.ssh/config')
            if os.path.exists(ssh_config_path):
                with open(ssh_config_path) as f:
                    ssh_config_obj.parse(f)
                
                # 查找主机配置
                host_config = ssh_config_obj.lookup(hostname)
                
                # 从配置文件获取实际的主机名和其他参数
                hostname = host_config.get('hostname', hostname)
                if not username and 'user' in host_config:
                    username = host_config['user']
                if not key_filename and 'identityfile' in host_config:
                    key_filename = host_config['identityfile'][0] if isinstance(host_config['identityfile'], list) else host_config['identityfile']
                if 'port' in host_config:
                    port = int(host_config['port'])
            
            # 连接参数
            connect_kwargs = {
                'hostname': hostname,
                'port': port,
                'timeout': 10
            }
            
            if username:
                connect_kwargs['username'] = username
            
            if key_filename:
                key_filename = os.path.expanduser(key_filename)
                connect_kwargs['key_filename'] = key_filename
            elif password:
                connect_kwargs['password'] = password
            
            # 连接
            client.connect(**connect_kwargs)
            
            # 收集信息
            info = {}
            
            # OS类型
            os_type = SSHContextManager._execute_ssh_command(client, "uname -s")
            info["os_type"] = os_type or "Linux"
            
            # 架构
            arch = SSHContextManager._execute_ssh_command(client, "uname -m")
            info["architecture"] = arch or "unknown"
            
            # 内核版本
            kernel = SSHContextManager._execute_ssh_command(client, "uname -r")
            info["kernel"] = kernel or "unknown"
            
            # 发行版信息
            os_release = SSHContextManager._execute_ssh_command(
                client,
                "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo 'Unknown'"
            )
            
            if os_release and os_release != "Unknown":
                if "=" in os_release:
                    # /etc/os-release 格式
                    parsed = SSHContextManager._parse_os_release(os_release)
                    info['distro_name'] = parsed.get('NAME', 'Unknown')
                    info['distro_id'] = parsed.get('ID', 'unknown')
                    info['distro_version'] = parsed.get('VERSION_ID', 'unknown')
                    info['distro_pretty_name'] = parsed.get('PRETTY_NAME', 'Unknown Linux')
                else:
                    # 简单格式（如 /etc/redhat-release）
                    info['distro_pretty_name'] = os_release
            else:
                info['distro_pretty_name'] = 'Unknown Linux'
            
            # 检测包管理器
            pkg_managers = ['apt', 'yum', 'dnf', 'pacman', 'zypper', 'apk']
            for mgr in pkg_managers:
                result = SSHContextManager._execute_ssh_command(client, f"which {mgr} 2>/dev/null")
                if result:
                    info['package_manager'] = mgr
                    break
            else:
                info['package_manager'] = 'unknown'
            
            # Shell类型
            shell = SSHContextManager._execute_ssh_command(client, "echo $SHELL")
            if shell:
                info['shell'] = os.path.basename(shell)
            else:
                info['shell'] = 'bash'
            
            # 用户名
            user = SSHContextManager._execute_ssh_command(client, "whoami")
            info['user'] = user or 'unknown'
            
            # 检查是否为root用户
            uid = SSHContextManager._execute_ssh_command(client, "id -u")
            info['is_root'] = uid == '0'
            
            # Home目录
            home = SSHContextManager._execute_ssh_command(client, "echo $HOME")
            info['home'] = home or '~'
            
            # Python版本
            python_ver = SSHContextManager._execute_ssh_command(
                client,
                "python3 --version 2>&1 || python --version 2>&1 || echo 'Not installed'"
            )
            if python_ver and "Python" in python_ver:
                info['python_version'] = python_ver.replace("Python ", "").strip()
            else:
                info['python_version'] = 'not installed'
            
            # 检查sudo权限
            has_sudo = SSHContextManager._execute_ssh_command(
                client,
                "sudo -n true 2>/dev/null && echo 'yes' || echo 'no'"
            )
            info['has_sudo'] = has_sudo == 'yes'
            
            # 主机名
            hostname_full = SSHContextManager._execute_ssh_command(client, "hostname")
            info['hostname'] = hostname_full or hostname
            
            # 关闭连接
            client.close()
            
            return info
            
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to collect remote system info: {e}[/yellow]")
            return default_info
    
    @staticmethod
    def format_remote_context(info: Dict[str, Any]) -> str:
        """格式化远程系统信息为上下文字符串"""
        lines = []
        
        distro = info.get("distro_pretty_name", "Unknown Linux")
        kernel = info.get("kernel", "unknown")
        arch = info.get("architecture", "unknown")
        pkg_mgr = info.get("package_manager", "unknown")
        shell = info.get("shell", "bash")
        user = info.get("user", "unknown")
        hostname = info.get("hostname", "remote")
        is_root = info.get("is_root", False)
        
        lines.append(f"- Remote OS: {distro}")
        lines.append(f"- Architecture: {arch}")
        lines.append(f"- Kernel: {kernel}")
        lines.append(f"- Package Manager: {pkg_mgr}")
        lines.append(f"- Shell: {shell}")
        lines.append(f"- User: {user}@{hostname}")
        
        if is_root:
            lines.append("- User Privilege: root (no sudo needed)")
        elif info.get("has_sudo"):
            lines.append("- Sudo Access: Available")
        
        python_ver = info.get("python_version", "unknown")
        if python_ver != "not installed":
            lines.append(f"- Python Version: {python_ver}")
        
        return "\n".join(lines)
