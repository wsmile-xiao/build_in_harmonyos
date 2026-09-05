# protobuf 21.12 适配笔记（3.21 线，无 Abseil）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-05
- 编译器: clang 15 (aarch64 OHOS)
- 状态: published

## 背景（为何新增此版本）
OLA 0.10.9 依赖 protobuf，但 OLA 代码仍是 C++11 世代（648 处
`std::auto_ptr`，`std::auto_ptr` 在 C++17 已被删除）。制品仓中已有
protobuf 33.6/33.6.1，其公开头文件经 Abseil 硬性要求 C++17，无法被
OLA 编译。21.12 是最后一代不依赖 Abseil、公开头文件保持 C++11 兼容
的版本（上游 protobuf >= 22 起引入 Abseil）。本 PR 发布该版本作为
OLA 的依赖（R36 依赖先发布）。

## 编译步骤
1. conan create（cmake，protobuf_BUILD_TESTS=OFF/CONFORMANCE=OFF/
   EXAMPLES=OFF、PROTOC_BINARIES=ON、LIBPROTOC=ON、WITH_ZLIB=OFF）
2. package() 中把安装的 protobuf.pc / protobuf-lite.pc 的绝对 prefix
   改写为 `prefix=${pcfiledir}/../..` 相对形式，保证 conan 缓存可迁移。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误报 python | 检测器把 v21.12 全语言仓库（java/csharp/python/ruby/php 等子目录）统计为 python，忽略主构建系统 CMakeLists.txt | 记录证据后按 cpp 继续（cmake 主工程，上游即 C++ 项目） |
| 2 | 上游单测未引入 | 21.12 gtest 单测需 configure 期从 GitHub 拉取 googletest 且体量巨大 | 由 test_package 程序化测试复现上游语义（见 MANIFEST.yml） |

## 源码修改
无（补丁为空；无需 __OHOS__ 平台宏）

## 依赖版本
无（21.12 零外部依赖，zlib 默认关闭）

## 验证结果
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 ...
# test_package: dynamic/pool/arena/parse_error 四场景 + protoc --version
# ctest 全绿
```

## 注意事项
- 此版本面向 C++11/C++14 时代消费者（OLA 0.10.9）；新项目应优先使用
  protobuf 33.x。
- commands.json / 软件级 manifest 追加 21.12 条目。
---

**编译结束**: 2026-09-05 13:58
**最终状态**: built
