# Blend2D 0.21.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27 (conan 适配 v2)
- 编译器: clang/clang++ (OHOS profile)
- 状态: built (conan-verify 通过)

## 源码
- 官方下载: https://blend2d.com/download/blend2d-0.21.2.tar.gz
- SHA256: 234ba57a64153c96885a6271f15fdcf6c594ac8cb03adaad19abb8d3b2b533fa
- 源码包含 asmjit (3rdparty/asmjit/)，无需外部依赖

## 编译步骤

1. 使用官方 blend2d.com 源码发布包（含 asmjit）
2. CMake 构建：BLEND2D_STATIC=ON, BLEND2D_TEST=OFF, BLEND2D_NO_JIT=OFF
3. Conan 配方验证通过 (G1-G4 + L2/L4/L5)

## 平台兼容性
- CMake 平台检测走 else() 分支，正确链接 libc/pthread/libm
- futex 实现使用 __linux__ 宏和 SYS_futex 系统调用
- 无需源码补丁

## 历史记录
- 2026-05-30: 首次编译（非 conan 方式）
- 2026-08-27 v1: 使用 GitHub commit + 独立 asmjit 下载
- 2026-08-27 v2: 改用官方 blend2d.com 源码（内置 asmjit），简化 conandata.yml

## 关闭
COMPLETED
---

**编译结束**: 2026-08-27 17:09
**最终状态**: published
