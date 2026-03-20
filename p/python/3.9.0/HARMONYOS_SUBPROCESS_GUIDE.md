# HarmonyOS 子进程执行 SELinux 限制与解决方案

> **文档版本**: 1.0  
> **更新日期**: 2026-03-20  
> **重要程度**: ⭐⭐⭐⭐⭐ (核心知识点)

---

## 一、问题现象

在 HarmonyOS 上，从用户编译的程序（Python、C/C++ 程序等）中创建子进程执行 SDK 工具（如 clang）时，子进程会静默失败（exit code 1），没有任何错误输出。但同样的命令在 shell 中直接执行是成功的。

### 典型表现

```bash
# 在 shell 中直接执行 - 成功
$ clang --version
clang version 15.0.4 ...

# 在 Python 中执行 - 失败
$ python3 -c "import os; os.system('clang --version')"
# (exit code 1, 无输出)

# 在 C 程序中执行 - 失败
$ ./my_program_that_calls_clang
# (exit code 1, 无输出)
```

---

## 二、根因分析

### 2.1 SELinux 域转换机制

HarmonyOS 使用 SELinux 强制访问控制，存在**域转换（Domain Transition）**机制：

| 场景 | 进程类型 | SELinux Context |
|------|----------|-----------------|
| Shell 进程 | 受信任进程 | `u:r:hishell_hap:s0` |
| Python 解释器 | 用户程序 | `u:r:adhoc_bin:s0` |
| 用户编译的 C 程序 | 用户程序 | `u:r:adhoc_bin:s0` |
| SDK clang-15 | 系统工具 | `u:object_r:hnp_file:s0` |
| 用户编译的文件 | 用户文件 | `u:object_r:hmdfs:s0` |

### 2.2 域转换流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        SELinux 域转换                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  hishell_hap:s0          执行用户程序           adhoc_bin:s0    │
│  (Shell 进程)   ───────────────────────>    (Python/C程序)      │
│                                                                 │
│  ✅ 可以执行 hnp_file    ───────────────>    ❌ 不能执行        │
│     (SDK 工具)                              hnp_file            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**关键点**：当 `hishell_hap` 域的进程执行 `hmdfs` 类型的文件时，SELinux 触发域转换，新进程进入 `adhoc_bin` 域，该域没有执行 `hnp_file` 类型文件的权限。

### 2.3 为什么静默失败

SDK 的 clang-15 是一个 109MB 的 ELF 二进制，当 `adhoc_bin` 域的进程尝试 `execve()` 它时：

1. `execve()` 系统调用成功（没有返回错误）
2. SELinux 在内核层面拦截了执行
3. 进程立即以 exit code 1 退出
4. 没有任何错误输出（因为二进制根本没有真正开始执行）

---

## 三、解决方案

### 3.1 管道绕过法（推荐）

**发现**：使用管道语法可以绕过 SELinux 限制！

```python
# 直接执行 - 失败
os.system("clang test.c -o test")  # exit code: 1

# 管道执行 - 成功！
os.system("clang test.c -o test | cat")  # exit code: 0
```

**原理**：管道强制 shell 创建子进程来执行管道的左侧命令。这个子进程的 SELinux 上下文可能具有不同的权限，能够执行 SDK 工具。

**正确实现**（使用 `pipefail` 获取真实退出码）：

```python
# HarmonyOS workaround
cmd_str = f"set -o pipefail; {cmd} 2>&1 | cat"
status = os.system(cmd_str)
```

### 3.2 验证结果

| 执行方式 | SDK 工具 | 用户程序 | 系统命令 |
|---------|---------|---------|---------|
| `fork() + execv()` | ❌ 失败 | ✅ 成功 | ❌ 失败 |
| `os.system()` | ❌ 失败 | ✅ 成功 | ❌ 失败 |
| `os.system("cmd | cat")` | ✅ **成功** | ✅ 成功 | ✅ **成功** |
| `system("cmd & wait")` | ⚠️ 不稳定 | ✅ 成功 | ⚠️ 不稳定 |

---

## 四、不同语言的解决方案

### 4.1 Python

**问题代码**：
```python
import os
pid = os.fork()
if pid == 0:
    os.execv("/path/to/clang", ["clang", "--version"])  # 失败
```

