# tree-sitter 0.25.1 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-08-21
- 编译器: clang/clang++ (通过 Conan VirtualBuildEnv 注入)
- 状态: published

## 版本说明

0.25.1 是 0.25 的适配修复版本（R37），修复内容：
- R33 修复：移除硬编码 `CC=clang AR=llvm-ar RANLIB=llvm-ranlib`，改用 Conan VirtualBuildEnv 从 profile 注入编译器
- 添加 `generate()` 方法使用 VirtualBuildEnv
- `url` 字段改为 GitCode 仓库地址（R39 合规）
- 移除空的 `requirements()` 方法

## 编译步骤

```bash
# tree-sitter 使用纯 Makefile，无需 configure
# CC/CXX/AR 由 Conan VirtualBuildEnv 从 profile tools.build:compiler_executables 注入
make -j1  # env="conanbuild"
```

## 源码修改

无补丁，tree-sitter 0.25.0 在鸿蒙平台上原生编译通过。

## 依赖版本

无外部依赖。tree-sitter 核心库是纯 C 实现。

## 验证结果

- conan-verify 全部通过 (G1/G2/G3/G4/L2/L4/L5)
- W3 本地 CI 模拟通过

## 注意事项

- tree-sitter 上游测试套件需要 Rust/cargo 环境，跳过不影响核心 C 库
- tree-sitter 不是系统同名库，R26 不适用
- 构建产物包含 .a (静态) 和 .so (共享)，Conan 配方默认静态
---

**编译结束**: 2026-08-21 16:24
**最终状态**: published
