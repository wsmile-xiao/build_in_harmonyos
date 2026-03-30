# Python 3.12.9 — HarmonyOS 适配档案

> **状态**: ⚠️ partial — 仅完成 Phase 2 补丁开发，尚未编译验证  
> **日期**: 2026-03-27 | **补丁数**: 21 | **报告数**: 5

## 概要

Python 3.12.9 的鸿蒙适配已进入 **Phase 2: 补丁开发** 阶段。基于源码全量分析和 3.9.0 适配经验，已完成 21 个补丁的编写，覆盖平台检测、构建系统、C 扩展模块和标准库运行时适配。

### 与 3.9.0 的关键差异

| 特性 | Python 3.9.0 | Python 3.12.9 |
|------|-------------|---------------|
| 模块构建 | setup.py | **PY_STDLIB_MOD 宏系统**（105 处） |
| distutils | 存在 | **完全移除** |
| subprocess.py | 无 _use_posix_spawn() | 新增 _use_posix_spawn() + _can_fork_exec |
| venv symlink | 无回退 | symlink_or_copy() **已有 try/except** |
| 源码中 __OHOS__ | 3.9.0 适配后存在 | **0 处**（从零适配） |

## 补丁概览

```
Phase 2A: 平台检测层     0001-0003  (3 个) — config.guess, config.sub, configure.ac
Phase 2B: 构建系统层     0004-0005  (2 个) — Makefile.pre.in, Setup.stdlib.in
Phase 2C: C 扩展模块层   0006-0010  (5 个) — threading, subprocess, time, posix
Phase 2D: 标准库层       0011-0018  (8 个) — sysconfig, subprocess, multiprocessing, venv
Phase 2F: 补充修复       0019-0021  (3 个) — posixmodule, 遗漏修复, HMDFS
```

应用方式：`patch -p1 < patches/0001-xxx.patch`（按编号顺序）

## 风险评估摘要

- 🔴 **高风险** (6): configure 失败、SDK sysroot 缺失、BIND_NOW ImportError、subprocess 不可用、ctypes MemoryError、HMDFS symlink
- 🟡 **中风险** (7): MACHDEP 异常、.exe 误判、cpu_count 崩溃、时区异常、CAN socket、setuptools、venv
- 🟢 **低风险** (7): /tmp 只读、工具链、pidfd/getrandom（自动排除）等

详见 [reports/RISK_ASSESSMENT.md](reports/RISK_ASSESSMENT.md)

## 3.9.0 补丁可复用性

从 3.9.0 的 24 个补丁评估：

| 分类 | 数量 | 说明 |
|------|------|------|
| ✅ 直接复用 | 5 | config.guess, config.sub, pythread.h, multiprocessing, posixpath |
| ⚠️ 需修改 | 7 | configure.ac, Makefile, sysconfig, subprocess 等 |
| ❌ 不再需要 | 6 | distutils, _bootsubprocess 已移除 |
| 🔄 需重写 | 6 | setup.py→Setup.stdlib.in, subprocess 新架构 |
| 🆕 新增需求 | 4 | cpu_count, _hacl, Programs/, PY_STDLIB_MOD_SET_NA |

详见 [reports/PATCH_REUSABILITY.md](reports/PATCH_REUSABILITY.md)

## 下一步

1. **Phase 3: 编译验证** — 应用补丁，执行 configure + make，验证核心构建
2. **Phase 4: 运行时测试** — 验证 subprocess、threading、multiprocessing、ctypes 等
3. **Phase 5: 补充补丁** — 根据编译/测试结果补充测试跳过补丁

## 报告索引

| 报告 | 说明 |
|------|------|
| [BUILD_SYSTEM_ANALYSIS.md](reports/BUILD_SYSTEM_ANALYSIS.md) | 构建系统全面分析 |
| [MODULES_ANALYSIS.md](reports/MODULES_ANALYSIS.md) | C 扩展模块分析 |
| [LIB_ANALYSIS.md](reports/LIB_ANALYSIS.md) | 标准库适配变更分析 |
| [PATCH_REUSABILITY.md](reports/PATCH_REUSABILITY.md) | 3.9→3.12 补丁可复用性 |
| [RISK_ASSESSMENT.md](reports/RISK_ASSESSMENT.md) | 风险评估 |

## 参考

- [Python 3.9.0 编译档案](../3.9.0/manifest.yaml) — 已完成编译和测试验证
- [Python 3.9.25 编译档案](../3.9.25/manifest.yaml) — 基于升级补丁集编译
