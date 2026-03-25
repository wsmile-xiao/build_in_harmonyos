# Python 3.9.0 鸿蒙（HarmonyOS）移植补丁分析报告

## 一、总览

本报告对比分析两个 Python 源码目录的差异：

| 目录 | 说明 |
|------|------|
| `Python-3.9.0-test` | 基准版本（已包含第一轮鸿蒙适配补丁） |
| `Python-3.9.0-work` | 修改后版本（在 test 基础上的增量修改） |

**重要发现**：`Python-3.9.0-test`（所谓的"原始"版本）**已经包含大量 HarmonyOS 适配代码**，说明这不是一个纯净的上游代码，而是经过了第一轮适配的版本。`Python-3.9.0-work` 是在此基础上进行的增量修改。

### 文件差异汇总

| 文件 | test→work 差异 | 两版均已含鸿蒙修改 | 差异性质 |
|------|:---:|:---:|------|
| `Lib/_harmonyos_compat.py` | ✅ | ✅（work 新增 `init()` 函数） | 功能增强 |
| `Lib/site.py` | ✅ | ✅（work 新增 compat 导入） | 功能增强 |
| `Lib/venv/__init__.py` | ✅ | ✅（work 新增符号链接容错） | 鲁棒性增强 |
| `configure` | ❌ | ✅ | 两版一致 |
| `setup.py` | ❌ | ✅ | 两版一致 |
| `Lib/sysconfig.py` | ❌ | ✅ | 两版一致 |
| `Lib/distutils/util.py` | ❌ | ✅ | 两版一致 |
| `Lib/_bootsubprocess.py` | ❌ | ✅ | 两版一致 |
| `Modules/posixmodule.c` | ❌ | ❌ | 无鸿蒙修改 |
| `Modules/getnameinfo.c` | ❌ | ❌ | 无鸿蒙修改 |
| `Makefile.pre` | ✅ | ✅ | 仅路径变化（构建产物） |
| `pyconfig.h` | ❌ | ❌ | 两版一致，无差异 |

---

## 二、增量修改详细分析（test → work 的变更）

### 2.1 `Lib/_harmonyos_compat.py` — 新增 `init()` 入口函数

**差异类型**：功能增强  
**修改类型**：鸿蒙特有适配  

#### 详细 Diff

```diff
--- Python-3.9.0-test/Lib/_harmonyos_compat.py
+++ Python-3.9.0-work/Lib/_harmonyos_compat.py
@@ -150,3 +150,9 @@
     _log("Compatibility layer applied successfully")
 
 
+# Auto-apply when module is imported (called from site.py)
+def init():
+    """Initialize HarmonyOS compatibility layer."""
+    _apply_compat_layer()
+
```

#### 分析

**修改内容**：在文件末尾新增一个 `init()` 函数作为对外接口，封装了 `_apply_compat_layer()` 的调用。这使得 `site.py` 可以通过简洁的 `_harmonyos_compat.init()` 来激活兼容层。

**平台隔离评估**：
- ✅ **已做平台隔离**：`_apply_compat_layer()` 内部调用 `_is_harmonyos()` 进行运行时检测，非鸿蒙平台不会执行任何补丁。
- 兼容层使用 `sys.platform` 检测（`'harmonyos' in platform or 'ohos' in platform`），在非鸿蒙平台上函数直接返回。

**对其他平台的影响**：无影响。`ImportError` 被 `site.py` 捕获。

**上游合入建议**：
- ⚠️ **只能作为 downstream patch 维护**。`_harmonyos_compat.py` 本身是 HarmonyOS 特有的新文件，修补 subprocess 的 SELinux 问题。这种运行时猴子补丁（monkey-patching）方式不适合上游合入。
- 上游更希望看到的是在 `subprocess.Popen` 本身提供适当的 hook 或配置选项。

---

### 2.2 `Lib/site.py` — 在 `main()` 中导入 HarmonyOS 兼容层

**差异类型**：功能增强  
**修改类型**：鸿蒙特有适配  

#### 详细 Diff

