# HarmonyOS 子进程执行完整指南

> **版本**: 3.0 | **更新**: 2026-03-26 | **重要度**: ⭐⭐⭐⭐⭐  
> 关联: [README.md](./README.md) · [MISSING_ADAPTATION_SCAN.md](./reports/MISSING_ADAPTATION_SCAN.md) · [UPSTREAM_ADAPTATION_ANALYSIS.md](./reports/UPSTREAM_ADAPTATION_ANALYSIS.md)

---

## 速查：一句话结论

**鸿蒙上 `posix_spawn()` + `os.pipe()` 完全可用，`fork()` 也可用。** SELinux 域转换仅限制 SDK 工具（如 clang），Python 子进程和系统命令通过 `posix_spawn` 正常执行。补丁 0020 修复了 0016 遗留的临时文件方案导致的 pipe 数据丢失问题。

---

## 一、问题现象

用户编译的程序（Python、C/C++）中创建子进程执行 SDK 工具（如 clang）时，**静默失败**（exit code 1，无输出）。Shell 中直接执行同一命令则正常。

```bash
# Shell 直接执行 ✅
$ clang --version
clang version 15.0.4 ...

# Python 中执行 ❌
$ python3 -c "import os; os.system('clang --version')"
# (exit code 1, 无输出)

# C 程序中执行 ❌
$ ./my_program
# (exit code 1, 无输出)
```

---

## 二、根因：SELinux 域转换

### 2.1 域转换机制

HarmonyOS 使用 SELinux 强制访问控制：

| 场景 | 进程类型 | SELinux Context |
|------|----------|-----------------|
| Shell 进程 | 受信任 | `u:r:hishell_hap:s0` |
| Python / 用户程序 | 用户程序 | `u:r:adhoc_bin:s0` |
| SDK clang-15 | 系统工具 | `u:object_r:hnp_file:s0` |

```
hishell_hap:s0 ──执行用户程序──→ adhoc_bin:s0
 (Shell)                          (Python/C)

 ✅ 可执行 hnp_file           ❌ 不能执行 hnp_file
    (SDK 工具)                    (SDK 工具)
```

**关键点**：`hishell_hap` 域执行 `hmdfs` 文件 → 触发域转换 → 进入 `adhoc_bin` 域 → 无权执行 `hnp_file` 类型的 SDK 工具。

### 2.2 为什么静默失败

`execve()` 系统调用本身成功（不返回错误），但 SELinux 在内核层面拦截执行，进程立即以 exit code 1 退出，二进制根本没开始执行。

---

## 三、鸿蒙子进程能力边界（C 级实测）

> 测试代码: `/storage/Users/currentUser/python/subprocess-tests/`  
> 测试文件: `test_syscalls.c`, `test_fork_clang.c`, `test_spawn*.c`

### 3.1 Python 进程的 fd 环境

Python 进程在鸿蒙上的标准 I/O fd **是 socket 而非终端**：

```
fd 0: socket:[628771]    ← stdin 是 socket（非终端/文件）
fd 1: <redirected>       ← stdout 重定向到文件
fd 2: <redirected>       ← stderr 重定向到文件
```

**影响**：子进程继承这些 fd 后，pipe 重定向行为可能异常（见 §4.2）。

### 3.2 完整测试矩阵

#### 系统调用级（C 代码直接测试）

| 原语 | SDK 工具 (clang) | 系统命令 (/bin/ls) | 用户编译的程序 |
|------|:---:|:---:|:---:|
| `fork() + execvp()` | ❌ SELinux 拦截 | ⚠️ 受目录权限影响 | ✅ 正常 |
| `posix_spawnp()` + pipe | ❌ SELinux 拦截 | ✅ 输出正确 | ✅ 正常 |
| `posix_spawnp()` + `USEVFORK` | ❌ SELinux 拦截 | ✅ 正常 | ✅ 正常 |
| `posix_spawnp()` (无 flags) | ❌ SELinux 拦截 | ✅ 正常 | ✅ 正常 |
| `system("cmd \| cat")` | ✅ **Pipe 绕过** | ✅ 正常 | ✅ 正常 |
| `system("cmd & wait")` | ⚠️ 不稳定 | ✅ 正常 | ✅ 正常 |

#### Python 层测试（subprocess 模块）

