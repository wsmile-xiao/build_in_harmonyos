# ⚡ 错误模式：运行时与测试类 (E049-E067)

> **父文档**: [error-patterns.md](./error-patterns.md)
> **类别**: 运行时行为 / 测试框架 / POSIX 差异 / 安全机制 / 编码规范
> **适用阶段**: Phase 2.5 测试 / Phase 3 收尾验证

---

## 错误模式列表

## E049: find_library 崩溃（ldconfig 不存在）

### 错误特征

```python
from ctypes.util import find_library
find_library("c")
# SubprocessError: Command '('/sbin/ldconfig', '-p')' returned non-zero exit status 127.
```

### 根因

HarmonyOS 没有 `/sbin/ldconfig`（Linux 标准的共享库缓存管理工具）。`ctypes.util.find_library()` 内部调用 `_findSoname_ldconfig()` 时，直接执行 `ldconfig -p` 命令，因命令不存在而触发 `SubprocessError`。

**问题链**：
```
ctypes.util.find_library(name)
    ↓
_findSoname_ldconfig(name, True)
    ↓
subprocess.run(['/sbin/ldconfig', '-p'], ...)
    ↓
ldconfig 不存在 → FileNotFoundError → SubprocessError
```

### 影响范围

| 影响程度 | 说明 |
|----------|------|
| 🔴 严重 | 所有调用 `find_library()` 的代码直接崩溃（SubprocessError） |
| 🟡 中等 | 返回 `None` 本身是合法行为（表示找不到库），崩溃才是问题 |

**受影响的三方库**：

| 三方库 | 影响场景 |
|--------|---------|
| cffi | `ffi.dlopen()` 内部调用 find_library 查找共享库 |
| trio | 调用 find_library 进行 DNS 解析器发现 |
| Django GIS | Spatialite 库查找依赖 find_library |
| Sphinx | 文档构建工具的部分扩展依赖 find_library |

### 验证命令

```python
from ctypes.util import find_library

# 修复前：SubprocessError
# find_library("c") → SubprocessError: Command '('/sbin/ldconfig', '-p')' returned non-zero exit status 127.

# 修复后（补丁 0022）：安全返回 None
# find_library("c") → None
```

### 解决方案

**补丁 0022**（Python 3.9.0）：在 `Lib/ctypes/util.py` 的 `_findSoname_ldconfig()` 函数头部跳过鸿蒙平台：

```python
# Lib/ctypes/util.py _findSoname_ldconfig() 函数
import sys

def _findSoname_ldconfig(name, is64):
    # HarmonyOS has no /sbin/ldconfig, skip to avoid SubprocessError
    if sys.platform.startswith(('ohos', 'harmonyos')):
        return None
    # ... original code ...
```

修复后 `find_library()` 安全返回 `None`（表示找不到共享库），与无 ldconfig 的 Linux 系统行为一致。

### 涉及软件

Python 3.9.0（补丁 0022）、cffi、trio、Django、Sphinx

---

## E050: HMDFS 符号链接不可跟踪导致链接器找不到库

### 错误特征

```
ld.lld: error: unable to find library -lpython3.9
pip install xxx  →  "error: command 'clang' failed with exit code 1"
```

### 根因

HMDFS 文件系统不正常跟踪符号链接。`os.path.exists()` 对符号链接返回 `False`，动态链接器（ld.lld）通过符号链接搜索库文件时也无法找到目标。

```
make install 创建:
  libpython3.9.so → libpython3.9.so.1.0  (符号链接)

Python 进程中:
  os.path.exists("libpython3.9.so")      → False  (符号链接不可见)
  os.path.exists("libpython3.9.so.1.0")  → True   (真实文件可见)

链接器搜索:
  -L/usr/local/lib -lpython3.9
    → 找 libpython3.9.so → 符号链接 → 无法解析 → "unable to find library"
```

### 影响范围

- `pip install` 编译所有 C 扩展包时链接失败
- 任何通过 `-l` 链接符号链接 `.so` 的操作都受影响

### 验证命令

```python
import os
symlink = '/usr/local/lib/libpython3.9.so'
real = '/usr/local/lib/libpython3.9.so.1.0'
print(f'symlink exists: {os.path.exists(symlink)}')  # False
print(f'real file exists: {os.path.exists(real)}')    # True
```

### 解决方案

**用文件副本替代符号链接**：

```bash
# 删除符号链接
rm /usr/local/lib/libpython3.9.so
# 复制真实文件
cp /usr/local/lib/libpython3.9.so.1.0 /usr/local/lib/libpython3.9.so
```