```diff
--- Python-3.9.0-test/Lib/site.py
+++ Python-3.9.0-work/Lib/site.py
@@ -562,6 +562,18 @@
     """
     global ENABLE_USER_SITE
 
+    # HarmonyOS compatibility layer - must be applied first
+    # This patches subprocess calls to work around SELinux restrictions
+    try:
+        import _harmonyos_compat
+        _harmonyos_compat.init()
+    except ImportError:
+        pass  # Module not available (non-HarmonyOS build)
+    except Exception as e:
+        # Don't let compat layer break Python startup
+        if os.environ.get('HARMONYOS_SUBPROCESS_DEBUG'):
+            print(f"[HarmonyOS-Compat] Error: {e}", file=sys.stderr)
+
     orig_path = sys.path[:]
     known_paths = removeduppaths()
```

#### 分析

**修改内容**：在 `main()` 函数开头（在 `removeduppaths()` 之前）添加了 HarmonyOS 兼容层的导入和初始化。

**平台隔离评估**：
- ✅ **已做平台隔离**：使用 `try/except ImportError` 模式，在非鸿蒙构建中 `_harmonyos_compat.py` 不存在，`ImportError` 被静默捕获。
- 额外的 `except Exception` 确保即使兼容层出错也不会阻止 Python 启动。
- 调试信息通过环境变量 `HARMONYOS_SUBPROCESS_DEBUG` 控制。

**对其他平台的影响**：无影响。`try/except ImportError` 是 Python 中常见的可选模块导入模式。

**上游合入建议**：
- ⚠️ **只能作为 downstream patch 维护**。上游不会接受在 `site.py` 中硬编码 HarmonyOS 特定逻辑。
- 如果要上游化，可以考虑让 `site.py` 支持一个通用的 `sitecustomize` 或 plugin 机制，但这需要更大的设计讨论。

---

### 2.3 `Lib/venv/__init__.py` — 符号链接失败时的容错处理

**差异类型**：鲁棒性增强  
**修改类型**：鸿蒙特有适配（但具有通用价值）

#### 详细 Diff

```diff
--- Python-3.9.0-test/Lib/venv/__init__.py
+++ Python-3.9.0-work/Lib/venv/__init__.py
@@ -137,7 +137,16 @@
             (sys.platform != 'darwin')):
             link_path = os.path.join(env_dir, 'lib64')
             if not os.path.exists(link_path):   # Issue #21643
-                os.symlink('lib', link_path)
+                try:
+                    os.symlink('lib', link_path)
+                except OSError:
+                    # HarmonyOS: HMDFS does not support symlinks (SELinux + Hmmac).
+                    # Fall back to creating lib64 as a real directory.
+                    # This works because Python's sysconfig.get_path() uses
+                    # sys.prefix (dynamic) rather than the static LIBDIR, so
+                    # pip/ensurepip install to lib/pythonX.Y/site-packages
+                    # regardless of whether lib64 is a symlink or directory.
+                    os.makedirs(link_path, exist_ok=True)
         context.bin_path = binpath = os.path.join(env_dir, binname)
         context.bin_name = binname
```

#### 分析

**修改内容**：在创建 `lib64` 符号链接时添加 `try/except OSError` 容错。当 `os.symlink()` 因 HarmonyOS HMDFS 不支持符号链接而失败时，回退为创建真实目录 `lib64`。

**平台隔离评估**：
- ⚠️ **部分隔离**：虽然 `except OSError` 是通用的（任何平台符号链接失败都会触发），但 `os.makedirs()` 回退的行为只对 HarmonyOS 是正确的。
- 在 Linux 上，如果 `os.symlink()` 因其他原因（如权限不足）失败，回退创建目录可能不是期望行为。

**对其他平台的影响**：
- 理论上有影响：如果 Linux 上符号链接因权限问题失败，会意外创建一个空目录。
- 实际影响低：这种情况在 Linux 上非常罕见。

**上游合入建议**：
- 💡 **可以尝试提 PR**，但需要改进隔离：
  - 建议方案 1：只在特定平台（已知不支持符号链接的文件系统）上启用回退
  - 建议方案 2：更精细地检测 `OSError` 的 `errno`（如 `errno.EPERM`, `errno.EACCES`）
  - 建议方案 3：先检测文件系统是否支持符号链接（创建临时链接测试）

**重构方案**：