| 测试 | 描述 | 旧结果(0016) | 新结果(0020) | 说明 |
|------|------|:------:|:------:|------|
| T0 | os.fork() 可用性 | - | ✅ | fork() 正常，鸿蒙内核支持 |
| T1 | Popen+wait (无 PIPE) | ❌ | ✅ | Python 子进程 + env dict 均正常 |
| T2 | stderr=PIPE | ❌ | ✅ | stderr 正确捕获 |
| T3 | PIPE+communicate (stdout) | ✅ | ✅ | 改用真正 os.pipe()，不再需要临时文件 |
| T4 | subprocess.run() capture | ✅ | ✅ | capture_output 正常 |
| T5 | error capture | ❌ | ✅ | stderr 正确捕获退出错误信息 |
| T6 | stdin pipe (双向) | ❌ | ✅ | stdin→子进程→stdout 全链路通 |
| T3b | stdout+stderr 双 PIPE | - | ✅ | 两个 pipe 同时工作 |
| T-env | env dict + PIPE | ❌ | ✅ | execve env 类型 bug 已修复 |

> **补丁 0020 修复内容**：
> 1. stdout/stderr PIPE 恢复使用 `os.pipe()`（移除 `_ohos_make_temp_pair` 临时文件方案）
> 2. `_python_fork_exec()` 的 `os.execve()` 使用原始 `env` dict 而非 `env_list`（list of bytes）
> 3. 移除 posix_spawn 路径对 `_OHOS_PIPE_WORKAROUND` 的禁用条件

### 3.3 关键结论

1. **`fork()` 在鸿蒙上存在**，`posix_spawn()` 完全可用且是推荐的子进程启动方式
2. **`os.pipe()` + `posix_spawn` 在鸿蒙上正常工作**，不需要临时文件方案
3. **Pipe 数据丢失问题已彻底解决**：根因是 0016 补丁的临时文件方案替代了真正的 pipe
4. **`os.execve()` 的 `env` 参数必须是 dict**，不能传 list of bytes（Python 层限制，非系统调用限制）
5. **SELinux 域转换限制**仅影响 SDK 工具（如 clang），不影响 Python 子进程和系统命令
6. **测试必须用 SDK 工具作锚点**（如 clang），不能用 echo/ls 等（它们是 shell 内置或系统命令，走不同路径）

---

## 四、解决方案

按层级从基础到高级排列。

### 4.1 Pipe 绕过 SELinux（基础方案）

**原理**：管道强制 shell 创建子进程执行管道左侧命令，该子进程的 SELinux 上下文具有不同权限。

```python
import os, shlex, sys

def run_with_pipe(cmd):
    """Pipe 绕过方案 — 适用于 os.system / subprocess"""
    cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
    cmd_str = f"set -o pipefail; {cmd_str} 2>&1 | cat"
    return os.waitstatus_to_exitcode(os.system(cmd_str))

# 使用
run_with_pipe(["clang", "test.c", "-o", "test"])  # exit code: 0
```

**注意**：必须用 `set -o pipefail` 获取真实退出码，否则 pipe 返回的是最后一个命令（cat）的退出码。

### 4.2 ~~临时文件替代 Pipe~~ → 已废弃

> **补丁 0020 后此方案不再需要。** 调试发现鸿蒙的 `posix_spawn` + `os.pipe()` 完全可用，
> 临时文件方案反而导致了 `communicate()` 读不到数据的问题。已恢复使用标准 `os.pipe()`。

**历史记录**（保留供参考）：
>
> **原问题**：使用 `posix_spawnp()` + pipe 重定向 stderr 时，子进程输出可能**完全丢失**（0 bytes）。
> 原因是 Python 进程的 fd 0/1/2 是 socket，子进程继承后 pipe 重定向异常。
>
> **原方案**：在 `Popen._get_handles()` 层面用临时文件替代 pipe。
> **实际根因**：临时文件本身导致了数据丢失（文件 fd 不支持 select 事件通知），
> 而真正的 `os.pipe()` 在 posix_spawn 路径下工作正常。

### 4.3 fd 0/1/2 /dev/null 保护

Python 进程的 fd 0 是 socket，子进程继承后可能导致 I/O 混乱。在 fork 后立即保护：

```python
# 在子进程中，fork 后 exec 前
devnull = os.open(os.devnull, os.O_RDWR)
os.dup2(devnull, 0)  # stdin -> /dev/null
os.dup2(devnull, 2)  # stderr -> errpipe 或 devnull
```

### 4.4 fork_exec 纯 Python Fallback

Python 3.9 的 `subprocess.py` 对 C 扩展 `_posixsubprocess` 有**硬依赖**，缺失时整个模块不可用。Python 3.12+ 已将 C 逻辑内联到 `subprocess.py`。

在 3.9 上实现相同的 fallback：

