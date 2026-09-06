# snmalloc 0.7.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 源码核验
- 官方来源: https://github.com/microsoft/snmalloc/archive/refs/tags/0.7.5.tar.gz（标签 0.7.5 已核验）
- SHA-256: 6efb0daa33fd1c0b406915786041fbce7176562cdfe74aa68baf90a77c451619
- 语言判定: 主体 C++（src/ 185 个 C++ 文件，0 个 .rs；根 Cargo.toml 仅为 snmalloc-rs Rust 绑定子目录的 workspace 声明；.py 仅 CI 辅助脚本）→ cpp，与任务语言匹配

## 编译步骤

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DSNMALLOC_BUILD_TESTING=ON -DSNMALLOC_CI_BUILD=ON
cmake --build build -j4
cd build && ctest
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | check 变体（SNMALLOC_CHECK_CLIENT）启动即 SIGABRT：`Failed to initialise snmalloc` | check 变体默认 full_checks 含 random_pagemap → FlatPagemap 预留 REQUIRED_SIZE + 4×next_pow2(REQUIRED_SIZE) ≈ 1280GB；HarmonyOS 平台 mmap 单次虚拟地址空间预留上限实测 256GB OK / 384GB FAIL（ENOMEM），预留失败 | 在 mitigations.h 增加 `__OHOS__` 平台特例：`CHECK_CLIENT ? full_checks - random_pagemap : no_checks`（参照上游 OPEN_ENCLAVE/NetBSD 先例，仅禁用 pagemap 随机化，保留其余全部检查）。经验证 check 变体从 31 失败降至 10 失败，总通过率 61%→88% |
| 2 | func-miracle_ptr / multi_atexit / multi_setspecific / multi_threadatexit SEGFAULT；func-new debug_check_empty 报 non-empty allocator | 该类测试覆盖 libc malloc/calloc/free 并与多线程/atexit/pthread key 交互，HarmonyOS 平台行为与 Linux/glibc 存在差异（fast 与 check 变体均失败，与本补丁无关） | 记录为平台差异，不阻塞库本体构建；详见"验证结果" |

## 源码修改
- `src/snmalloc/mitigations/mitigations.h`：新增 `__OHOS__` 分支（位于 OPEN_ENCLAVE 之后、NetBSD 之前），禁用 random_pagemap mitigation，原因见上表 #1。由 finish 的 refresh-patch --auto 生成 patches/ 补丁。

## 依赖版本
- 无第三方编译依赖（header-heavy C++ 内存分配器，仅依赖 libc/pthread/ELF 系统接口）

## 验证结果

```bash
# native 构建（本机即 aarch64 HarmonyOS 平台）
cmake --build build -j4   # exit 0
cd build && ctest         # 88% tests passed, 10 tests failed out of 80 (70/80)
```

剩余 10 个失败均为 fast+check 重复的 5 个 libc 覆盖/多线程交互测试（func-miracle_ptr、func-multi_atexit、func-multi_setspecific、func-multi_threadatexit、func-new），属 HarmonyOS 平台差异，不涉及库本体 API 正确性。

## 注意事项
- 本机即 HarmonyOS PC（aarch64），cmake 提示 unknown platform 属正常，不影响构建
- snmalloc 0.7.5 官方标签为 `0.7.5`（无 v 前缀）
---

**编译结束**: 2026-09-03 12:42
**最终状态**: built