```python
# 方案 3：推荐 — 通用化检测
import errno

link_path = os.path.join(env_dir, 'lib64')
if not os.path.exists(link_path):
    try:
        os.symlink('lib', link_path)
    except OSError as e:
        # On filesystems that don't support symlinks (e.g., HarmonyOS HMDFS,
        # some network filesystems, or when running in restricted containers),
        # fall back to creating a real directory.
        if e.errno in (errno.EPERM, errno.EACCES, errno.EOPNOTSUPP, errno.ENOSYS):
            os.makedirs(link_path, exist_ok=True)
        else:
            raise
```

---

### 2.4 `Makefile.pre` — 仅路径变化（构建产物）

**差异类型**：构建产物差异  
**修改类型**：无源码变更  

#### 详细 Diff

```diff
--- Python-3.9.0-test/Makefile.pre
+++ Python-3.9.0-work/Makefile.pre
@@ -29,8 +29,8 @@
 VERSION=	3.9
 srcdir=		.
 
-abs_srcdir=	/storage/Users/currentUser/python/Python-3.9.0-test
-abs_builddir=	/storage/Users/currentUser/python/Python-3.9.0-test
+abs_srcdir=	/storage/Users/currentUser/python/Python-3.9.0-work
+abs_builddir=	/storage/Users/currentUser/python/Python-3.9.0-work
 
 
 CC=		clang
@@ -199,7 +199,7 @@
 OTHER_LIBTOOL_OPT=
 
 # Environment to run shared python without installed libraries
-RUNSHARED=       LD_LIBRARY_PATH=/storage/Users/currentUser/python/Python-3.9.0-test:...
+RUNSHARED=       LD_LIBRARY_PATH=/storage/Users/currentUser/python/Python-3.9.0-work:...
 
 # ensurepip options
 ENSUREPIP=      upgrade
@@ -259,8 +259,8 @@
 PYTHON=		python$(EXE)
 BUILDPYTHON=	python3.9$(BUILDEXE)
 
-PYTHON_FOR_REGEN?=python3
-UPDATE_FILE=python3 $(srcdir)/Tools/scripts/update_file.py
+PYTHON_FOR_REGEN?=python3.9
+UPDATE_FILE=python3.9 $(srcdir)/Tools/scripts/update_file.py
 PYTHON_FOR_BUILD=./$(BUILDPYTHON) -E
 _PYTHON_HOST_PLATFORM=
 BUILD_GNU_TYPE=	aarch64-unknown-linux-ohos
```

#### 分析

**修改内容**：全部是构建路径和工具链引用的变更：
- `abs_srcdir`/`abs_builddir` 指向不同目录
- `RUNSHARED` 中的 `LD_LIBRARY_PATH` 路径变化
- `PYTHON_FOR_REGEN` 从 `python3` 改为 `python3.9`（因为鸿蒙上只有 `python3.9`）

**上游合入建议**：
- ❌ **不需要上游合入**。这些都是 `./configure` 和 `make` 自动生成的构建产物，不属于源码修改。

---

## 三、两版均已包含的鸿蒙修改详细分析

以下文件在 test 和 work 版本中完全一致，但**相对于上游 Python 3.9.0 原始代码已包含 HarmonyOS 适配**。

### 3.1 `configure` — 构建系统平台检测与配置

**修改类型**：构建系统适配  
**文件性质**：autoconf 脚本

#### 修改点清单

