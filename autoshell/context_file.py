import os
from pathlib import Path
from rich.console import Console

console = Console()

class ContextFileManager:
    """管理用户提供的上下文文件"""
    
    # 支持的文本文件扩展名
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.json', '.yaml', '.yml',
        '.sh', '.bash', '.py', '.js', '.ts',
        '.conf', '.cfg', '.ini', '.toml',
        '.xml', '.html', '.css', '.sql',
        '.log', '.env', '.gitignore', '.rst',
        '.c', '.cpp', '.h', '.java', '.go',
        '.rb', '.php', '.pl', '.r', '.swift'
    }
    
    @staticmethod
    def validate_file(filepath: str, max_size: int) -> tuple:
        """
        验证文件是否存在、可读、大小合理
        
        :param filepath: 文件路径
        :param max_size: 最大文件大小（字节）
        :return: (is_valid: bool, error_message: str or None)
        """
        try:
            path = Path(filepath)
            
            # 检查文件是否存在
            if not path.exists():
                return False, f"文件不存在: {filepath}"
            
            # 检查是否为文件（不是目录）
            if not path.is_file():
                return False, f"路径不是文件: {filepath}"
            
            # 检查文件大小
            file_size = path.stat().st_size
            if file_size == 0:
                console.print(f"[yellow]警告: 文件为空: {filepath}[/yellow]")
            elif file_size > max_size:
                size_mb = file_size / (1024 * 1024)
                max_mb = max_size / (1024 * 1024)
                return False, f"文件过大: {size_mb:.2f}MB (最大: {max_mb:.2f}MB)"
            
            # 检查文件是否可读
            if not os.access(filepath, os.R_OK):
                return False, f"文件不可读: {filepath}"
            
            # 检查文件扩展名（可选警告）
            if path.suffix.lower() not in ContextFileManager.SUPPORTED_EXTENSIONS and path.suffix:
                console.print(f"[yellow]警告: 文件扩展名 '{path.suffix}' 可能不是文本文件[/yellow]")
            
            return True, None
            
        except Exception as e:
            return False, f"验证文件时出错: {str(e)}"
    
    @staticmethod
    def read_context_file(filepath: str) -> dict:
        """
        读取单个上下文文件
        
        :param filepath: 文件路径
        :return: {
            'filepath': str,
            'filename': str,
            'content': str,
            'size': int,
            'error': str or None
        }
        """
        result = {
            'filepath': filepath,
            'filename': Path(filepath).name,
            'content': '',
            'size': 0,
            'error': None
        }
        
        try:
            path = Path(filepath)
            result['size'] = path.stat().st_size
            
            # 尝试多种编码读取
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
            content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        content = f.read()
                    used_encoding = encoding
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if content is None:
                result['error'] = "无法使用支持的编码读取文件"
                return result
            
            result['content'] = content
            
            # 如果使用了非UTF-8编码，给出提示
            if used_encoding and used_encoding != 'utf-8':
                console.print(f"[dim]提示: 文件 {result['filename']} 使用 {used_encoding} 编码读取[/dim]")
            
        except Exception as e:
            result['error'] = f"读取文件时出错: {str(e)}"
        
        return result
    
    @staticmethod
    def read_multiple_files(filepaths: list, max_size: int) -> list:
        """
        读取多个上下文文件
        
        :param filepaths: 文件路径列表
        :param max_size: 单个文件最大大小
        :return: 文件信息列表
        """
        results = []
        
        for filepath in filepaths:
            # 验证文件
            is_valid, error_msg = ContextFileManager.validate_file(filepath, max_size)
            
            if not is_valid:
                console.print(f"[bold red]错误:[/bold red] {error_msg}")
                continue
            
            # 读取文件
            file_info = ContextFileManager.read_context_file(filepath)
            
            if file_info['error']:
                console.print(f"[bold red]错误:[/bold red] {file_info['error']}")
                continue
            
            results.append(file_info)
        
        return results
    
    @staticmethod
    def format_context_string(context_files: list) -> str:
        """
        将上下文文件格式化为prompt字符串
        
        :param context_files: 文件信息列表
        :return: 格式化的字符串
        """
        if not context_files:
            return ""
        
        lines = ["\n=== User Provided Context Files ===\n"]
        lines.append("The user has provided the following context files for reference:\n")
        
        for file_info in context_files:
            filename = file_info['filename']
            content = file_info['content']
            size = file_info['size']
            line_count = len(content.splitlines())
            
            lines.append(f"\n--- File: {filename} (Size: {size} bytes, Lines: {line_count}) ---")
            lines.append(content)
            lines.append(f"--- End of {filename} ---\n")
        
        lines.append("\n⚠️ IMPORTANT: Please consider the information in these context files when generating commands.")
        lines.append("The context may include:")
        lines.append("- Examples to follow or reference")
        lines.append("- Configuration requirements and settings")
        lines.append("- Environment setup instructions")
        lines.append("- Coding standards or conventions")
        lines.append("- Project-specific information")
        lines.append("- Proxy settings or network configuration")
        lines.append("- Deployment procedures")
        lines.append("- Any other relevant information for the task")
        lines.append("\n=== End of User Context ===\n")
        
        return "\n".join(lines)
    
    @staticmethod
    def display_file_summary(context_files: list):
        """
        显示上下文文件摘要
        
        :param context_files: 文件信息列表
        """
        if not context_files:
            return
        
        console.print(f"\n[bold cyan]已加载 {len(context_files)} 个上下文文件:[/bold cyan]")
        
        total_size = 0
        total_lines = 0
        
        for i, file_info in enumerate(context_files, 1):
            filename = file_info['filename']
            size = file_info['size']
            lines = len(file_info['content'].splitlines())
            
            total_size += size
            total_lines += lines
            
            size_kb = size / 1024
            console.print(f"  {i}. [green]{filename}[/green] - {size_kb:.2f}KB, {lines} 行")
        
        # 显示总计
        total_kb = total_size / 1024
        console.print(f"\n[dim]总计: {total_kb:.2f}KB, {total_lines} 行[/dim]")
        console.print()
