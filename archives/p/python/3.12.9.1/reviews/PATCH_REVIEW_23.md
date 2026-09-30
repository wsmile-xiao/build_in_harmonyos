# Python 3.12.9 鸿蒙适配补丁 — 全面审查报告

> 审查日期: 2026-03-31
> 补丁总数: 23 个（0001-0023）
> 源码版本: Python 3.12.9

---

## 总览

| 结论 | 数量 | 补丁编号 |
|------|------|---------|
| ✅ 必要 | 16 | 0001, 0002, 0003, 0004, 0006, 0007, 0008, 0009, 0012, 0013, 0015, 0016, 0017, 0018, 0022, 0023 |
| ✅ 必要但可优化 | 3 | 0005, 0020, 0019 |
| ⚠️ 存疑 | 2 | 0010, 0011 |
| ❓ 需验证 | 1 | 0014 |

---

## 逐补丁详情

### 第一组: 平台检测 + 构建系统（0001-0005, 0021）

| 补丁 | 结论 | 关键发现 |
|------|------|---------|
| **0001** config.guess | ✅ 必要 | 上游无 HarmonyOS 支持，必须添加 |
| **0002** config.sub | ✅ 必要 | 同上 |
| **0003** configure.ac | ✅ 必要 | MACHDEP=ohos + 20+ 处平台判断均正确。**⚠️ lchmod 跳过逻辑当前是直接编辑到源码的，不在 0003 补丁文件内（在 0020 中），应合并到 0003** |
| **0004** Makefile.pre.in HARDLINK | ✅ 必要 | `uname -s` 返回 "HarmonyOS"，grep -qi harmony 匹配正确。**⚠️ 建议**: bininstall L2049-2076 的 `$(LN) -s` 也需检查；`HARMONYOS_MODLIBS` 每次 make 都执行子进程 uname，建议改为 configure 一次性检测 |
| **0005** Setup.stdlib.in sysroot | ⚠️ 可优化 | 3.12 已有 `PKG_CHECK_MODULES` 机制，若 SDK 提供正确 .pc 文件则此补丁可省略。建议作为可选 fallback 保留 |
| **0021** Makefile HMDFS symlink | ✅ 必要 | 与 0004 **不是重叠，是分层修复**: 0004 解决 `ln -sf` 命令级兼容，0021 解决 HMDFS 符号链接无法被 `ld.lld` 追踪的运行时问题 |

### 第二组: C 扩展模块（0006-0010, 0019）

| 补丁 | 结论 | 关键发现 |
|------|------|---------|
| **0006** pythread.h PY_HAVE_THREAD_NATIVE_ID | ✅ 必要 | configure.ac **无** HAVE_GETTID 检测，平台宏是唯一选择 |
| **0007** thread_pthread.h gettid 实现 | ✅ 必要 | 与 0006 配套，缺一不可 |
| **0008** _posixsubprocess.c FD_DIR | ✅ 必要 | 鸿蒙无 procfs，`/proc/self/fd` 不存在，`/dev/fd` 是唯一选择 |
| **0009** timemodule.c musl 时区 | ✅ 必要 | 3 处修改全部必要，构成 声明→使用→初始化 完整链（musl tm_zone 问题是已知 bug bpo-34672） |
| **0010** posixmodule.c cpu_count | ❌ **存疑** | 位于 `HAVE_SYSCONF #elif` 分支之后，是**死代码**。`HAVE_SYSCONF=1` 已由 configure 检测，cpu_count 走的是 sysconf 分支而非 /proc 分支。**建议移除** |
| **0019** posixmodule.c sendfile | ✅ 必要 | ⚠️ **标题错误** — 实际修改的是 sendfile NULL offset 而非 fallocate。posix_fallocate 已被 AC_CHECK_FUNCS 自动检测为不可用（如确实不可用），无需额外守卫 |

### 第三组: Python 标准库（0011-0018）