| 行号 | 修改内容 | 平台隔离 | 上游建议 |
|------|----------|---------|---------|
| 3730-3731 | `*-*-linux-ohos*)` 交叉编译识别为 `HarmonyOS` | ✅ `case` 分支 | 💡 可提 PR |
| 3757 | `harmonyos*\|HarmonyOS*)` MACHDEP 设为 `ohos` | ✅ `case` 分支 | 💡 可提 PR |
| 3836-3839 | HarmonyOS 不定义 `_XOPEN_SOURCE`（musl libc） | ✅ `case` 分支 | 💡 可提 PR |
| 5961-5971 | `__OHOS__` 宏下的多架构 triplet（aarch64/arm/x86_64） | ✅ `#ifdef` | 💡 可提 PR |
| 6407-6413 | 跳过文件系统大小写检测（HarmonyOS 特殊处理） | ✅ `case` 分支 | 💡 可提 PR |
| 6641-6647 | musl libc + BIND_NOW → 使用共享库而非静态库 | ✅ `case` 分支 | 💡 可提 PR |
| 10851-10857 | LDSHARED 包含 `-lpython`（BIND_NOW 符号解析） | ✅ `case` 分支 | 💡 可提 PR |
| 10995 | `CCSHARED="-fPIC"` | ✅ `case` 分支 | 💡 可提 PR |
| 11073-11074 | `LINKFORSHARED="-Xlinker -export-dynamic"` | ✅ `case` 分支 | 💡 可提 PR |
| 12935-12939 | 跳过 `CAN_RAW_FD_FRAMES` 检查（内核头文件缺失） | ✅ `case` 分支 | 💡 可提 PR |
| 12976-12980 | 跳过 `CAN_RAW_JOIN_FILTERS` 检查（内核头文件缺失） | ✅ `case` 分支 | 💡 可提 PR |

#### 平台隔离评估
- ✅ **所有修改均已做平台隔离**：全部使用 `case $ac_sys_system in ... HarmonyOS*)` 模式或 `#ifdef __OHOS__` 预处理条件。
- 对其他平台零影响。

#### 上游合入建议
- 💡 **大部分可以提 PR**。`configure` 中的平台检测模式（`case` 分支 + `#ifdef`）是上游标准做法。
- 可以参考 iOS/Android/VxWorks 等已有的上游移植案例，将 HarmonyOS 作为新平台合入。
- `CAN_RAW_*` 的跳过可以改为更通用的 autoconf 检测（检查头文件中是否定义了宏），而不是硬编码平台名。

**重构方案**（CAN_RAW 检查通用化）：

```m4
# 当前做法（平台硬编码）：
case $ac_sys_system in
    HarmonyOS*)
        # skip
        ;;
    *)
        # 实际检查
        ;;
esac

# 推荐做法（通用检测）：
AC_CHECK_DECL(CAN_RAW_FD_FRAMES, 
    [AC_DEFINE(HAVE_CAN_RAW_FD_FRAMES, 1, ...)],
    [], [#include <linux/can.h>])
```

---

### 3.2 `setup.py` — 构建扩展模块的鸿蒙适配

**修改类型**：构建系统适配 + 鸿蒙特有适配

#### 修改点清单

| 行号 | 修改内容 | 平台隔离 | 上游建议 |
|------|----------|---------|---------|
| 67 | `OHOS = (HOST_PLATFORM.startswith('harmony') or HOST_PLATFORM.startswith('ohos'))` | ✅ 运行时检测 | 💡 可提 PR |
| 243-280 | `ohos_sdk_root()` — 获取鸿蒙 SDK sysroot 路径 | ✅ OHOS 条件 | ⚠️ 需重构 |
| 285-310 | `get_ohos_arch()` — 获取鸿蒙架构 | ✅ 内部函数 | ⚠️ 需重构 |
| 325-326 | sysroot 查找使用 `ohos_sdk_root()` | ✅ OHOS 条件 | 💡 可提 PR |
| 528-535 | BIND_NOW 扩展模块链接 `-lpython` | ✅ `if OHOS` | 💡 可提 PR |
| 722-728 | 多架构路径 `/usr/lib/{arch}-linux-ohos` | ✅ `if OHOS` | 💡 可提 PR |
| 863-878 | sysroot 下的 lib/inc 路径搜索 | ✅ `if OHOS` | 💡 可提 PR |
| 1183-1193 | curses `_XOPEN_SOURCE_EXTENDED` 定义 | ✅ `if MACOS or OHOS` | ⚠️ 需讨论 |

#### 平台隔离评估
- ✅ **已做平台隔离**：所有鸿蒙特定逻辑都在 `if OHOS:` 条件块中。
- `OHOS` 变量通过 `HOST_PLATFORM` 字符串匹配设置，与 `AIX`、`MACOS` 等其他平台变量模式一致。