```python
def _python_fork_exec(args, executable_list, close_fds, fds_to_keep,
                     cwd, env_list, p2cread, p2cwrite, c2pread, c2pwrite,
                     errread, errwrite, errpipe_read, errpipe_write,
                     restore_signals, start_new_session, gid, gids, uid,
                     umask, preexec_fn):
    """Pure Python fork+exec (参考 Python 3.12+ 实现)"""
    pid = os.fork()
    if pid == 0:
        # 子进程：设置 fd、执行 exec
        ...
    return pid
```

同时修改 `_use_posix_spawn()` 使其在鸿蒙上返回 `True`：

```python
def _use_posix_spawn():
    ...
    if sys.platform.startswith(('ohos', 'harmonyos')):
        if hasattr(os, 'posix_spawn'):
            return True
        return False
```

### 4.5 communicate() Bug 修复

`communicate()` 的简单路径用 `elif` 链，只能处理一个 pipe。当 stdout 和 stderr 都是 PIPE 时，只读一个：

```python
# 修复：检查 pipe 数量
pipe_count = sum(1 for p in [self.stdout, self.stderr] if p is not None)
if pipe_count == 1:
    # 简单路径
elif pipe_count >= 2:
    # 复杂路径（select/poll 或顺序读取）
```

---

## 五、多语言解决方案

### 5.1 Python

```python
import os, shlex, sys

def run_command(cmd, capture=False):
    """鸿蒙兼容的命令执行"""
    cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
    if 'ohos' in sys.platform or 'harmonyos' in sys.platform:
        cmd_str = f"set -o pipefail; {cmd_str} 2>&1 | cat"
    return os.waitstatus_to_exitcode(os.system(cmd_str))
```

### 5.2 C/C++

```c
// 方案 1: system() + pipe（推荐）
int status = system("set -o pipefail; clang test.c -o test 2>&1 | cat");

// 方案 2: popen()（捕获输出）
FILE *fp = popen("clang --version 2>&1", "r");
// popen 内部使用 pipe，在某些情况下可工作
char buf[256];
while (fgets(buf, sizeof(buf), fp)) printf("%s", buf);
pclose(fp);
```

### 5.3 Shell / Makefile

```bash
# Shell: 管道语法
clang --version | cat

# Makefile: 修改规则
%.o: %.c
	$(CC) -c $< -o $@ | cat

# Makefile: 或修改 SHELL（影响所有规则）
SHELL = /bin/sh -c 'set -o pipefail; eval "$$1 | cat"' _SHELL_
```

### 5.4 构建系统集成（Autotools）

```m4
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

## 六、注意事项

| 问题 | 说明 |
|------|------|
| **pipefail 必须加** | 否则 `clang bad \| cat` 返回 0（cat 的退出码） |
| **2>&1 必须** | 否则 stderr 不走 pipe，丢失错误信息 |
| **& wait 不稳定** | 有时 exit 0 但文件没生成，不推荐 |
| **cat 有性能开销** | 额外进程，但对编译任务影响可忽略 |
| **输出捕获** | 需要捕获输出时用 `tee` 或临时文件 |

---

## 七、构建验证成果

### 7.1 扩展模块编译（Python 3.9.0 全量构建）

| 类别 | 数量 | 说明 |
|------|------|------|
| ✅ 编译+导入成功 | **64** | math, json, pickle, xml, unicodedata, decimal 等 |
| ⚠️ 编译成功但导入失败 | 2 | _gdbm, _lzma（运行时库路径问题） |
| ❌ 编译失败 | 1 | _ctypes（ffi 头文件/库找不到） |
| ⏭️ 依赖缺失未编译 | 10 | _ssl(已修复), _sqlite3 等 |

关键修复：**libintl_gettext 问题**修复后 CJK 编解码模块全部编译成功。

### 7.2 C 扩展包四关卡测试（2026-03-26）

| 包 | 获取 | 编译 | 导入 | 运行 | 判定 |
|---|---|---|---|---|---|
| msgpack 1.1.2 | ✅ | ✅ | ✅ | ✅ | compatible |
| regex 2026.1.15 | ✅ | ✅ | ✅ | ✅ | compatible |
| cffi 2.0.0 | ✅ | ✅ | ✅ | ✅ | compatible |
| yarl 1.22.0 | ✅ | ✅ | ✅ | ✅ | compatible |
| multidict 6.7.1 | ✅ | ✅ | ✅ | ⚠️ setitem异常 | partial |
| websockets 15.0.1 | ✅ | ✅ | ✅ | ⚠️ C加速不可用 | partial |
| greenlet 3.2.5 | ✅ | ✅ | ❌ | — | import 失败 |
| ujson 5.11.0 | ✅ | ✅ | ❌ | — | import 失败 |
| numpy 1.26.4 | ✅ | ✅ | ❌ | — | import 失败 |

**根因**：`libpython3.9.so` 不导出动态符号（`nm -D` 返回 0 个 text 符号），greenlet/ujson/numpy 的 .so 运行时找不到 `PyType_IsSubtype` 等 C API。修复方式：重新编译 Python（`--enable-shared`）。

### 7.3 multiprocessing

```
multiprocessing spawn Pool: OK         ← ✅ spawn 方式可用
Process(lambda): AttributeError         ← lambda 无法 pickle（非鸿蒙特有）
```

---

## 八、调试方法论与踩坑清单

### 8.1 三层调试法

```
第一层: C 级系统调用测试 → 确认内核支持哪些原语（fork/posix_spawn/pipe）
  ↓