对于 Python 的 `make install`，补丁 0024 将 `$(LN_FORCE)` 改为 `$(HARDLINK)`（鸿蒙上为 `cp -p`）：

```makefile
# Makefile.pre.in sharedinstall
# 修改前：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(LN_FORCE) $(INSTSONAME) $(LDLIBRARY))
# 修改后：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(HARDLINK) $(INSTSONAME) $(LDLIBRARY))
```

### 代价

额外占用约 10MB 磁盘空间（共享库的副本）。

### 涉及软件

Python 3.9.0（补丁 0024）、任何使用 `make install` + 符号链接分发共享库的 C/C++ 项目

---

## E051: 未实现 syscall 触发 SIGSYS 导致进程崩溃

### 错误特征

- 进程意外退出，无错误信息输出
- Exit code 159（128 + 31 = SIGSYS）
- 可能产生 core dump
- Python: `OSError` 或直接 `killed`，无 traceback

### 触发条件

调用鸿蒙内核未实现的 syscall，已确认的包括：
- `setreuid()` / `setregid()` — **SIGSYS 不可捕获，进程直接终止**
- `chroot()` — SIGSYS 可捕获但返回垃圾值
- `clock_settime()` — SIGSYS 可捕获但 errno 不确定

### 根因分析

鸿蒙内核对未实现的 syscall 发送 SIGSYS 信号（signal 31），但其行为与 Linux seccomp SIGSYS **完全不同**：

| 特性 | Linux seccomp SIGSYS | HarmonyOS 未实现 syscall |
|------|---------------------|------------------------|
| sigaction 可捕获？ | ✅ 全部可捕获 | ❌ 部分不可捕获（setreuid/setregid） |
| handler 中 si_syscall | ✅ 包含 syscall 号 | ❌ 不确定 |
| handler 返回后 | 返回 -ENOSYS | 进程被终止（不可捕获时） |

**关键发现**：`setreuid`/`setregid` 的 SIGSYS 不触发任何 signal handler（包括 C 层 sigaction），进程直接被终止。这意味着**信号处理方案完全不可行**，必须在源码层面拦截。

### 验证命令

```bash
# Python 层面
python3 -c "import os; os.setreuid(0,0)"
# 预期: exit code 159 (killed by SIGSYS)

# C 层面
cat > test_sigsys.c << 'EOF'
#include <unistd.h>
int main() {
    setreuid(0, 0);
    return 0;
}
EOF
clang test_sigsys.c -o test_sigsys && ./test_sigsys
echo "exit=$?"  # 159
```

### 解决方案

在 C 源码中用 `#ifdef __OHOS__` 守卫，在 syscall 调用前直接返回 ENOSYS：

```c
int some_function(...) {
#ifdef __OHOS__
    /* HarmonyOS: unimplemented syscall sends uncatchable SIGSYS.
       Return ENOSYS to avoid process death. */
    errno = ENOSYS;
    return -1;
#endif
    return actual_syscall(...);
}
```

**为什么不用信号处理？**
- Python `signal.signal(signal.SIGSYS, handler)` → ❌ 进程仍 core dump
- C `sigaction(SIGSYS, &sa, NULL)` → ❌ setreuid/setregid 不触发 handler
- C handler + longjmp → ❌ setreuid/setregid 不触发 handler

### 编译注意事项

- `__OHOS__` 由鸿蒙 SDK 的 clang 自动定义，无需额外 `-D` 参数
- 编译器会警告原始 syscall 调用变为不可达代码（`code will never be executed`），这是预期的
- 修改 C 源码后需要重新编译并链接

### 影响范围

所有调用未实现 syscall 的 C/C++ 程序。不仅限于 Python，任何从 Linux 移植到鸿蒙的软件都可能遇到。

### 相关补丁

- Python 3.9.0: 0039（timemodule.c clock_settime）、0040（posixmodule.c setreuid/setregid/chroot）

### 相关知识

- `ohos-adaptation-patterns.md` — "未实现 syscall 提前拦截"适配模式
- `harmonyos-specifics.md` — SIGSYS 信号行为章节

---

## E052: rpath 缺失导致子进程找不到 libpython

### 错误特征

```
rpath, libpython, LD_LIBRARY_PATH, 子进程, exit 127, libpython3.9.so, subprocess
```

### 根因

子进程启动时无法通过 RPATH 或 LD_LIBRARY_PATH 找到 libpython 共享库。

### 解决方案

确保主程序和所有子进程可执行文件的 RPATH 正确设置，或通过 activate.sh 设置 LD_LIBRARY_PATH。

### 涉及软件