#### 上游合入建议
- 💡 **大部分可以提 PR**，但需要注意：
  1. `ohos_sdk_root()` 和 `get_ohos_arch()` 可以参考 `macosx_sdk_root()` 的上游实现模式。
  2. curses 的 `_XOPEN_SOURCE_EXTENDED` 应该独立判断（而非与 macOS 合并），建议使用更细粒度的检测。
  3. 中文字符注释应改为英文注释后再提 PR。

**重构方案**（curses 独立判断）：

```python
# 当前：
if MACOS or OHOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))

# 推荐（更精确的平台判断）：
if MACOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))
elif OHOS:
    # HarmonyOS musl libc: need _XOPEN_SOURCE_EXTENDED for wide char support
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))
```

---

### 3.3 `Lib/sysconfig.py` — 平台标识字符串

**修改类型**：平台检测缺失修复  

#### 修改内容（第 657-660 行）

```python
elif osname[:9] == "harmonyos" or osname[:4] == "ohos":
    # HarmonyOS/OpenHarmony: similar to Linux, release contains spaces
    return "ohos-%s" % (machine,)
```

#### 平台隔离评估
- ✅ **已做平台隔离**：使用 `elif` 分支，只匹配 `harmonyos` 或 `ohos` osname。

#### 对其他平台的影响：无影响。

#### 上游合入建议
- 💡 **可以直接提 PR**。这是标准的平台标识处理，与已有的 `linux`, `darwin`, `aix` 等分支模式一致。

---

### 3.4 `Lib/distutils/util.py` — 平台标识字符串

**修改类型**：平台检测缺失修复  

#### 修改内容（第 95-96 行）

```python
elif osname[:9] == "harmonyos":
    return "ohos-%s" % (machine,)
```

#### 平台隔离评估
- ✅ **已做平台隔离**：`elif` 分支。

#### 上游合入建议
- 💡 **可以直接提 PR**。与 `sysconfig.py` 的修改配套。
- 注意：此处缺少 `or osname[:4] == "ohos"` 的判断（对比 `sysconfig.py` 中的处理更完整），建议补齐。

**重构方案**：

```python
# 当前：
elif osname[:9] == "harmonyos":
    return "ohos-%s" % (machine,)

# 推荐（与 sysconfig.py 保持一致）：
elif osname[:9] == "harmonyos" or osname[:4] == "ohos":
    return "ohos-%s" % (machine,)
```

---

### 3.5 `Lib/_bootsubprocess.py` — SELinux 子进程兼容

**修改类型**：鸿蒙特有适配  

#### 文件完整分析

此文件是 Python 3.9 为 `setup.py`（构建时）提供的最小 subprocess 实现（仅在标准 `subprocess` 模块不可用时使用）。鸿蒙修改添加了 SELinux 回避逻辑。

#### 关键修改点

| 位置 | 修改内容 | 平台隔离 |
|------|----------|---------|
| `_is_harmonyos()` 函数 | 运行时检测 `sys.platform` | ✅ |
| `Popen.wait()` 第 65 行 | `if _is_harmonyos(): cmd_str = "set -o pipefail; {cmd} 2>&1 \| cat"` | ✅ |
| `check_output()` 第 118 行 | `if _is_harmonyos(): cmd = "set -o pipefail; {cmd} 2>&1 \| cat >{tmp}"` | ✅ |

#### 平台隔离评估
- ✅ **已做平台隔离**：使用 `_is_harmonyos()` 运行时检测，非鸿蒙平台保持原行为。

#### 对其他平台的影响：无影响。

#### 上游合入建议
- ⚠️ **只能作为 downstream patch 维护**。
- 原因：`cmd | cat` 的 pipe 技巧是针对 HarmonyOS SELinux 策略的特定 workaround，不是通用修复。
- 上游可能会质疑这种修改的正确性和安全性（改变了命令执行语义）。

---

### 3.6 `Makefile.pre`（两版共有的鸿蒙修改）

**修改类型**：构建系统适配  

#### 修改内容

