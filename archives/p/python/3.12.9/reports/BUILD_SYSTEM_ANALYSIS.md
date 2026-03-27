# Python 3.12.9 构建系统全面分析报告（鸿蒙适配视角）

> **日期**: 2026-03-27 | **基于**: 子任务 task_mn8bfl9l_8y3z

---

## 核心发现

1. **Python 3.12.9 整个源码树中 `__OHOS__` 出现次数：0** — 需要从零开始适配
2. **setup.py 已完全移除** — 模块构建由 configure.ac + Modules/Setup 机制替代
3. **config.guess/config.sub 无 HarmonyOS 支持** — 需要添加
4. **PY_STDLIB_MOD 宏系统（105处使用）**是 3.12 新的模块构建核心
5. **Modules/_posixsubprocess.c 仍然存在**（1251行），并未内联到 subprocess.py

## configure.ac 关键位置

### 平台检测入口
- **交叉编译 host case** (行 539-566): 需新增 `*-*-ohos*` 分支
- **MACHDEP 映射** (行 583-589): 需新增 `ohos*` → `ohos`
- **_PYTHON_HOST_PLATFORM** (行 601-627): 需新增鸿蒙 CPU 映射
- **_XOPEN_SOURCE 控制** (行 640-725): 需考虑跳过
- **平台模块禁用 PY_STDLIB_MOD_SET_NA** (行 7282-7345): 需新增 HarmonyOS 分支

### 共享库变量
- **LDSHARED** (行 3386-3388): Linux* 分支已有 `$(CC) -shared`，鸿蒙需显式添加
- **LDLIBRARY** (行 1520-1524): Linux* 分支已有 `.so` 设置
- **LINKFORSHARED** (行 3501): Linux* 分支已有 `-Xlinker -export-dynamic`
- **BUILDEXEEXT** (行 1316-1328): 大小写检测可能误判

### 新增检测
- `getrandom`, `memfd_create`, `pidfd.h`, `copy_file_range`, `dup3`, `mremap`
- CAN_RAW_FD_FRAMES, CAN_RAW_JOIN_FILTERS

## 模块构建新架构

```
Modules/Setup.bootstrap.in → 引导静态模块（posix, _signal 等）
Modules/Setup.stdlib.in   → 标准库扩展模块（使用 @MODULE_XXX_TRUE@ 模板）
Modules/Setup.local       → 用户本地修改
configure.ac PY_STDLIB_MOD → 模块启用/禁用/检测
Modules/makesetup          → 生成 Modules/config.c 和 Makefile 规则
```

## 必须修改的 P0 位置

| 文件 | 行号 | 修改 |
|------|------|------|
| configure.ac | 543-566 | host case 新增 `*-*-ohos*` |
| configure.ac | 583-589 | MACHDEP 映射新增 |
| configure.ac | 601-627 | _PYTHON_HOST_PLATFORM |
| configure.ac | 7282-7345 | PY_STDLIB_MOD_SET_NA |
| config.guess | — | HarmonyOS 识别 |
| config.sub | — | ohos 操作系统 |
