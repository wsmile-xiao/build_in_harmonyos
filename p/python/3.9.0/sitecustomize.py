"""
HarmonyOS Subprocess Compatibility Layer

问题分析：
==========
HarmonyOS 的 SELinux 域转换机制导致 Python 子进程无法直接执行某些操作：
1. 当 shell 进程执行用户二进制时，域从 hishell_hap 转换为 adhoc_bin
2. adhoc_bin 域的权限受限，可能无法访问某些资源（如 /tmp）

解决方案：
==========
使用管道语法（cmd 2>&1 | cat）强制 shell 创建子进程，这些子进程可能保留原始权限。

关键发现：
- subprocess.run(['ls', '/tmp']) → Permission denied
- subprocess.run('ls /tmp 2>&1 | cat', shell=True) → SUCCESS

使用方法：
==========
安装: {site-packages}/sitecustomize.py
禁用: export HARMONYOS_SUBPROCESS_COMPAT=0
调试: export HARMONYOS_SUBPROCESS_DEBUG=1
"""

import os
import sys
import shlex

# 配置
DEBUG = os.environ.get('HARMONYOS_SUBPROCESS_DEBUG', '0') == '1'

def _log(msg):
    if DEBUG:
        print(f"[HarmonyOS-Compat] {msg}", file=sys.stderr)

def _is_harmonyos():
    """检测是否运行在 HarmonyOS 上"""
    platform = sys.platform.lower()
    return 'harmonyos' in platform or 'ohos' in platform

def _wrap_with_pipe(cmd_str):
    """
    为命令添加管道语法以绕过 HarmonyOS 限制
    
    格式: set -o pipefail; {cmd} 2>&1 | cat
    
    pipefail 确保命令的退出码正确传递
    """
    return f"set -o pipefail; {cmd_str} 2>&1 | cat"

def _should_wrap():
    """判断是否应该启用兼容层"""
    if not _is_harmonyos():
        return False
    return os.environ.get('HARMONYOS_SUBPROCESS_COMPAT', '1') != '0'

if _should_wrap():
    # ============================================================
    # 包装 os.system
    # ============================================================
    _original_os_system = os.system
    
    def _wrapped_os_system(cmd):
        if cmd:
            wrapped_cmd = _wrap_with_pipe(cmd)
            _log(f"os.system: {cmd[:60]}...")
            return _original_os_system(wrapped_cmd)
        return _original_os_system(cmd)
    
    os.system = _wrapped_os_system
    _log("Wrapped: os.system")
    
    # ============================================================
    # 包装 os.popen
    # ============================================================
    _original_os_popen = os.popen
    
    def _wrapped_os_popen(cmd, mode='r', buffering=-1):
        if cmd:
            wrapped_cmd = _wrap_with_pipe(cmd)
            _log(f"os.popen: {cmd[:60]}...")
            return _original_os_popen(wrapped_cmd, mode, buffering)
        return _original_os_popen(cmd, mode, buffering)
    
    os.popen = _wrapped_os_popen
    _log("Wrapped: os.popen")
    
    # ============================================================
    # 包装 subprocess.Popen
    # ============================================================
    import subprocess
    
    _original_popen_init = subprocess.Popen.__init__
    
    def _wrapped_popen_init(self, *args, **kwargs):
        # 获取命令
        cmd = args[0] if args else kwargs.get('args')
        
        if cmd:
            # 判断命令类型
            if isinstance(cmd, (list, tuple)):
                # 列表命令：转换为带管道的 shell 命令
                cmd_str = ' '.join(shlex.quote(str(a)) for a in cmd)
                wrapped_cmd = _wrap_with_pipe(cmd_str)
                
                # 修改参数：使用 shell=True 和包装后的命令
                new_args = (wrapped_cmd,) + args[1:] if len(args) > 1 else (wrapped_cmd,)
                kwargs['shell'] = True
                kwargs.pop('executable', None)
                
                # 处理 stdout/stderr 重定向
                # 管道语法已经处理了输出，需要调整
                if 'capture_output' in kwargs and kwargs['capture_output']:
                    kwargs.pop('capture_output')
                    if 'stdout' not in kwargs:
                        kwargs['stdout'] = subprocess.PIPE
                    if 'stderr' not in kwargs:
                        kwargs['stderr'] = subprocess.PIPE
                
                _log(f"Popen(list): {cmd_str[:60]}...")
                return _original_popen_init(self, *new_args, **kwargs)
            else:
                # 字符串命令：添加管道语法，确保 shell=True
                wrapped_cmd = _wrap_with_pipe(str(cmd))
                kwargs['shell'] = True
                kwargs.pop('executable', None)
                
                # 处理 capture_output
                if 'capture_output' in kwargs and kwargs['capture_output']:
                    kwargs.pop('capture_output')
                    if 'stdout' not in kwargs:
                        kwargs['stdout'] = subprocess.PIPE
                    if 'stderr' not in kwargs:
                        kwargs['stderr'] = subprocess.PIPE
                
                _log(f"Popen(str): {str(cmd)[:60]}...")
                return _original_popen_init(self, wrapped_cmd, **kwargs)
        
        return _original_popen_init(self, *args, **kwargs)
    
    subprocess.Popen.__init__ = _wrapped_popen_init
    _log("Wrapped: subprocess.Popen.__init__")
    
    _log("Compatibility layer loaded successfully")