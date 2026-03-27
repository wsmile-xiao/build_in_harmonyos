# Python 3.12.9 补丁可复用性评估报告

> **日期**: 2026-03-27 | **基于**: 3.9.0 24 补丁 vs 3.12.9 源码全量分析
> **结论先行**: 5 个可直接复用 / 7 个需修改 / 6 个不再需要 / 6 个需重写

---

## 总览

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| ✅ 直接复用 | 5 | 21% | 源文件存在且上下文匹配 |
| ⚠️ 需修改 | 7 | 29% | 逻辑相同但行号/代码结构变化 |
| ❌ 不再需要 | 6 | 25% | 文件已移除或上游已修复 |
| 🔄 需重写 | 6 | 25% | 构建系统架构变化或逻辑重构 |

---

## 逐一评估

### ✅ 直接复用（5 个）

| 补丁 | 文件 | 评估 | 说明 |
|------|------|------|------|
| **0003** | config.guess | ✅ 直接复用 | 文件结构相同，添加 HarmonyOS 检测逻辑 |
| **0004** | config.sub | ✅ 直接复用 | 文件结构相同，添加 linux-ohos 支持 |
| **0012** | Include/pythread.h | ✅ 直接复用 | `PY_HAVE_THREAD_NATIVE_ID` 条件添加 `\|\| defined(__OHOS__)`，3.12 中此宏已无条件定义但实现仍在 thread_pthread.h |
| **0014** | Lib/multiprocessing/util.py | ✅ 直接复用 | `_platform_supports_abstract_sockets()` 添加鸿蒙平台检测，代码结构相同（行108-113） |
| **0015** | Lib/posixpath.py | ✅ 直接复用 | `defpath` 从 `'/bin:/usr/bin'` 改为 `'/system/bin:/bin:/usr/bin:/usr/local/bin'`，代码结构相同（行21） |

### ⚠️ 需修改（7 个）

| 补丁 | 文件 | 评估 | 需修改的内容 |
|------|------|------|-------------|
| **0001** | configure.ac | ⚠️ 需大幅修改 | 3.12 的 configure.ac 结构有重大变化：新增 PY_STDLIB_MOD 宏系统(105处)、行号全面偏移、平台检测入口新增 Emscripten/WASI 分支。核心修改点（MACHDEP/LDSHARED/LDLIBRARY/LINKFORSHARED/CAN_RAW/XOPEN_SOURCE）逻辑相同但需重新定位行号 |
| **0007** | Makefile.pre.in | ⚠️ 需修改 | 3.12 中 sharedmods 构建机制变化（不再依赖 setup.py），HARDLINK/LN_FORCE 变量位置变化。`$(LN)` 变量（行1674-1677）已区分 CYGWIN。需检查 sharedmods 目标中 LDSHARED 的传递方式 |
| **0008** | Lib/sysconfig.py | ⚠️ 需修改 | `get_platform()` 在行753-832，逻辑结构相同但代码略有重构。需在 Linux 分支旁添加鸿蒙分支 |
| **0013** | Lib/multiprocessing/context.py | ⚠️ 需修改 | `get_all_start_methods` 在行260-268，`_default_context` 在行322-328。3.12 中 macOS 已改默认 spawn。需添加鸿蒙默认 spawn 逻辑 |
| **0017** | Modules/_posixsubprocess.c | ⚠️ 需修改 | 文件仍存在(1251行)，FD_DIR 定义在行63-66，逻辑完全相同。补丁可直接应用但需确认行号匹配 |
| **0019** | Modules/timemodule.c | ⚠️ 需修改 | musl tm_zone 条件在行613/665/2116，模式 `__linux__ && !__GLIBC__` 相同。需将条件扩展为 `(__linux__ \|\| defined(__OHOS__)) && !defined(__GLIBC__)` |
| **0021** | Python/thread_pthread.h | ⚠️ 需修改 | `PyThread_get_thread_native_id()` 在行326-352，平台分支链完整。需在 `__linux__` 分支旁添加 `__OHOS__` 分支（使用 syscall(SYS_gettid)） |

### ❌ 不再需要（6 个）