第二层: Python subprocess 层 → 确认 Python 层行为和限制
  ↓
第三层: 应用层测试 → 确认 pip/venv/multiprocessing 等实际场景
```

### 8.2 踩坑清单

| # | 踩坑 | 症状 | 正确做法 |
|---|------|------|---------|
| 1 | 用 echo 测试 subprocess | echo 通过但 clang 失败 | **用 SDK 工具作锚点** |
| 2 | ~~pipe 在鸿蒙正常工作~~ | ~~子进程输出丢失~~ | ~~临时文件替代~~ **已废弃：os.pipe() + posix_spawn 正常工作** |
| 3 | fd 0/1/2 是 socket | 子进程 I/O 混乱 | fork 后 dup2 到 /dev/null（_python_fork_exec 中已处理） |
| 4 | communicate() elif 链 | 双 pipe 只读一个 | 0020 修复后双 pipe 正常（用真正的 pipe 而非临时文件） |
| 5 | cleanup 关 read_fd | close 时报错 | cleanup 只删文件不关 fd |
| 6 | 移除 _posixsubprocess.so | subprocess 完全不可用 | 纯 Python fallback（_python_fork_exec） |
| 7 | 不用 pipefail | 错误退出码被吞 | `set -o pipefail` |
| 8 | _ohos_make_temp_pair 替代 pipe | communicate() 读不到数据 | **0020 修复：恢复使用 os.pipe()** |
| 9 | execve 传 list of bytes | AttributeError: 'list' has no keys | **0020 修复：传原始 env dict** |
| 10 | _OHOS_PIPE_WORKAROUND 禁用 posix_spawn | 默认走 fork_exec 路径 | **0020 修复：移除禁用条件** |

---

## 九、Python 3.12 适配路线图

### 9.1 有利因素

| 3.12+ 变化 | 影响 |
|-----------|:---:|
| `_posixsubprocess.c` 内联到 subprocess.py | ✅ 不再需编译 C 扩展 |
| 更完善的 `posix_spawn` 路径 | ✅ 可直接启用 |
| 移除 `distutils` | ✅ 减少维护负担 |

### 9.2 仍需处理

| 问题 | 3.12 预期 |
|------|:---:|
| SELinux 限制 SDK 工具 | **仍需** pipe 绕过 |
| Pipe 数据丢失 | ~~可能已修复~~ **已修复（补丁 0020）** |
| fd 0/1/2 socket | **仍需** /dev/null 保护 |
| multiprocessing fork 默认 | **可能**上游已修复 |
| threading.get_native_id | **仍需** 加 `__OHOS__` |

### 9.3 适配步骤

```
1. 检查 3.12 configure.ac 对 HarmonyOS 的支持
2. 尝试原生编译（不应用任何 patch）
3. 复用 subprocess-tests/ 中的 C 级测试
4. 重点测试 subprocess 和 multiprocessing
5. 对比 3.9 的 patch 列表，识别不再需要的 patch
6. 运行完整测试套件
```

---

## 十、相关文件

| 文件 | 说明 |
|------|------|
| `patches/0006` | `_bootsubprocess.py` 补丁（构建阶段） |
| `patches/0009` | `_harmonyos_compat.py` 补丁（运行时 monkey-patch） |
| `patches/0010` | `site.py` 自动加载兼容层 |
| `patches/0020` | subprocess pipe/execve/posix_spawn 修复（替代 0016 的临时文件方案） |
| `reports/MISSING_ADAPTATION_SCAN.md` | P0-2/P0-3/P0-5/P1-11 等源码级遗漏修复方案 |
| `reports/UPSTREAM_ADAPTATION_ANALYSIS.md` | 上游合入策略 |
| `/storage/.../subprocess-tests/` | C 级测试代码（可直接复用于 3.12） |

---

*维护: OpenDesk 项目组 · 最后更新: 2026-03-26*
