# cbitset 0.4.0 适配记录

## W0/W0b

- 任务为无依赖 C 依赖项；preflight 检查未发现未发布依赖。
- 上游源码为 CMake 项目，不需要额外工具链或运行时依赖。
- 官方源码：`https://github.com/lemire/cbitset/archive/refs/tags/v0.4.0.tar.gz`
- SHA-256：`ee96e7bf000f495e69a813aed59af8b1386b20472b105d1cb96d60c4261de4f4`。

## 适配与测试

- Conan recipe 使用 `CMakeToolchain`/`cmake_layout`，默认静态库；打开上游 `CBITSET_BUILD_TESTS`，关闭 benchmarks。
- `build()` 调用 `cmake.test()` 执行官方 CTest `unit` 测试。
- 上游 `tests/unit.c` 包含 15 个测试函数、40 个 `TEST_ASSERT` 调用。
- `test_package` 真实调用 `bitset_create`、`bitset_set`、`bitset_count`、`bitset_get`、`bitset_minimum`、`bitset_maximum`、`bitset_next_set_bit`、`bitset_clear` 和 `bitset_empty`。

## 路径判断

- 当前改动是该库自身的 CMake/Conan 适配，不形成可复用于其他库的新知识，按路径 A 处理；若后续验证出新的跨库 CMake/Conan 规则，将另行沉淀为知识库扩展。
### 对话 #1（2026-09-03）

- 自动生成的 Autotools 配方与上游 CMake 构建系统不一致；已按源码 CMakeLists.txt 重写为 CMakeToolchain/cmake_layout 配方。
- G1 首轮要求显式 `export_sources()`，已补齐并复跑通过。
- Conan create、上游 CTest、test_package、verify-build 与 W3 本地 CI 均通过；从已验证 Conan package 生成 OHOS arm64 归档。

## 结束

最终状态: built

## W4 修复（2026-09-03）

- 按独立审计要求，test_package 改为显式执行 `ctest --test-dir . --output-on-failure`，确保消费者测试由 AST 可见的运行命令真实执行。
- `conandata.yml` 仅保留官方 GitHub tag URL；gh-proxy 由下载器 fallback 处理，不写入归档。
- 补齐软件级 `archives/c/cbitset/manifest.yaml`，版本级测试统计保持上游 15 个测试函数 + 消费者 1 项 = 16。
- finish 后需再次检查并清理临时 ghfast 备份，确认官方 URL 仍是归档中的最终内容。
---

**编译结束**: 2026-09-03 11:56
**最终状态**: built
