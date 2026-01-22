# SSH远程命令中断功能修复

## 修复内容

修复了SSH远程执行命令时无法通过Ctrl+C中断的问题，并添加了实时输出显示和交互式输入支持（如sudo密码）。

## 技术实现

### 修改文件
- [`autoshell/executor.py`](autoshell/executor.py)

### 关键改进

1. **使用PTY（伪终端）**
   ```python
   stdin, stdout, stderr = client.exec_command(command, get_pty=True)
   ```
   - 分配伪终端，支持信号传递
   - 允许将本地Ctrl+C转换为远程SIGINT信号

2. **非阻塞读取**
   ```python
   stdout.channel.setblocking(0)
   while not stdout.channel.exit_status_ready():
       if stdout.channel.recv_ready():
           data = stdout.channel.recv(4096)
       time.sleep(0.1)
   ```
   - 设置channel为非阻塞模式
   - 使用循环读取，可以响应KeyboardInterrupt
   - 避免阻塞在`read()`调用上

3. **中断信号处理**
   ```python
   except KeyboardInterrupt:
       stdout.channel.send(b'\x03')  # 发送Ctrl+C到远程
   ```
   - 捕获本地KeyboardInterrupt
   - 发送ASCII码3（Ctrl+C）到远程进程
   - 优雅地终止远程命令

4. **交互式输入支持**
   ```python
   # 检查用户输入
   if sys.stdin in readable:
       user_input = sys.stdin.readline()
       stdin.write(user_input)
   ```
   - 支持交互式命令（如sudo密码输入）
   - Windows使用msvcrt.kbhit()检测按键
   - Unix使用select检测stdin可读性

## 测试方法

### 测试用例1：短命令（正常完成）
```bash
python main.py --ssh-host user@hostname -c "echo 'test'"
```
**预期结果**：命令正常执行并返回输出

### 测试用例2：长命令 + 中断
```bash
python main.py --ssh-host user@hostname -c "sleep 30"
# 执行过程中按 Ctrl+C
```
**预期结果**：
- 显示 "Sending interrupt signal to remote process..."
- 命令被中断
- 返回 "Command interrupted by user (Ctrl+C)"

### 测试用例3：循环命令 + 中断
```bash
python main.py --ssh-host user@hostname -c "while true; do echo 'running'; sleep 1; done"
# 按 Ctrl+C
```
**预期结果**：循环被中断，远程进程终止

### 测试用例4：管道命令 + 中断
```bash
python main.py --ssh-host user@hostname -c "yes | head -n 1000000"
# 按 Ctrl+C
```
**预期结果**：管道命令被中断

### 测试用例5：sudo命令（需要密码）
```bash
python main.py --ssh-host user@hostname -c "sudo apt update"
# 当提示输入密码时，直接输入密码并按回车
```
**预期结果**：
- 显示 "[sudo] password for user:"
- 用户输入密码（不显示）
- 命令正常执行

## 行为变化

### 修复前
- 按Ctrl+C无响应
- 必须等待命令执行完成
- 无法终止长时间运行的命令

### 修复后
- 按Ctrl+C立即响应
- 发送中断信号到远程进程
- 远程命令被优雅终止
- 返回已收集的输出
- 支持实时输出显示
- 支持交互式输入（如sudo密码）

## 注意事项

1. **PTY输出格式**
   - 使用PTY可能会改变某些命令的输出格式
   - 某些命令可能会输出ANSI颜色代码
   - 使用 `errors='replace'` 处理编码错误

2. **中断延迟**
   - 发送中断信号后等待0.5秒让进程响应
   - 如果进程未响应，会再次发送中断信号
   - 某些进程可能需要更长时间才能终止

3. **交互式输入**
   - 支持sudo密码输入等交互式场景
   - Windows使用msvcrt检测按键
   - Unix使用select检测stdin
   - 输入会实时发送到远程进程

4. **兼容性**
   - 已测试与paramiko库的兼容性
   - 支持各种Linux发行版
   - 向后兼容，不影响现有功能
   - Windows和Unix系统都支持

## 相关文档

- [SSH使用指南](SSH_USAGE.md)
- [执行器文档](autoshell/executor.py)

## 版本信息

- 修复日期：2026-01-22
- 影响范围：SSH远程执行功能
- 向后兼容：是