| 补丁 | 文件 | 评估 | 原因 |
|------|------|------|------|
| **0005** | Lib/distutils/util.py | ❌ 不需要 | **distutils 在 3.12 中完全移除** |
| **0006** | Lib/_bootsubprocess.py | ❌ 不需要 | **文件已移除**，3.12 构建不再需要 bootstrapping subprocess |
| **0011** | Lib/venv/__init__.py | ❌ 大部分不需要 | 3.12 的 `symlink_or_copy()` 方法（行247-264）**已有 try/except 回退机制**。但 lib64 symlink（行176-181）仍直接调用 `os.symlink`，此处仍需适配（小幅修改） |
| **0022** | Lib/ctypes/util.py | ❌ 不需要（改判断） | 3.12 中鸿蒙无 `/sbin/ldconfig` 时会因 OSError 自然返回空结果，**不会崩溃**（3.9 会 SubprocessError）。但仍建议添加显式跳过以避免错误日志 |
| **0024** | Lib/distutils/command/build_ext.py | ❌ 不需要 | **distutils 已移除**，但 setuptools 的 build_ext 可能需要类似修复（需验证） |

### 🔄 需重写（6 个）

| 补丁 | 文件 | 评估 | 重写要点 |
|------|------|------|---------|
| **0002** | setup.py | 🔄 需重写 | **setup.py 在 3.12 中完全移除**。模块构建由 `Modules/Setup.stdlib.in` + `configure.ac` 的 `PY_STDLIB_MOD` 宏控制。SDK sysroot 搜索逻辑需迁移到新的构建机制 |
| **0009** | Lib/_harmonyos_compat.py | 🔄 需重写 | 兼容层模块需要重新设计。3.12 中 `_bootsubprocess.py` 已移除，monkey-patch 的目标函数可能有变化。需要评估 3.12 中哪些运行时行为仍需要 monkey-patch |
| **0010** | Lib/site.py | 🔄 需重写 | 兼容层加载逻辑需要重新设计，与 0009 配套 |
| **0016** | Lib/subprocess.py | 🔄 需重写 | 3.12 的 subprocess.py 有重大变化：新增 `_use_posix_spawn()` 函数、`_can_fork_exec` 守卫、`_USE_VFORK` 开关。3.9 补丁 0016 的 541 行修改需要完全重新适配 |
| **0020** | Lib/subprocess.py | 🔄 需重写 | 依赖 0016，需要一起重新设计 |
| **0023** | 多文件遗漏修复 | 🔄 需重写 | 包含 pylifecycle.c/shutil.py/tempfile.py/configure/uuid.py 的修复。部分仍需要（pylifecycle.c fd 验证、uuid.py），部分可能已不需要。需要逐项重新评估 |

---

## 补丁依赖关系图

```
Phase 0 — 平台检测层:
  0003 (config.guess)     ✅ 直接复用
  0004 (config.sub)       ✅ 直接复用
  0001 (configure.ac)     ⚠️ 需修改（核心，影响一切）

Phase 1 — 构建执行层:
  0002 (setup.py)         🔄 需重写（→ Setup.stdlib.in 机制）
  0007 (Makefile.pre.in)  ⚠️ 需修改

Phase 2 — 运行时适配:
  0008 (sysconfig.py)     ⚠️ 需修改
  0005 (distutils/util)   ❌ 已移除
  0015 (posixpath.py)     ✅ 直接复用

Phase 3 — 子进程兼容:
  0006 (_bootsubprocess)  ❌ 已移除
  0009 (_harmonyos_compat) 🔄 需重写
  0010 (site.py)          🔄 需重写
  0016 (subprocess.py)    🔄 需重写
  0020 (subprocess.py)    🔄 需重写（依赖 0016）

Phase 4 — 功能修复:
  0012 (pythread.h)       ✅ 直接复用
  0014 (multiproc/util)   ✅ 直接复用
  0017 (posixsubprocess)  ⚠️ 需修改
  0019 (timemodule)       ⚠️ 需修改
  0021 (thread_pthread)   ⚠️ 需修改
  0013 (multiproc/context) ⚠️ 需修改
  0011 (venv)             ❌ 大部分不需要（lib64 处仍需小改）
  0022 (ctypes/util)      ❌ 不需要（改判断）

Phase 5 — 遗漏修复:
  0023 (多文件)           🔄 需逐项重写
  0024 (build_ext)        ❌ 已移除

3.12 新增需求（3.9 无对应补丁）:
  🆕 cpu_count /proc 回退
  🆕 _hacl/ 编译验证
  🆕 Programs/ 目录结构适配
  🆕 configure.ac PY_STDLIB_MOD_SET_NA 新增鸿蒙分支
```

---

## 工作量估算

| 分类 | 预估补丁数 | 工作量 | 风险 |
|------|----------|--------|------|
| ✅ 直接复用 | 5 | 低 | 低 |
| ⚠️ 需修改 | 7 | 中 | 中 |
| ❌ 不再需要 | 6 | 无（节省） | 无 |
| 🔄 需重写 | 6 | 高 | 高 |
| 🆕 新增需求 | 4 | 中 | 中 |
| **合计** | **约 22 个新补丁** | — | — |
