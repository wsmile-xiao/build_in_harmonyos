# mpack-msgpack 1.1.1 适配笔记

## 编译环境
- 构建系统: cmake（源码包无 CMakeLists.txt，由 conanfile.py 生成）
- 编译日期: 2026-07-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 mpack v1.1.1 源码包并解压
2. 源码包不包含构建库的 CMakeLists.txt（上游构建系统仅用于运行单元测试，使用 Python + Ninja）
3. 在 conanfile.py build() 方法中生成 CMakeLists.txt，将 src/mpack/ 下的 6 个 .c 文件编译为 libmpack.a 静态库
4. 使用 Conan CMakeToolchain 处理 OHOS aarch64 工具链（CI 环境为鸿蒙 PC，build 与 host 架构一致，不存在交叉编译）
5. 安装静态库到 lib/，头文件到 include/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包无构建系统 | MPack 设计为 amalgamation 嵌入式使用，不提供库构建系统 | 在 build() 中生成 CMakeLists.txt 编译源文件为静态库 |
| 2 | 与现有 mpack/1.6 命名冲突 | mpack/1.6 是 MIME 邮件工具，非 MessagePack 库 | 使用 mpack-msgpack 作为包名区分 |

## 源码修改

无补丁。仅添加 CMakeLists.txt（在 build() 中动态生成，不修改源码）。

## 依赖版本

无外部依赖。

## 验证结果

消费者测试 (test_package/test.c)：
- 编码 MessagePack 消息 {"compact": true, "schema": 42}
- 解码并验证 compact=true, schema=42
- 2 个断言全部通过

## 注意事项

- MPack 上游推荐使用 amalgamation 包（mpack.h + mpack.c 单文件）直接嵌入项目
- 本配方将完整源码编译为静态库，适合通过 Conan 管理依赖的场景
- 上游单元测试需要 Python 3 + Ninja 构建系统，未集成到 test_package。CI 环境为鸿蒙 PC（aarch64），test_package 消费者测试可直接运行（test_mpack 编码+解码往返验证）
- 本包（mpack-msgpack）与仓库中已有的 mpack/1.6（MIME 邮件打包工具）是完全不同的软件