```makefile
# 第 66-72 行
# On HarmonyOS, hard links are not supported due to SELinux policy.
# Use cp -p instead of ln for hard link operations.
HARDLINK=	$(shell uname -s 2>/dev/null | grep -qi harmony && echo cp -p || echo ln)

# On HarmonyOS, 'ln -sf' may not work as expected.
# Use 'ln -s' and let callers 'rm -f' target beforehand if needed.
LN_FORCE=	$(shell uname -s 2>/dev/null | grep -qi harmony && echo ln -s || echo ln -sf)

# 第 133-137 行
MACHDEP=	ohos
MULTIARCH=	aarch64-linux-ohos
MULTIARCH_CPPFLAGS = -DMULTIARCH=\"aarch64-linux-ohos\"

# 第 266-267 行
BUILD_GNU_TYPE=	aarch64-unknown-linux-ohos
HOST_GNU_TYPE=	aarch64-unknown-linux-ohos
```

#### 平台隔离评估
- ✅ `HARDLINK`/`LN_FORCE`：通过 `uname -s | grep harmony` 运行时检测隔离。但这种方式不够健壮（`uname -s` 在鸿蒙上可能返回 `Linux`）。
- ⚠️ `MACHDEP`/`MULTIARCH`：由 `configure` 脚本生成，属于构建时确定，无需隔离。

#### 上游合入建议
- 💡 `MACHDEP=ohos` 和 `MULTIARCH` 由 `configure` 自动生成，随 configure 的修改一起上游化。
- ⚠️ `HARDLINK`/`LN_FORCE` 的检测方式需要改进：
  - 如果 `uname -s` 在鸿蒙上返回 `Linux`，这些 make 变量不会正确设置。
  - 建议改为在 `configure` 中检测（类似其他平台特定变量），或使用 `make` 条件。

**重构方案**（configure 中检测）：

```m4
# 在 configure 中添加：
AC_MSG_CHECKING(whether hard links work)
case $ac_sys_system in
    HarmonyOS*)
        AC_MSG_RESULT(no - HarmonyOS SELinux)
        HARDLINK="cp -p"
        LN_FORCE="ln -s"
        ;;
    *)
        AC_MSG_RESULT(yes)
        HARDLINK="ln"
        LN_FORCE="ln -sf"
        ;;
esac
AC_SUBST(HARDLINK)
AC_SUBST(LN_FORCE)
```

---

## 四、`pyconfig.h` 对比结果

`Python-3.9.0-test/pyconfig.h` 和 `Python-3.9.0-work/pyconfig.h` **完全一致**，无任何差异。

这说明两版使用的 `configure` 参数相同，产生的配置结果一致。`pyconfig.h` 中应该包含由 `configure` 自动检测出的鸿蒙相关宏定义（如 `__OHOS__`），但这些在两个版本间没有变化。

---

## 五、其他目录对比

| 目录/文件 | 结果 |
|-----------|------|
| `Include/*.h` | ❌ 无差异，无鸿蒙相关修改 |
| `Modules/*.c` | ❌ 源码无差异（`.o` 文件差异为构建产物） |
| `Objects/`, `Parser/`, `Python/` | ❌ 未检测到差异 |

**注意**：`Modules/posixmodule.c` 中的 `EX_NOHOST` 和 `Modules/getnameinfo.c` 中的 `ENI_NOHOSTNAME` 是标准 POSIX 定义（`NOHOST` ≠ `OHOS`），与鸿蒙无关。

---

## 六、`Lib/_harmonyos_compat.py` 完整内容分析

这是一个**全新的 HarmonyOS 专用模块**（两版均有），用于运行时修补 subprocess 调用以绕过 SELinux 限制。

### 功能概述

| 组件 | 修补对象 | 修补方式 |
|------|---------|---------|
| `os.system` | 直接替换为 pipe 包装版本 | `cmd` → `set -o pipefail; cmd 2>&1 \| cat` |
| `os.popen` | 直接替换为 pipe 包装版本 | 同上 |
| `subprocess.Popen` | 替换 `__init__` 强制 shell 模式 | `args` → shell string + pipe |

### 平台隔离
- ✅ `_is_harmonyos()` 检测函数在非鸿蒙平台返回 `False`
- ✅ `init()` 从 `site.py` 导入，非鸿蒙构建中文件不存在

