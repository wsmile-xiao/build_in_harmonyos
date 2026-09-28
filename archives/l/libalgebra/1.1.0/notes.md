# libalgebra 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无编译产物；Conan header-library 打包）
- 编译日期: 2026-09-22
- 编译器: clang/clang++（aarch64-unknown-linux-ohos clang 15.0.4）
- 状态: built

## 编译步骤

```bash
# 1) 源码下载（官方 tag v1.1.0，SHA-256 c0d6a81ad...）
#    https://github.com/mklarqvist/libalgebra/archive/refs/tags/v1.1.0.tar.gz
# 2) 头文件编译验证（patch 0001 守卫 x86intrin.h 后）
clang -O2 -fPIC -std=c11 -I <src> -o header-smoke header-smoke.c   # exit 0, 运行 OK
# 3) 上游 CMake 配置/构建验证
cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX=<prefix>   # exit 0
make -j2            # benchmark.cpp 为 x86 专用汇编，aarch64 不可编译（exit 2，记录为样例限制）
make check          # 上游无测试目标（No rule to make target 'check'）
# 4) Conan 配方（header-only）→ conan-verify 8 门禁全部 PASS → finish W3 本地 CI PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libalgebra.h` 在 aarch64 编译失败（`x86intrin.h` 仅限 x86） | 上游第 107 行无条件 `#include <x86intrin.h>`（仅排除 _MSC_VER） | 补丁 0001：以 X86_OR_X64 家族宏守卫（与头文件既有平台分支一致，非 __OHOS__ 宏） |
| 2 | 上游 `benchmark.cpp` 在 aarch64 不可编译（CPUID/rdtsc 内联汇编） | x86 专用基准样例，非测试用例 | 不打包、不纳入用例计数；header-only 库仅交付头文件（见 test-ledger.md） |
| 3 | Conan 2 `package(): No files in this package!` | `copy()` 相对 dst 未解析到 package_folder | 用 `os.path.join(self.package_folder, ...)` 绝对目标路径；`package_type = "header-library"` |
| 4 | CMake 4.x 拒绝 `cmake_minimum_required(VERSION 2.8)` | 上游 CMakeLists 过旧 | 本地配置加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（仅验证用；交付配方为 header-only 不构建上游 CMake） |
| 5 | W3 JC 门禁命中其他库基线文件（cloog/kics 的 .build-closed/.staging-verified） | 其他库提交前已存在的空状态标记被 git 跟踪 | 按基线隔离规程：记录路径+隔离前 SHA-256（e3b0c442...空文件）→ 临时隔离 → 复跑门禁通过 → 原样恢复并核对哈希一致；不修改/不提交该基线文件 |

## 源码修改

- `patches/0001-libalgebra.h.patch`：`#include <x86intrin.h>` 增加
  `__i386__/__x86_64__/_M_IX86/_M_X64` 架构守卫（+3/-1）

## 依赖版本

无第三方依赖（header-only 单头文件库）。

## 验证结果

```bash
# conan-verify（ohos-aarch64 profile）: G0-G4 + L2/L4/L5 全部 PASS
# finish W3 本地 CI 模拟: setup.sh + build_and_test.sh 通过（基线隔离复验后）
# conan create test_package: ctest 2/2 通过
#   1/2 Test #1: test_libalgebra ... Passed 0.03 sec  （消费者用例）
#   2/2 Test #2: test_ohos ... Passed 0.02 sec        （鸿蒙专项测试）
```

## 知识候选（详见 knowledge 候选台账）

- E 候选：header-only 单头文件库在 aarch64 无条件包含 x86intrin.h 的通用
  守卫模式（跨库可复用）。
---

**编译结束**: 2026-09-22 01:46
**最终状态**: built