**解决方案**：
```python
import os
import shlex

def run_command(cmd):
    """HarmonyOS 兼容的命令执行"""
    cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
    
    # HarmonyOS: 使用管道绕过 SELinux
    if 'ohos' in sys.platform or 'harmonyos' in sys.platform:
        cmd_str = f"set -o pipefail; {cmd_str} 2>&1 | cat"
    
    status = os.system(cmd_str)
    return os.waitstatus_to_exitcode(status)

# 使用
run_command(["clang", "test.c", "-o", "test"])
```

### 4.2 C/C++

**问题代码**：
```c
#include <unistd.h>
#include <sys/wait.h>

int main() {
    pid_t pid = fork();
    if (pid == 0) {
        char *args[] = {"/path/to/clang", "--version", NULL};
        execv(args[0], args);  // 失败，静默退出
        _exit(1);
    }
    int status;
    waitpid(pid, &status, 0);
    // WEXITSTATUS(status) == 1
}
```

**解决方案 1**：使用 `system()` + 管道
```c
#include <stdlib.h>

int main() {
    // 使用管道语法
    int status = system("set -o pipefail; clang test.c -o test 2>&1 | cat");
    // WEXITSTATUS(status) == 0 表示成功
}
```

**解决方案 2**：通过 shell 脚本包装
```c
// 创建一个 shell 脚本来执行编译命令
int status = system("/bin/sh /path/to/wrapper.sh");
```

**解决方案 3**：使用 `popen()` 捕获输出
```c
#include <stdio.h>

FILE *fp = popen("clang --version 2>&1", "r");
// popen 内部使用 pipe，在某些情况下可以工作
char buffer[256];
while (fgets(buffer, sizeof(buffer), fp)) {
    printf("%s", buffer);
}
pclose(fp);
```

### 4.3 Shell 脚本

**问题**：从用户程序调用的 shell 脚本中执行 SDK 工具也会失败。

```bash
#!/bin/sh
# 这个脚本如果被 Python/C 程序调用，clang 会失败
clang --version
```

**解决方案**：
```bash
#!/bin/sh
# 使用管道语法
clang --version | cat
```

或者使用子 shell：
```bash
#!/bin/sh
# 子 shell 可能具有不同的权限
(clang --version) | cat
```

### 4.4 Makefile

**问题**：`make` 调用的命令也会失败。

```makefile
# 这个规则会失败
%.o: %.c
    $(CC) -c $< -o $@
```

**解决方案**：修改 SHELL 或命令
```makefile
# 方案 1: 使用管道
%.o: %.c
    $(CC) -c $< -o $@ | cat

# 方案 2: 修改 SHELL 变量
SHELL = /bin/sh -c 'set -o pipefail; eval "$$1 | cat"' _SHELL_
```

---

## 五、完整测试矩阵

### 5.1 测试环境

- 系统：HarmonyOS HongMeng Kernel 1.11.0
- Python：3.9.0 (本地编译)
- clang：15.0.4 (SDK 预装)
- SELinux：enforcing

### 5.2 测试结果汇总

| 目标程序 | direct_exec | system() | system(\|cat) | system(&wait) | shell_exec | shell(\|cat) |
|---------|-------------|----------|---------------|---------------|------------|--------------|
| clang-15 (SDK binary) | ❌ | ❌ | ✅ | ⚠️ | ❌ | ✅ |
| clang (SDK script) | ❌ | ❌ | ✅ | ⚠️ | ❌ | ✅ |
| /bin/ls (system) | ❌* | ❌* | ✅ | ⚠️ | ❌* | ✅ |
| user static binary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| user dynamic binary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

注：`❌*` 表示因目录权限而非 exec 权限导致失败

### 5.3 测试代码

**Python 测试**：
```python
import os

CLANG = "/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native/llvm/bin/clang-15"

# 测试 1: fork + execv (失败)
pid = os.fork()
if pid == 0:
    os.execv(CLANG, [CLANG, "--version"])
    os._exit(1)
_, status = os.waitpid(pid, 0)
print(f"fork+execv: {os.waitstatus_to_exitcode(status)}")  # 输出: 1

# 测试 2: os.system (失败)
ret = os.system(f"{CLANG} --version")
print(f"system: {os.waitstatus_to_exitcode(ret)}")  # 输出: 1

# 测试 3: os.system + 管道 (成功！)
ret = os.system(f"set -o pipefail; {CLANG} --version 2>&1 | cat")
print(f"system+pipe: {os.waitstatus_to_exitcode(ret)}")  # 输出: 0
```