### 上游合入评估
- ❌ **只能作为 downstream patch 维护**
- **原因**：
  1. 猴子补丁（monkey-patching）`os.system`/`os.popen`/`subprocess.Popen` 是侵入性操作
  2. 将所有 `Popen` 调用强制改为 `shell=True` 改变了安全语义（shell injection 风险）
  3. `cmd | cat` 是特定 SELinux 策略的 workaround，不是通用解决方案

---

## 七、汇总表

| # | 文件 | 修改摘要 | 类型 | 已隔离? | 上游建议 |
|---|------|---------|------|:------:|---------|
| 1 | `Lib/_harmonyos_compat.py` (增量) | 新增 `init()` 入口函数 | 鸿蒙特有适配 | ✅ | ⚠️ downstream patch |
| 2 | `Lib/site.py` (增量) | 导入并初始化 `_harmonyos_compat` | 鸿蒙特有适配 | ✅ | ⚠️ downstream patch |
| 3 | `Lib/venv/__init__.py` (增量) | `os.symlink` 失败时回退创建目录 | 鸿蒙特有+通用价值 | ⚠️ 部分 | 💡 可提 PR（需改进 errno 检测） |
| 4 | `Makefile.pre` (增量) | 仅路径变化 | 构建产物 | N/A | ❌ 不需要 |
| 5 | `configure` (两版共有) | 平台检测、musl 配置、多架构、CAN_RAW 跳过 | 构建系统适配 | ✅ | 💡 大部分可提 PR |
| 6 | `setup.py` (两版共有) | OHOS 变量、SDK root、BIND_NOW 链接、多架构路径 | 构建系统适配 | ✅ | 💡 大部分可提 PR |
| 7 | `Lib/sysconfig.py` (两版共有) | `_get_platform()` 中添加 HarmonyOS 分支 | 平台检测缺失 | ✅ | 💡 可直接提 PR |
| 8 | `Lib/distutils/util.py` (两版共有) | `get_platform()` 中添加 HarmonyOS 分支 | 平台检测缺失 | ✅ | 💡 可直接提 PR |
| 9 | `Lib/_bootsubprocess.py` (两版共有) | SELinux pipe workaround | 鸿蒙特有适配 | ✅ | ⚠️ downstream patch |
| 10 | `Makefile.pre` (两版共有) | HARDLINK/LN_FORCE/MACHDEP | 构建系统适配 | ⚠️ 部分 | 💡 随 configure 一起上游化 |
| 11 | `Modules/posixmodule.c` | 无鸿蒙修改 | — | — | — |
| 12 | `Modules/getnameinfo.c` | 无鸿蒙修改 | — | — | — |
| 13 | `pyconfig.h` | 两版一致，无差异 | — | — | — |

---

## 八、上游合入策略总览

### 8.1 可直接提 PR 的修改（通用性强）

1. **`configure`** — 作为新平台支持合入（参考 VxWorks 的上游模式）
   - 平台识别（`*-*-linux-ohos*`）
   - MACHDEP 设置
   - `_XOPEN_SOURCE` 处理
   - 多架构 triplet
   - 共享库链接参数（BLDSHARED/LDSHARED/CCSHARED/LINKFORSHARED）
   - BIND_NOW 共享库配置

2. **`Lib/sysconfig.py`** — 平台字符串分支（一行修改）

3. **`Lib/distutils/util.py`** — 平台字符串分支（一行修改，建议补齐 `ohos` 判断）

4. **`Lib/venv/__init__.py`** — symlink 回退（需改进 errno 检测使其更通用）

### 8.2 需要重构后可提 PR 的修改

1. **`setup.py`** — `ohos_sdk_root()`/`get_ohos_arch()` 需要参考 `macosx_sdk_root()` 的上游模式重写
2. **`Makefile.pre`** HARDLINK/LN_FORCE — 需要在 `configure` 中检测而非 `uname -s | grep`
3. **`configure` CAN_RAW 跳过** — 需要改为通用 autoconf 检测

### 8.3 只能作为 downstream patch 维护的修改

1. **`Lib/_harmonyos_compat.py`** — SELinux 猴子补丁，侵入性太强
2. **`Lib/site.py`** 的 compat 导入 — 与 `_harmonyos_compat.py` 配套的 downstream 修改
3. **`Lib/_bootsubprocess.py`** 的 pipe workaround — HarmonyOS SELinux 特有的 workaround