Python 3.9.0 可移植打包

---

## E053: cc1plus 不可用，必须使用 clang++

### 错误特征

```
cc1plus: error: unrecognized command-line option '-Wno-deprecated-register'
CXX compiler cannot create executables
configure: error: C++ compiler cannot create executables
```

或在软件内部调用 C++ 编译器时失败，例如 Python 3.9.0 编译 `_ctypes` 模块：

```
cc1plus: error: unrecognized option '-Wno-unused-result'
```

### 根因

鸿蒙 SDK 工具链**不提供 `cc1plus`**（GCC 的 C++ 编译器前端）。鸿蒙使用 LLVM/Clang 工具链，
`clang++` 是 C++ 编译器，但部分 autotools 项目的 configure 脚本或 Makefile 硬编码调用 `cc1plus`，
或者 configure 的 C++ 编译器检测逻辑在 clang++ 上误判。

**问题链**：
```
configure 或 Makefile 调用 C++ 编译器
    ↓
默认使用 g++ 或检测到 cc1plus → 不存在 → 失败
    ↓
或 clang++ 被检测为 C++ 编译器但编译参数不兼容 → 编译器报错
```

### 验证命令

```bash
# 确认 cc1plus 不存在
which cc1plus  # 不存在

# 确认 clang++ 可用
which clang++  # /data/service/hnp/bin/clang++
clang++ --version
```

### 解决方案

**方案 1：显式指定 C++ 编译器为 clang++**

```bash
export CXX=clang++
./configure --prefix=$HOME/usr/local CXX=clang++
```

**方案 2：确保 CXX 环境变量在 configure 之前设置**

```bash
export CC=clang
export CXX=clang++
# 确保 CXX 被正确检测
./configure --prefix=$HOME/usr/local
grep "CXX" config.log | head -5
```

**方案 3：如果 Makefile 硬编码了 cc1plus 调用**

```bash
# 搜索硬编码的 cc1plus
grep -rn 'cc1plus' Makefile* configure.ac
# 替换为 clang++
sed -i 's/cc1plus/clang++/g' Makefile*
```

### 影响范围

所有使用 C++ 代码且 configure 脚本不正确检测 C++ 编译器的 autotools 项目。

### 涉及软件

Python 3.9.0（`_ctypes` 模块编译）、其他包含 C++ 代码的 autotools 项目

### 相关知识