**C 测试**：
```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main() {
    const char *clang = "/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native/llvm/bin/clang-15";
    
    // 测试 1: fork + execv (失败)
    pid_t pid = fork();
    if (pid == 0) {
        char *args[] = {(char*)clang, "--version", NULL};
        execv(clang, args);
        _exit(1);
    }
    int status;
    waitpid(pid, &status, 0);
    printf("fork+execv: %d\n", WEXITSTATUS(status));  // 输出: 1
    
    // 测试 2: system (失败)
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version", clang);
    status = system(cmd);
    printf("system: %d\n", WEXITSTATUS(status));  // 输出: 1
    
    // 测试 3: system + 管道 (成功！)
    snprintf(cmd, sizeof(cmd), "set -o pipefail; %s --version 2>&1 | cat", clang);
    status = system(cmd);
    printf("system+pipe: %d\n", WEXITSTATUS(status));  // 输出: 0
    
    return 0;
}
```

---

## 六、注意事项

### 6.1 管道退出码处理

管道默认返回最后一个命令的退出码。使用 `set -o pipefail` 获取真实退出码：

```bash
# 错误示例：clang 失败但 exit code 为 0
clang bad.c -o bad | cat
echo $?  # 输出: 0 (因为 cat 成功)

# 正确示例：使用 pipefail
set -o pipefail; clang bad.c -o bad | cat
echo $?  # 输出: 1 (clang 的真实退出码)
```

### 6.2 输出捕获

管道会改变标准输出，如果需要捕获输出：

```python
# 使用 tee 保留输出
import os
cmd = "clang --version 2>&1 | tee /dev/stderr | cat"
os.system(cmd)

# 或使用临时文件
cmd = "clang --version > /tmp/output.txt 2>&1 | cat; cat /tmp/output.txt"
os.system(cmd)
```

### 6.3 性能影响

管道会引入额外的进程（cat），但对于编译任务来说影响微乎其微。

### 6.4 不稳定的方案

`& wait` 方式有时成功有时失败，不推荐使用：

```python
# 不稳定，有时 exit 0 但文件没生成
os.system("clang test.c -o test & wait")
```

---

## 七、最佳实践

### 7.1 平台检测

```python
import sys

def is_harmonyos():
    """检测是否运行在 HarmonyOS 上"""
    platform = sys.platform.lower()
    return 'harmonyos' in platform or 'ohos' in platform
```

### 7.2 统一封装

```python
import os
import shlex
import sys

def run_command(cmd, env=None, capture_output=False):
    """
    跨平台兼容的命令执行函数
    
    Args:
        cmd: 命令列表，如 ["clang", "test.c", "-o", "test"]
        env: 可选的环境变量字典
        capture_output: 是否捕获输出
    
    Returns:
        (exitcode, output) 元组
    """
    # 构建命令字符串
    cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
    
    # 处理环境变量
    if env:
        env_parts = [f"{k}={shlex.quote(str(v))}" for k, v in env.items()]
        cmd_str = 'env ' + ' '.join(env_parts) + ' ' + cmd_str
    
    # HarmonyOS 特殊处理
    if 'ohos' in sys.platform.lower() or 'harmonyos' in sys.platform.lower():
        if capture_output:
            cmd_str = f"set -o pipefail; {cmd_str} 2>&1 | cat"
        else:
            cmd_str = f"set -o pipefail; {cmd_str} 2>&1 | cat"
    
    # 执行
    status = os.system(cmd_str)
    exitcode = os.waitstatus_to_exitcode(status)
    
    return exitcode
```

### 7.3 构建系统集成

对于使用 Autotools/CMake/Makefile 的项目，可以在配置阶段检测：

```bash
# configure 脚本中
AC_MSG_CHECKING([whether pipe workaround is needed])
if test "$host_os" = "linux-ohos"; then
    AC_MSG_RESULT([yes])
    PIPE_WORKAROUND=" | cat"
else
    AC_MSG_RESULT([no])
    PIPE_WORKAROUND=""
fi
AC_SUBST(PIPE_WORKAROUND)
```

---

## 八、相关文件

| 文件 | 说明 |
|------|------|
| `_bootsubprocess.py` | Python 子进程模块补丁 |
| `0006-Lib-_bootsubprocess.py-HarmonyOS-fix.patch` | 补丁文件 |
| `/proc/self/attr/current` | 进程 SELinux context 查询 |

---

## 九、参考资料

- SELinux Domain Transitions: https://selinuxproject.org/page/NB_MLS
- HarmonyOS 应用安全模型: (内部文档)
- Python subprocess 模块: https://docs.python.org/3/library/subprocess.html

---

*文档维护: OpenDesk 项目组*  
*最后更新: 2026-03-20*