| 补丁 | 结论 | 关键发现 |
|------|------|---------|
| **0011** sysconfig.py get_platform | ❌ **存疑** | 🔴 **高优先级**: 当前返回 `ohos-aarch64` 会导致 pip 无法匹配 PyPI 任何 wheel 标签。pip 的 musllinux 检测期望平台以 `linux` 开头。**建议改为 `linux-<machine>`** 让 pip 正确生成 musllinux 兼容标签 |
| **0012** posixpath.py defpath | ✅ 必要 | 鸿蒙可执行文件在 `/system/bin`，默认 PATH 需包含 |
| **0013** subprocess.py posix_spawn | ✅ 必要 | musl 平台默认使用 posix_spawn 合理。**⚠️ 有 fd 泄漏隐患**: 放宽 posix_spawn 快速路径允许 `close_fds=True` 后，`_posix_spawn()` 方法未实现 fd 关闭逻辑，长期运行可能耗尽 fd |
| **0014** _harmonyos_compat.py | ❓ **需验证** | musl 下 subprocess 使用 posix_spawn（不走 fork+exec），理论上不应有 SELinux 问题。3.12 上是否还需要这个 monkey-patch 需编译后实际验证。此外 mode='w' 的 os.popen() 未实现 |
| **0015** site.py 加载兼容层 | ✅ 必要 | 依赖 0014 结论。若 0014 移除则此补丁也应移除 |
| **0016** multiprocessing context.py spawn 默认 | ✅ 必要 | `hasattr(os, 'fork')` 检查设计优秀，比硬编码平台名更通用 |
| **0017** multiprocessing util.py abstract socket | ✅ 必要 | 鸿蒙无 `/proc/net/unix` |
| **0018** venv __init__.py symlink | ✅ 必要 | 3.12.9 原始 venv 对 lib64 symlink 直接调用 `os.symlink()` 无回退，HMDFS 上会失败 |

### 第四组: 聚合修复 + 新增（0020, 0022, 0023）

| 补丁 | 结论 | 关键发现 |
|------|------|---------|
| **0020-a** pylifecycle.c is_valid_fd | ✅ 必要 | 不加 `__OHOS__` 则所有条件分支都不匹配 |
| **0020-b** shutil.py sendfile | ✅ 必要 | `HAVE_SENDFILE=1` 已在 pyconfig.h 中定义，但 `sys.platform != 'linux'` 导致优化被跳过。⚠️ **需验证**: 鸿蒙 sendfile(2) 语义是否与 Linux 完全一致 |
| **0020-c** tempfile.py 临时目录 | ⚠️ **可优化** | `/data/local/tmp` 是 Android 惯例非鸿蒙，else 分支已含 `/tmp` `/var/tmp`。**建议删除此子项** |
| **0020-d** uuid.py MAC 查找 | ⚠️ 可优化 | PATH 通常已含 `/system/bin`，保留无害但不必要 |
| **0020-e** configure lchmod | ✅ 必要 | **⚠️ 组织问题**: 此修改在 0020 聚合补丁中，但属于 configure 阶段逻辑。**应合并到 0003** |
| **0022** compileall.py hardlink | ✅ 必要 | 方案合理。建议 `sys.platform == 'ohos'` 改为 `startswith(('ohos', 'harmonyos'))` 与其他补丁保持一致 |
| **0023** ctypes/util.py ldconfig | ✅ 必要 | 守卫在函数入口，覆盖完整 |

---

## 🔴 需要立即修复的问题

### 1. 0011 sysconfig.get_platform() 返回值（影响 pip）

**问题**: 返回 `ohos-aarch64` 导致 pip 无法匹配任何 wheel 标签。
**建议**: 改为返回 `linux-{machine}`，让 pip 走 musllinux 兼容路径。
**影响**: 所有用 pip 安装二进制包的操作。

### 2. 0020-e lchmod 修改应合并到 0003

**问题**: 当前 lchmod 跳过逻辑不在 0003 补丁文件中，重新打补丁会丢失。
**建议**: 将 `test "$MACHDEP" != ohos` 条件合并到 0003 configure.ac 补丁。

### 3. 0010 cpu_count 补丁是死代码

**问题**: 在 `HAVE_SYSCONF` 分支之后，永远不会执行。
**建议**: 删除此补丁。

### 4. 0019 补丁标题错误

**问题**: 标题含 "fallocate" 但实际修改的是 sendfile。
**建议**: 修正标题为 `Modules-posixmodule.c-OHOS-sendfile.patch`。

---

## ⚠️ 编译后需验证的项

| # | 验证项 | 验证方法 |
|---|--------|---------|
| 1 | 0014 _harmonyos_compat.py 是否必要 | 编译后直接运行 `os.system("echo hello")` 和 `os.popen("ls").read()`，看是否报错 |
| 2 | 鸿蒙 sendfile(2) 语义 | 对比 `shutil.copyfile()` 和 sendfile 路径的输出结果 |
| 3 | 0013 close_fds fd 泄漏 | 长时间运行的 Popen 子进程观察 fd 数量增长 |

---

## 📊 与 3.9.25 对比的关键改进

3.9.25 的 72 个补丁中，以下类别在 3.12 上已不再需要：
- `distutils/` 适配（3.12 已移除 distutils）
- `_bootsubprocess.py`（文件已移除）
- `setup.py` 构建逻辑（3.12 用 `Setup.stdlib.in` + `configure`）

3.12 新增的改进：
- 0007 使用 `gettid()` 替代 3.9 的可能绕过方案
- 0013 利用 musl 原生 posix_spawn 支持（3.9 可能需更多 workaround）
- 0016 使用 `hasattr(os, 'fork')` 动态检测而非硬编码平台名