- [error-patterns-core.md E012](./error-patterns-core.md#e012-找不到-llvm-ar) — LLVM 工具链配置
- [build-systems.md §3](build-systems.md#3-autotools-适配) — Autotools 适配策略

> 来源：`archives/p/python/3.9.0/manifest.yaml`

---

## E054: 外来二进制首次执行被安全确认弹窗阻止

### 错误特征

- 编译产物在 `make install` 后 Permission denied
- `make check` 中测试用例全部失败（误判为功能问题）
- 首次手动执行后问题消失

### 根因

鸿蒙安全机制要求用户确认非系统预装二进制的执行权限。

### 修复方案

1. `make install` 后手动执行一次二进制触发确认
2. 批量触发：`find $PREFIX/bin -type f -exec {} --version \;`
3. `make check` 前确保所有产物已完成确认

### 参考档案

`archives/c/coreutils/9.10/`

### 知识层级

L1 平台真理

### 相关章节

[harmonyos-specifics.md §18](harmonyos-specifics.md#18-外来二进制首次执行确认弹窗)

---

## E055: posix_spawn 与 fork+exec 行为差异（Python 3.12+）

### 错误特征

```
test__use_vfork: AssertionError (mock _fork_exec 不触发)
test_exception_errpipe_normal: FileNotFoundError (直接报错，不走 errpipe)
test_restore_signals: FileNotFoundError ('cat' 找不到)
test_bytes_program: FileNotFoundError (b'true' 是 shell 内建命令)
```

### 根因

Python 3.12 `subprocess.py` 在 musl/HarmonyOS 上 `_USE_POSIX_SPAWN=True`，所有子进程通过 `os.posix_spawn()` 启动而非 `fork()+exec()`：

| 行为差异 | fork+exec | posix_spawn |
|---------|----------|-------------|
| errpipe 机制 | ✅ 子进程通过 errpipe 传错 | ❌ 父进程直接报错 |
| shell 内建命令 | ✅ shell 处理后 exec | ❌ `true`/`cd` 不可直接 exec |
| vfork 标志 | `_USE_VFORK` 控制是否用 vfork | 无意义（不用 fork） |

**修复方案**：运行时检测 `subprocess._USE_POSIX_SPAWN` 并 skip 受影响测试（补丁 0116）

---

## E056: @unittest.skipIf reason 换行反转导致 IndentationError（P0）

### 错误特征

```
IndentationError: unexpected indent
    @unittest.skipIf(condition,
                      "long reason wraps"
                      )
def test_something(self):   # ← 被识别为缩进错误
```

### 根因

编辑器/补丁工具将多行 reason 的后续行放到装饰器声明之前。**每次修改测试文件后必须 `py_compile` 验证**。

### 已确认案例

| 文件 | 补丁 | 影响 |
|------|------|------|
| test_os.py | 0111 | 6 处 → 全模块无法加载 |
| test_site.py | 0112 | 4 处 → 全模块无法加载 |

### 防范：长 reason 用括号包裹或保持单行

---

## E057: regrtest 默认多 worker 导致并发竞态

### 错误特征

```
Run 492 tests in parallel using 18 worker processes  # cpu_count=16
load avg: 75.00  # 16 核系统严重过载
Warning -- locale was modified by test_strptime  # 全局状态污染
test_strptime: 7 errors (首轮) / 0 errors (re-run)  # flaky
```

### 根因

regrtest 默认按 `os.cpu_count()` 开启 worker（鸿蒙=18），与 `MAKEFLAGS=-j1` **独立**：
- `MAKEFLAGS=-j1`：make 编译串行化（必需，FIFO 限制）
- `TESTOPTS="-j1"`：regrtest 测试串行化（推荐用于精确基线）

### 修复

```bash
MAKEFLAGS="-j1" make test TESTOPTS="-j1 --ignore=smtpnet ..."
```

---

## E058: sed 操作生成文件导致补丁不可复现

### 错误特征

```
# 编译过程中使用了 sed 修改 configure 或 Makefile：
sed -i 's/BUILDEXEEXT=.exe/BUILDEXEEXT=/' Makefile
sed -i '/^#define MAN_OWNER/s/^/#\/\* /' config.h

# 编译成功了，但：
# 1. 这些修改没有对应的 .patch 文件
# 2. 下次从原始 tarball 重新编译时，这些修改丢失
# 3. 无法向上游提交（上游不接受 sed hack）
```

### 根因

`configure` 和 `Makefile` 是**生成文件**（由 `autoconf` / `automake` 从 `configure.ac` / `Makefile.am` 生成）。
对生成文件使用 `sed` 修改：

| 问题 | 说明 |
|------|------|
| **不可复现** | 原始 tarball 不包含这些修改 |
| **易丢失** | `make distclean` + 重新 `./configure` 后修改消失 |
| **不可验证** | 无法通过 `patch --dry-run` 检查 |
| **不可上游** | 上游只接受源码级修改 |

### 正确做法

```
sed 操作的目标文件          →  正确的修改位置
─────────────────────────────────────────────
configure                   →  configure.ac（优先级①）或 configure 本身（优先级②）+ 生成 .patch
Makefile                    →  Makefile.am（①）或 Makefile.in（②）+ 生成 .patch
config.h                    →  config.h.in（由 autoconf 从 configure.ac 生成）+ .patch
build-aux/config.guess      →  直接打补丁（非 autoreconf 生成）✅
build-aux/config.sub        →  直接打补丁 ✅
```

**例外情况**：如果软件**只有** `configure` 没有 `configure.ac`（即上游发布的是预生成的 tarball），则直接修改 `configure` 并保存为 `.patch` 文件是可接受的（优先级②）。

### 验证命令

```bash
# Phase 4 补丁校验时必须执行：
diff -ruN original_src/ modified_src/ > all_changes.diff

# 检查是否有未捕获的 sed 修改：
grep -c "++++" all_changes.diff  # 对话中讨论的修改数
ls patches/*.patch | wc -l       # 实际补丁文件数
# 两者应该一致（排除 build/ 等构建产物）
```

### 涉及范围

所有 autotools 项目。**这是最常见的补丁质量问题。**

### 相关规范

- SKILL.md §P0 参数最少化原则
- `knowledge/build-systems.md` §3.6 修改层级决策树

---

## E059: 源码修改未保存为 .patch 文件

### 错误特征

```
# 编译过程中临时修改了源码解决了问题：
# 编辑 lib/stdio.c，在第 42 行添加了 #ifdef __OHOS__ 分支
# 编译通过了！

# 但归档时发现：
ls patches/
# 总计 0
# （没有 .patch 文件）

# 或：对话中讨论了 5 处修改，但 patches/ 下只有 3 个 .patch
```

### 根因

编译调试过程中专注于解决问题，忘记将修改固化为正式补丁文件。
Phase 4 归档时如果没有做 **Step 3 补丁完整性校验**，这些修改会永久丢失。

### 解决方案

**实时保存**（推荐，Phase 3 Step 6）：

```bash
# 每解决一个问题后立即生成补丁
cd /path/to/source
# 假设原始源码在 ../original/，修改后在当前目录
diff -ruN ../original/ . > ../archives/x/xxx/version/patches/NNNN-description.patch

# 验证补丁可干净应用
cd ../original/
patch --dry-run -p1 < ../archives/x/xxx/version/patches/NNNN-description.patch
```

**批量刷新**（Phase 4 Step 3，使用工具脚本）：

```bash
./scripts/refresh-patch.sh --all orig_dir/ mod_dir/ patches_dir/
```

### 防范措施

1. **PROGRESS.md 实时记录**：每处源码修改必须立即写入"源码修改清单"表格
2. **Phase 4 强制校验**：`diff -ruN` 对比原始源码和修改后源码
3. **close-archive.sh 检查**：归档收脚脚本检查 patches/ 数量与 PROGRESS.md 一致性

### 相关规范

- SKILL.md §P0 补丁质量"三可"原则
- SKILL.md Phase 4 Step 3 补丁完整性校验

---

## E060: 补丁缺少 __OHOS__ 守卫无法上游化

### 错误特征

```c
// ❌ 错误：硬编码修改，影响所有平台
int fd = open(path, O_RDONLY);
if (fd < 0) {
    return 0;  // HarmonyOS 上某些路径需要跳过
}

// ❌ 错误：用 Linux 判断来排除其他平台
#ifndef __linux__
int fd = open(path, O_RDONLY);
if (fd < 0) return 0;
#endif
```

### 根因

修改源码时只考虑了"让它在鸿蒙上工作"，没有考虑：
1. 其他平台（BSD、macOS、其他 Linux 发行版）
2. 上游维护者的审核标准
3. 代码的可读性和可维护性

### 正确写法

```c
// ✅ 正确：标准 OHOS 隔离模板
#ifdef __OHOS__
/*
 * HarmonyOS: open() on certain paths returns unexpected errors
 * due to SELinux restrictions on non-standard filesystems.
 * Skip gracefully instead of failing.
 */
if (open(path, O_RDONLY) < 0) {
    return 0;
}
#endif
```

### 守卫宏选择指南

| 场景 | 推荐守卫 | 说明 |
|------|---------|------|
| 鸿蒙特有行为 | `#ifdef __OHOS__` | 最精确，clang 自动定义 |
| musl 特有行为 | `#if defined(__OHOS__) \|\| (!defined(__GLIBC__) && defined(__linux__))` | 覆盖所有 musl 平台 |
| 缺少某系统调用 | `#ifdef HAVE_XXX` + 在 configure 中检测 | 最通用，平台无关 |
| 内核差异 | 运行时检测 errno/EACCES | 无需编译期判断 |

### 命名和注释规范

```c
/* HarmonyOS: <简短原因> */
/* HarmonyOS: <原因> — <详细说明（可选）> */

// 示例：
/* HarmonyOS: fstat() returns EACCES for non-file descriptors */
/* HarmonyOS: musl iconv does not support //IGNORE suffix (glibc extension) */
```

### 相关规范

- `knowledge/build-systems.md` §3.7 OHOS 平台隔离标准写法
- SKILL.md §P0 补丁质量"三可"原则（可上游化）

---

## E061: gnulib stdbool.h 模块缺失

### 错误特征

```
./config.h:2555:6: error: "<stdbool.h> does not exist on this platform. Use gnulib module 'stdbool-c99' instead of gnulib module 'stdbool'."
```

### 根因

GNU 软件使用 gnulib 提供 POSIX 兼容层。gnulib 的 `stdbool` 模块在较新版本中被标记为 deprecated，应使用 `stdbool-c99` 替代。但 configure 检测时如果 conftest 无法执行（见 E064），会回退到错误的默认值。

**问题链**：
```
configure 运行 conftest 测试
    ↓
conftest 二进制无法执行（安全弹窗 / SELinux）
    ↓
检测结果默认为"不可用"
    ↓
gnulib 选择 fallback 模块（如 stdbool 而非 stdbool-c99）
    ↓
编译时报错：模块不兼容当前平台
```

### 解决方案

**方案 1：让 configure 的 conftest 正常执行**
- 首次运行编译产物触发安全弹窗确认
- 或在 configure 前设置 `ac_cv_func_*` 缓存变量跳过检测

**方案 2：强制使用正确的 gnulib 模块**

```bash
# 在 configure.ac 中（源码级修改）:
gl_STDLIB_H  # 替代 gl_STDBOOL_H

# 或通过环境变量强制:
export gl_cv_header_stdbool_h=yes
```

**方案 3：CFLAGS 禁用该检查（临时绕过）**

```bash
# 如果是 Werror 导致的级联错误，先修 Werror（E063）可能一并解决
```

### 涉及软件

sed 4.9、以及所有使用新版 gnulib 的 GNU 软件（grep, coreutils, gawk 等）

### 相关模式

- [E064](#e064-conftest-无法执行导致配置检测失败) — 根因
- [E063](#e063--werror-导致警告变错误) — 可能的级联原因

---

## E062: FLEXIBLE_ARRAY_MEMBER 未定义

### 错误特征

```
lib/dfa.h:42:13: error: use of undeclared identifier 'FLEXIBLE_ARRAY_MEMBER'
```

### 根因

C99 的灵活数组成员（Flexible Array Member）在某些平台上需要宏定义。gnulib 的 `flexmember.h` 提供了可移植实现，但如果头文件包含顺序错误或 gnulib 检测失败，该宏未被定义。

### 解决方案

```c
// 在受影响的 .h 文件顶部添加:
#if !defined(FLEXIBLE_ARRAY_MEMBER)
#if __STDC_VERSION__ >= 199901L
#define FLEXIBLE_ARRAY_MEMBER // C99: 空（FAM 直接用 []）
#else
#define FLEXIBLE_ARRAY_MEMBER 1  // C89: 大小为 1
#endif
#endif
```

或确保 gnulib 的 `flexmember.h` 在使用前被正确包含：

```bash
# configure 时指定:
export gl_cv_flexmember=yes
```

### 涉及软件

sed 4.9（lib/dfa.h）、其他使用 gnulib FAM 的软件

---

## E063: -Werror 导致警告变错误

### 错误特征

```
sed/compile.c:205:9: error: incompatible integer to pointer conversion initializing 'char *' with an expression of type 'int' [-Wint-conversion]
sed/compile.c:422:15: error: incompatible integer to pointer conversion assigning to 'char *' from 'int' [-Wint-conversion]
18 warnings and 12 errors generated.
```

注意：**warnings 数量 > 0 但 errors = 0 是正常的；errors > 0 则是 -Werror 把 warning 升级成了 error。**

### 根因

项目启用了 `-Werror`（或某些类别如 `-Werror=implicit-function-declaration`），将所有编译器警告视为错误。musl/clang 组合下会产生一些与 glibc 不同的警告：

| 警告类型 | 触发场景 | musl 特有 |
|---------|---------|---------|
| `-Wint-conversion` | int→指针 隐式转换 | ✅ musl size_t 差异 |
| `-Wincompatible-pointer-types` | 不同类型指针赋值 | ✅ 常见 |
| `-Wimplicit-function-declaration` | 未声明函数调用 | ✅ 头文件差异 |
| `-Wformat-truncation` | 格式化字符串截断 | ✅ 常见 |

### 解决方案

**方案 1（推荐）：在 Makefile 中对特定 warning 禁用 error**

```makefile
# 在编译规则中添加（不改 configure.ac）:
CFLAGS += -Wno-error=int-conversion
CFLAGS += -Wno-error=incompatible-pointer-types
```

**方案 2：configure.ac 中条件性禁用（可 upstream）**

```m4
# 在 configure.ac 的 compiler flag 检测之后:
case "$host_os" in
    *ohos*|*linux-musl*)
        AX_APPEND_FLAG([CFLAGS], [-Wno-error=int-conversion])
        AX_APPEND_FLAG([CFLAGS], [-Wno-error=incompatible-pointer-types])
        ;;
esac
```

**方案 3：仅用于本次编译的临时 workaround**

```bash
make CFLAGS="-O2 -fPIC -Wno-error=int-conversion -Wno-error=incompatible-pointer-types"
```

### 判断方法

```bash
# 区分"真正的 error"和"warning 被 -Werror 升级":
make 2>&1 | grep "error:" 
# 如果看到 "-Werror" 或 "[-Wxxx]" 字样 → 就是 E063
# 如果只有 "undefined reference" / "No such file" → 不是 E063
```

### 涉及范围

**所有使用 `-Werror` 的软件在鸿蒙上都可能遇到**。这是最普遍的适配问题之一。

### 相关知识

- SKILL.md R1 参数最少化原则：额外 CFLAGS 应记录为技术债务
- `knowledge/build-systems.md` §3 — CFLAGS hack 消除策略

---

## E064: conftest 无法执行导致配置检测失败

### 错误特征

```
configure: error: cannot run C compiled programs.
If you meant to cross compile, use '--host'.
See 'config.log' for more details.

config.log: ./conftest: inaccessible or not found
configure:5796: $? = 127
```

### 根因

autotools 的 configure 脚本通过**编译并运行小测试程序**来检测平台能力（如函数是否存在、类型大小等）。在鸿蒙上：

1. configure 编译出 `conftest` 二进制
2. 尝试执行 `./conftest`
3. **首次执行非系统二进制需要安全确认弹窗**
4. 弹窗超时未点 → 进程被杀 → configure 认为程序无法运行
5. **得出错误结论："此平台不能运行编译出的程序"→ 误判为交叉编译**

**关键区别**：

| 场景 | conftest 结果 | configure 行为 |
|------|--------------|---------------|
| 正常（点了弹窗） | exit 0 + 输出 | 正确检测平台能力 |
| 弹窗超时 | exit 127 / Permission denied | **误判为 cross compile** |
| 真正交叉编译 | 不能执行（架构不同） | 正确判断 |

### 影响

当 configure 误判为交叉编译后：
- 大量检测使用**硬编码默认值**而非实际检测结果
- gnulib 模块选择错误（E061）
- 函数可用性检测跳过
- 最终导致编译错误（E062/E063 级联失败）

### 解决方案

**方案 1（首选）：手动触发弹窗后再跑 configure**

```bash
# 1. 先跑一次 configure（会卡在弹窗）
./configure --prefix=$PREFIX &
# 2. 快速点击所有弹窗
# 3. 等 configure 完成
# 4. 如果超时被杀，重新跑（此时弹窗已确认过）
./configure --prefix=$PREFIX
```

**方案 2：预填充 ac_cv_* 缓存变量**

```bash
# 从成功的 config.log 中提取关键变量，创建 cache 文件
cat > config.cache <<'EOF'
ac_cv_c_bigendian=no
ac_cv_func_mmap_fixed_mapped=yes
ac_cv_func_strerror_r_char_p=no
ac_cv_file__dev_ptmx=yes
ac_cv_type_uid_t=yes
ac_cv_type_size_t=yes
EOF
./configure --prefix=$PREFIX --cache-file=config.cache
```

**方案 3（禁止）：加 --host 参数**

```bash
# ❌ 违反 R1 参数最少化原则
# 且会导致更多问题（预定义宏、库路径等全部错误）
./configure --prefix=$PREFIX --host=aarch64-unknown-linux-ohos
```

### 如何区分真交叉编译 vs 弹窗超时

```bash
# 查看 config.log 关键行:
grep "cannot run\|inaccessible\|conftest.*exit" config.log

# 弹窗超时的特征:
#   ./conftest: inaccessible or not found   ← 权限问题
#   $? = 127                               ← 找不到/不能执行

# 真交叉编译的特征:
#   file format not recognized             ← 架构完全不匹配
#   Exec format error                       ← 同上
```

### 涉及范围

**所有 autotools 项目**。这是鸿蒙编译中最常见的根因性问题。

### 相关模式

- [E054](#e054-外来二进制首次执行被安全确认弹窗阻止) — 弹窗机制本身
- [E061](#e061-gnulib-stdbool-h-模块缺失) — 级联后果之一
- [E008](../error-patterns-core.md#e008-fstat-返回-eacces) — 类似的 conftest 运行环境问题

---

## E065: gnulib 头文件包含顺序导致符号未声明

### 错误特征

```
sed/compile.c:988:7: error: use of undeclared identifier 'xzalloc'
sed/compile.c:1299:62: unexpected type name 'size_t': expected expression
sed/compile.c:1321:67: expected expression
```

### 根因

gnulib 提供的头文件之间有依赖顺序要求。例如：
- `xzalloc()` 定义在 `lib/xalloc.h`
- `size_t` 需要 `<stddef.h>` 或 `<sys/types.h>`
- 如果 `.c` 文件的 `#include` 顺序不符合 gnulib 的预期，或者 gnulib 的替换头文件未正确覆盖系统头文件，就会导致符号未声明。

这通常是 **E064（conftest 失败）** 的二级后果：gnulib 的 `config.h` 中包含了错误的 `#define` 配置。

### 解决方案

```bash
# 方案 1：确保 CFLAGS 包含必要的路径
export CPPFLAGS="-I$BUILD_SRC_DIR/lib -I$BUILD_SRC_DIR"

# 方案 2：在受影响的 .c 文件中显式包含所需头文件
// 在 compile.c 顶部添加:
#include <stddef.h>      // 提供 size_t
#include "xalloc.h"       // 提供 xzalloc/xzalloc

# 方案 3：清理后重新 configure（解决 E064 后通常会顺带解决）
make distclean
./configure --prefix=$PREFIX  # 这次弹窗已确认
```

### 涉及软件

sed 4.9、以及其他深度依赖 gnulib 的 GNU 软件

### 诊断流程

```
遇到 "undeclared identifier" 错误
    │
    ├─ 该符号来自系统头文件（size_t, FILE*, etc）
    │   → 缺少 #include → 补上即可
    │
    ├─ 该符号来自 gnulib 替代模块（xzalloc, xmemdup, etc）
    │   → gnulib 头文件包含顺序问题 → 检查 CPPFLAGS / I 路径
    │
    └─ 该符号来自项目自身
        → 正常编译错误 → 修复源码
```

---

## E066: refresh-patch.sh 不支持 .tar.xz 格式

### 错误特征

```
refresh-patch.sh --auto sed 4.9
# tar: Error is not recoverable: exiting now
# 或: tar: Cannot open: No such file
# 补丁管线失败，跳过补丁生成
```

### 根因

`refresh-patch.sh` 内部硬编码 `tar xzf` 解压原始 tarball，只支持 `.tar.gz` 格式。
但 GNU 软件越来越多使用 `.tar.xz`（xz 压缩率更高，文件更小）。

| 格式 | tar 参数 | 使用频率 |
|------|----------|---------|
| `.tar.gz` / `.tgz` | `tar xzf` | 传统格式 |
| `.tar.xz` / `.txz` | `tar xJf` | **现代 GNU 软件主流**（sed 4.9, grep 3.12+, coreutils 9.14+） |
| `.tar.bz2` / `.tbz2` | `tar xjf` | 较少 |

### 解决方案

```bash
# refresh-patch.sh 应按扩展名选择解压方式
case "$TARBALL" in
    *.tar.gz|*.tgz)  tar xzf "$TARBALL" -C "$DIR" ;;
    *.tar.xz|*.txz)  tar xJf "$TARBALL" -C "$DIR" ;;
    *.tar.bz2|*.tbz2) tar xjf "$TARBALL" -C "$DIR" ;;
    *)               tar xf  "$TARBALL" -C "$DIR" ;;  # 自动检测
esac
```

### 涉及范围

所有使用 `.tar.xz` 源码的软件。**这是 refresh-patch.sh 的脚本缺陷，不是平台问题。**

### 相关知识

- SKILL.md Step 3（finish-build.sh 调用 refresh-patch.sh）
- `scripts/refresh-patch.sh` 第 ~430 行

---

## E067: grep 匹配含正则元字符的固定字符串失败

### 错误特征

```
# 测试版本信息：
$SED --version | head -1 | grep "GNU sed 4.9"
# 返回空（匹配失败），但输出明明包含该字符串

# 原始输出:
# /storage/Users/currentUser/tmp/sed-test-install/bin/sed (GNU sed) 4.9
```

### 根因

`grep` 默认使用**基本正则表达式 (BRE)** 模式。当待匹配字符串含正则元字符时：
- `(` `)` → 分组符号
- `[` `]` → 字符类
- `$` → 行尾锚定

本例中 `(GNU)` 的括号被 grep 当作分组元字符，导致匹配失败。

### 验证命令

```bash
V=$($SED --version | head -1)
echo "[$V]"
echo "$V" | grep "GNU sed 4.9"    # ❌ 失败：( 是正则元字符
echo "$V" | grep -F "GNU sed 4.9"   # ✅ 成功：-F 固定字符串匹配
case "$V" in *GNU sed 4.9*) echo OK;; esac  # ✅ 成功：shell 原生模式匹配
```

### 解决方案

| 场景 | 推荐方式 |
|------|---------|
| 匹配固定字符串（含元字符风险） | `grep -F` （强制固定字符串模式） |
| shell 变量模式匹配 | `case "$var" in *pattern*)` （POSIX 原生，无元字符问题） |
| 简单子串检查 | `case "$var" in *substring*)` |

### 涉及范围

所有在鸿蒙上编写测试脚本或验证逻辑时。**这是 AI 编程疏忽，不是平台问题。**

### 相关规范

- SKILL.md §1.2 AI 执行风格规范 — grep -F 原则
- E010 toybox 兼容性问题（部分 grep 实现差异）

---
*属于 [error-patterns.md](./error-patterns.md) 的模块化子集*
