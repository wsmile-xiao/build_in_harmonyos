# glob 0.0.1 适配笔记

## 编译环境

- 构建系统：CMake 3.14+，Conan 2.29.1
- 编译器：OpenHarmony PC aarch64 clang 15.0.4
- 标准：C++17
- 状态：built（待 W4/PR）

## W0/W1 事实

- 任务语言为 C++，语言预检检测为 C++，构建系统为 CMake。
- 源码只有 `include/glob/glob.h` 和 `source/glob.cpp` 两个库文件，无 Conan 依赖。
- 上游 CMakeLists 在 configure 阶段通过 CPM.cmake 下载 PackageProject.cmake；该网络依赖不适合离线 Conan/CI。
- 上游归档没有自动化测试目标；README 的 standalone 示例依赖 cxxopts，不能冒充库的上游测试。

## 路径与修改

- 路径 A：用 Conan CMake 配方构建并通过真实 test_package 消费 `glob::glob`。
- 路径 B：补充可复用的“离线 CMake 去网络依赖 + 显式安装规则”知识草稿，见 `knowledge/drafts/DRAFT-glob-0.0.1-cmake-offline-install.{kv,md}`。
- 补丁 `0001-CMakeLists.txt.patch`：移除 CPM/PackageProject 的 configure-time 网络下载，固定 `Glob` 为静态库，并添加 GNUInstallDirs 下的库和头文件安装规则。
- `shared=True` 明确拒绝，因为上游目标硬编码为 `STATIC`。

## 验证计划

- `conan-verify glob 0.0.1`：必须通过 G1/G0/G2/G3/G4/L2/L4/L5。
- `test_package/test.cpp` 创建真实目录和文件，验证 `glob`、`rglob("**")` 及多模式重载的返回路径；使用显式返回码，不依赖 Release 下可能被 `-DNDEBUG` 消除的 `assert()`。
- W3 记录 Release `test_glob` 的编译、链接和 CTest 结果；若上游无测试则如实记录，不伪造上游测试通过。

## 已知限制

- 包只提供静态库和头文件，不打包 standalone 命令行示例；该示例需要未随归档提供的 cxxopts。
---

**编译结束**: 2026-09-03 01:47
**最终状态**: built

### 对话 #1（2026-09-03）

- W0/语言预检通过；Conan verify、W3 本地 CI、verify-build 与 release 打包均通过。
- 上游没有自动化测试目标，消费者测试真实调用 `glob`/`rglob` API；未把 standalone cxxopts 示例冒充上游测试。
- 路径 B 草稿已随本归档记录离线 CMake 去网络依赖和补安装规则的可复用经验。

## 结束

最终状态: built
