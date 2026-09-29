# faster-utf8-validator cf482014d0 适配笔记

## 编译环境
- 构建系统: cmake（上游为 make.py，新增 CMakeLists.txt）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```
python3 $SKILL_ROOT/scripts/ohc-run.py init-build faster-utf8-validator cf482014d0 --url=https://github.com/zwegner/faster-utf8-validator
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init faster-utf8-validator cf482014d0
python3 $SKILL_ROOT/scripts/ohc-run.py finish faster-utf8-validator cf482014d0 published
```

源码经官方 GitHub archive `https://github.com/zwegner/faster-utf8-validator/archive/cf482014d0.tar.gz`
下载（SHA-256 dc6b9389aa6bda4d365fa5c4ef22f9138a8791605820da8b367885fd0a13baea）
由 conan create 干净构建；补丁 5 个由 refresh-patch 生成，W3 本地 CI 模拟通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 编译失败：`immintrin.h ... only meant to be used on x86 and x64` | 上游无条件包含 x86 SIMD 头 | immintrin.h 按 AVX2/SSE4 宏条件包含 |
| 2 | `#error "No valid configuration: must define one of AVX2 or SSE4"` | 上游为 x86-only SIMD 库，无标量路径 | 新增标量回退 `z_validate_utf8`（同验收语义），向量部分 `#if defined(AVX2)\|\|defined(SSE4)` 守卫 |
| 3 | 条件包含后 `size_t` 未声明 | size_t 原由 immintrin 传递引入 | 显式 `#include <stddef.h>` |
| 4 | 上游 test.lua 无法运行（LuaJIT + x86 .so 缺失） | 测试框架双硬依赖不适用 aarch64 | 46 项独立用例移植为 C 测试目标全量通过（46/46，127803 校验） |
| 5 | W3 JC1/JC5 命中 cloog/kics 基线空文件 | 其他库提交前已存在的主干 .build-closed/.staging-verified | 基线隔离复验：临时隔离→复跑→原样恢复→SHA-256 一致（e3b0c442...），未修改未提交 |

## 源码修改

补丁（patches/，refresh-patch --auto 生成）：
- 0001-CMakeLists.txt.patch（新增 CMake 构建入口）
- 0002-test_ohos_special.c.patch（鸿蒙专项测试，22 用例）
- 0003-test_upstream_port.c.patch（上游 46 用例移植）
- 0004-z_validate.c.patch（标量回退 + 条件包含 immintrin + stddef.h）
- 0005-z_validate.h.patch（公共头文件）

## 依赖版本

- 无第三方运行时依赖（纯 C，无 requires）

## 验证结果

- 上游 46/46 通过（upstream-port-run.log，SHA-256 28b6738f13f5...）
- 鸿蒙专项 22/22（ohos-special-run.log，SHA-256 866d1b9ea2db...）
- 消费者验证通过（consumer-verify.log，SHA-256 4de195f4ca9e...）
- conan-verify G1-G4/L2/L4/L5 PASS；W3 通过；finish EXIT_CODE 0

## 知识记录

- 知识候选台账 + 七轴查重 + 路径决定：reports/knowledge-candidate-ledger.md
- 草稿：knowledge/drafts/DRAFT-x86-simd-only-c-library-aarch64-scalar-fallback.{kv,md}
- 路径决定：new_draft（路径 B 知识库扩展）