### 8.4 不需要上游合入的修改

1. **`Makefile.pre`** 路径变化 — 构建产物
2. **`.o`/`.so`/pickle 文件** — 构建产物

---

## 九、重构方案详细示例

### 9.1 venv symlink 回退（通用化方案）

```python
# Lib/venv/__init__.py — 通用化符号链接回退
import errno

# ...existing code...
link_path = os.path.join(env_dir, 'lib64')
if not os.path.exists(link_path):   # Issue #21643
    try:
        os.symlink('lib', link_path)
    except OSError as e:
        # Filesystems that don't support symlinks (e.g., HarmonyOS HMDFS,
        # certain network filesystems, or restricted container environments)
        # should fall back to creating a real directory. The pip/ensurepip
        # install paths are based on sys.prefix (dynamic), so they work
        # regardless of whether lib64 is a symlink or real directory.
        if e.errno in (errno.EPERM, errno.EACCES, errno.EOPNOTSUPP,
                       errno.EPROTONOSUPPORT, errno.ENOSYS):
            os.makedirs(link_path, exist_ok=True)
        else:
            raise
```

### 9.2 configure — 通用 CAN_RAW 检测（替代平台硬编码）

```m4
# 替代当前 HarmonyOS 硬编码跳过的通用方案
AC_MSG_CHECKING([for CAN_RAW_FD_FRAMES])
AC_COMPILE_IFELSE(
    [AC_LANG_PROGRAM([#include <linux/can.h>],
                     [#ifndef CAN_RAW_FD_FRAMES
                      #error "CAN_RAW_FD_FRAMES not defined"
                      #endif])],
    [AC_MSG_RESULT(yes)
     AC_DEFINE(HAVE_CAN_RAW_FD_FRAMES, 1, [Define if CAN_RAW_FD_FRAMES is available])],
    [AC_MSG_RESULT(no)])
```

### 9.3 Makefile.pre — configure 中检测 HARDLINK（替代 uname grep）

```m4
# configure.ac 中添加
AC_CACHE_CHECK([whether hard links work], [ac_cv_hardlink_works],
    [AC_RUN_IFELSE([AC_LANG_PROGRAM([
        #include <unistd.h>
        #include <stdio.h>
    ], [
        if (link("conftest.$ac_ext", "conftest.hardlink") != 0) return 1;
        unlink("conftest.hardlink");
        return 0;
    })],
    [ac_cv_hardlink_works=yes],
    [ac_cv_hardlink_works=no],
    [ac_cv_hardlink_works=yes])])

if test "$ac_cv_hardlink_works" = yes; then
    HARDLINK="ln"
    LN_FORCE="ln -sf"
else
    HARDLINK="cp -p"
    LN_FORCE="ln -s"
fi
AC_SUBST([HARDLINK])
AC_SUBST([LN_FORCE])
```

---

## 十、结论

### 鸿蒙移植的整体质量评估

| 维度 | 评分 | 说明 |
|------|:----:|------|
| 平台隔离度 | ⭐⭐⭐⭐ | 绝大多数修改已做平台隔离，仅 venv symlink 回退需改进 |
| 代码质量 | ⭐⭐⭐⭐ | 注释详细，逻辑清晰，但 `_harmonyos_compat.py` 的猴子补丁方式较为粗暴 |
| 上游合入可行性 | ⭐⭐⭐ | 约 70% 的修改可以上游化（configure/setup.py/sysconfig/distutils），30% 只能 downstream 维护 |
| 安全性 | ⭐⭐⭐ | `subprocess.Popen` 强制 `shell=True` 引入 shell injection 风险，需谨慎评估 |

### 推荐的上游合入路径

```
Phase 1: configure + sysconfig + distutils（低风险，平台检测补充）
  └── 可单独提 3-4 个小 PR

Phase 2: setup.py SDK root + 链接配置（中风险，需代码审查）
  └── 参考 macosx_sdk_root() 模式

Phase 3: venv symlink 回退（低风险，通用改进）
  └── 通用化 errno 检测

Downstream-only（不提交上游）:
  └── _harmonyos_compat.py + site.py 导入 + _bootsubprocess pipe workaround
```
