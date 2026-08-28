# argparse

## 软件描述
argparse 是一个 header-only 的 C++17 命令行参数解析库，借鉴 Python argparse 的设计，提供简洁、现代、类型安全的 CLI 参数解析能力。

## 功能概述
- **参数解析**：positional/optional 参数、flag、选项组（`argparse::ArgumentParser`）
- **类型安全**：自动类型转换（int/double/string/vector 等）
- **子命令**：支持嵌套子命令
- **校验**：参数范围/choices 校验
- **帮助/错误**：自动生成 help，解析错误带格式输出

## OHOS 适配

### 构建方式
- **header-only C++17**：无库编译——`package()` 拷贝 `include/argparse/argparse.hpp`（单头文件）到 include
- CMake 构建（`ARGPARSE_BUILD_TESTS=OFF` 打包；测试单独 `ARGPARSE_BUILD_TESTS=ON` 构建）

### 关键攻坚点
1. **header-only**：单头文件——aarch64 OHOS 直接可编译（无平台限制）
2. **上游测试实测**：doctest 单元测试（test/ 自带 doctest.hpp——无需网络下载）——`ARGPARSE_BUILD_TESTS=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 3.2 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/p-ranav/argparse
- 文档: https://p-ranav.github.io/argparse/
