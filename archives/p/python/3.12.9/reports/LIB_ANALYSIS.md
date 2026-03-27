# Python 3.12.9 Lib/ 标准库鸿蒙适配变更分析报告

> **日期**: 2026-03-27 | **基于**: 子任务 task_mn8bfn01_9xn0

---

## 重要纠正

**subprocess.py 中的 `_posixsubprocess` 在 3.12.9 中仍然作为 C 扩展导入**，并未内联。
（`from _posixsubprocess import fork_exec as _fork_exec`，行 102）

## 标准库适配需求总表

| # | 文件 | 存在 | 难度 | 主要适配内容 |
|---|------|------|------|-------------|
| 1 | **subprocess.py** | ✅ | 🔴 高 | `_posixsubprocess` C 扩展、shell 路径、`_use_posix_spawn()` 鸿蒙分支 |
| 2 | **multiprocessing/context.py** | ✅ | 🟡 中 | 默认启动方法改 spawn |
| 3 | **multiprocessing/util.py** | ✅ | 🟢 低 | abstract sockets |
| 4 | **multiprocessing/heap.py** | ✅ | 🟢 低 | `/dev/shm` 已有 fallback |
| 5 | **venv/__init__.py** | ✅ | 🟢 低 | lib64 symlink 添加 try/except（symlink_or_copy 已有回退） |
| 6 | **sysconfig.py** | ✅ | 🟡 中 | `get_platform()` 添加鸿蒙分支 |
| 7 | **distutils/** | ❌ | 🟢 低 | 已移除，原补丁不再需要 |
| 8 | **_bootsubprocess.py** | ❌ | 🟢 低 | 已移除，无需处理 |
| 9 | **posixpath.py** | ✅ | 🟢 低 | `defpath` 修改 |
| 10 | **ctypes/util.py** | ✅ | 🟡 中 | 无 ldconfig，需鸿蒙实现 |
| 11 | **shutil.py** | ✅ | 🟢 低 | sendfile 性能优化（可选） |
| 12 | **tempfile.py** | ✅ | 🟢 低 | 依赖 TMPDIR |
| 13 | **uuid.py** | ✅ | 🟡 中 | MAC 地址获取分支 |
| 14 | **_harmonyos_compat.py** | ❌ | 🟡 中 | 需新建 |
| 15 | **site.py** | ✅ | 🟢 低 | 兼容层加载 |

## subprocess.py 关键细节

- `_can_fork_exec` (行76): 排除 emscripten/wasi，**未排除鸿蒙**
- `_use_posix_spawn()` (行697-742): darwin/sunos5 直接 True，Linux 需 glibc ≥ 2.24
- `unix_shell` (行1763): 仅 Android 特殊处理 `/system/bin/sh`
- `_USE_VFORK` (行748): 默认启用，需评估鸿蒙 vfork 支持

## 有利变化

- distutils 移除 → 补丁 0005/0024 不再需要
- venv symlink_or_copy 已有回退 → 补丁 0011 大部分不再需要
- _bootsubprocess.py 移除 → 补丁 0006 不再需要
