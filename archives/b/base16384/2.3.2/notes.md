# base16384 2.3.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-21
- 编译器: clang/clang++
- 状态: built (前置适配完成，待真机验证)

## 编译步骤

1. 源码解压后进入目录，标准 CMake 流程：
   ```
   cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<prefix> ..
   cmake --build .
   cmake --install .
   ```
2. 安装产物：
   - `bin/base16384` — 命令行编解码工具
   - `lib/libbase16384.so` / `lib/libbase16384.a` — 共享/静态库
   - `include/base16384.h` — 公共头文件
   - `share/man/man1/base16384.1` — man 手册

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 最低版本 2.8.12 过旧 | OHOS clang 工具链可能要求 cmake_minimum_required >= 3.5 | patch 修改为 3.5 |

## 源码修改

- `0001-CMakeLists.txt-portability.patch`: cmake_minimum_required 2.8.12 → 3.5

## 依赖版本

无外部依赖（纯 C 标准库）。

## 验证结果

```bash
# 待真机验证
# CI_PACKAGES="archives/b/base16384/2.3.2" zsh ci/conan/build_and_test.sh
```

## 注意事项

- 许可证为 GPL-3.0-or-later，与依赖项目的许可证需注意兼容性
- 上游 CMakeLists.txt 无条件同时构建 shared/static，Conan 的 BUILD_SHARED_LIBS 变量仅影响默认链接
- 上游测试通过 `cmake -DBUILD=test ..` 开启，定义 BASE16384_BUFSZ_FACTOR=1 减小缓冲区以增加边界测试覆盖
