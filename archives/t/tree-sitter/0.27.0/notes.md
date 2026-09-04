# tree-sitter 0.27.0 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-09-04
- 编译器: clang/clang++ (通过 Conan VirtualBuildEnv 注入)
- 状态: built

## 版本说明

0.27.0 是 tree-sitter 的新版本适配。

## 编译步骤

```bash
# tree-sitter 使用纯 Makefile，无需 configure
# CC/CXX/AR 由 Conan VirtualBuildEnv 从 profile tools.build:compiler_executables 注入
make -j1  # env="conanbuild"
```

## 源码修改

无补丁，tree-sitter 0.27.0 在鸿蒙平台上原生编译通过。

## 依赖版本

无外部依赖。tree-sitter 核心库是纯 C 实现。

## 验证结果

- conan-verify 全部通过 (G1/G2/G3/G4/L2/L4/L5)
- W3 本地 CI 模拟通过

## 注意事项

- tree-sitter 上游测试套件需要 Rust/cargo 环境，跳过不影响核心 C 库
- tree-sitter 不是系统同名库，R26 不适用
- 构建产物包含 .a (静态)，Conan 配方默认静态
- test_package 使用直接 clang 调用（非 CMake）以绕过 OHOS SDK lld/libxml2.so.16 问题
- test_package 使用 nm 符号验证（非直接执行）以绕过 OHOS SELinux 限制
---

**编译结束**: 2026-09-04 14:13
**最终状态**: built
