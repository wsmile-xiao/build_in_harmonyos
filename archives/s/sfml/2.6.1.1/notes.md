# sfml 2.6.1.1 OpenHarmony PC 适配笔记

## 适配范围

本次 Conan 配方只交付 SFML 2.6.1.1 的 `System` 和 `Network` 模块：

- `sfml-system`
- `sfml-network`

`Window`、`Graphics`、`Audio` 暂不纳入本次基础适配：

- `Window` 需要 SFML 2.x 支持的 X11/DRM/UDev 等窗口和输入后端，当前 OHOS CI 环境不具备。
- `Graphics` 依赖 `Window` 提供渲染上下文，因此随 `Window` 一起关闭。
- `Audio` 依赖 OpenAL，当前基线没有可直接使用的已发布 OpenAL Conan 包。

这属于路径 A 基础适配，目标是先提供可被下游链接和使用的 System/Network 能力，不声明完整多媒体栈可用。

Conan 打包阶段会裁剪禁用模块对应的 `SFML/Audio`、`SFML/Graphics`、`SFML/Window` 头文件目录，以及 `sfml-all.pc`、`sfml-audio.pc`、`sfml-graphics.pc`、`sfml-window.pc`，避免下游误以为这些模块已经可用。

## 构建方式

构建系统：CMake。

主要 CMake 选项：

```text
BUILD_SHARED_LIBS=ON
SFML_BUILD_AUDIO=OFF
SFML_BUILD_WINDOW=OFF
SFML_BUILD_GRAPHICS=OFF
SFML_BUILD_EXAMPLES=OFF
SFML_BUILD_DOC=OFF
SFML_BUILD_TEST_SUITE=ON
```

## 补丁说明

- `0001-cmake-Config.cmake.patch`：让 SFML 的平台检测将 `HarmonyOS` 视为 Unix-like 目标，并启用 `SFML_OS_LINUX` 兼容路径。
- `0002-src-SFML-System-Unix-ThreadImpl.cpp.patch`：通过 CMake 功能检测生成 `SFML_HAS_PTHREAD_CANCEL`，没有 `pthread_cancel` 时退化为 `wait()` 回收线程，避免 `terminate()` 在用户线程仍运行时释放 `ThreadImpl`；同时跳过 `pthread_setcanceltype`。
- `0003-test-CMakeLists-enabled-targets.patch`：修正上游 `runtests` 目标，使其只依赖当前启用模块对应的测试目标；本包关闭 Window/Graphics/Audio 后，仍可构建并运行 System/Network 上游测试。
- 2026-08-14 清理：删除未被 `conandata.yml` 引用的 `0003-src-SFML-System-CMakeLists.txt.patch` 和 `0004-test-CMakeLists-gated-runtests.patch`，避免残留补丁误导测试覆盖口径。

旧 partial 归档里曾有 `Window` 模块 EGL/GLES 相关补丁，但其中包含机器本地 SDK 绝对路径；本次 Conan 配方禁用 `Window`，因此不携带该补丁，避免把不可复现路径带入 PR。

## 测试

`test_package` 使用消费者视角的 CMake 工程：

1. `find_package(SFML REQUIRED COMPONENTS system network)`。
2. 编译并链接 `SFML::System` 和 `SFML::Network`。
3. 运行 `test_sfml`，实际调用：
   - `sf::String::getSize()`
   - `sf::milliseconds().asMilliseconds()`
   - `sf::seconds(1).asMicroseconds()`
   - `sf::IpAddress::toString()`

上游测试清单已在 `test_package/MANIFEST.yml` 中按源码文件和 CTest 目标记录。当前交付模块对应的上游测试已纳入构建：`test-sfml-system` 覆盖 `Vector2.cpp`、`Vector3.cpp`，`test-sfml-network` 覆盖 `Packet.cpp`。Conan 配方开启 `SFML_BUILD_TEST_SUITE=ON`，构建后执行 `ctest --test-dir <build> -R 'test-sfml-(system|network)' --output-on-failure`。

经核对上游 2.6.1 的 `test/` 目录，共有 4 个测试源文件：`System/Vector2.cpp`、`System/Vector3.cpp`、`Network/Packet.cpp`、`Graphics/Rect.cpp`。其中 3 个属于本次交付的 System/Network 模块并已纳入测试，1 个 Graphics 用例因模块关闭而排除；`Window` 和 `Audio` 在上游 `test/` 中没有独立测试源文件，因此不存在被漏掉的可用用例。

完整上游图形测试 `test-sfml-graphics` 仍不纳入当前 PR，因为本次路径 A 包明确关闭 `Window`、`Graphics`、`Audio`，其中 `Graphics/Rect.cpp` 依赖未交付的 Graphics 模块，启用后会连带要求 Window/OpenGL 上下文支持。该排除项已在测试清单中单独说明，不再把未执行的完整套件误写为已通过。

当前分支对应的 CI `#20572`（head `30b86659d4c20b597eca5ae014e553d851374156`）已通过，包含 `conan test_package`、L0、L1。2026-08-14 OpenDesk 真机队列任务 `20260814-070628-bfc89f-20260814-misc2-3053-3057-3058-r1` 在当前 head `24b85f30e` 完成复验：`test-sfml-system` 与 `test-sfml-network` 均通过，`test_package` 输出 `sfml system/network smoke test passed`，Build Summary Total 1 / Success 1 / Failed 0。

## Verification status

The current candidate branch has passed recipe-level checks on the server control host:

- `python3 -m py_compile` passed.
- `conan inspect archives/s/sfml/2.6.1.1` passed.
- Both patches apply cleanly to the official `2.6.1.tar.gz` source with `git apply --check`.
- A non-target Linux `conan create archives/s/sfml/2.6.1.1 --build=sfml/*` passed, and `test_package` really ran with output `sfml system/network smoke test passed`.
- The generated package contains the two intended libraries and only the `sfml-system.pc`/`sfml-network.pc` pkg-config files after disabled-module pruning.

The current server is an Ubuntu x86_64 control host. It does not have DevBox/HNP/OHOS SDK, `/data/service/hnp`, or `ohos.toolchain.cmake`, so it cannot be used as the final OHOS build result. The CI run and the 2026-08-14 OpenDesk queue job above both passed on the OHOS Conan/SDK toolchain:

```bash
CI_PACKAGES="archives/s/sfml/2.6.1.1" zsh ci/conan/build_and_test.sh
```

The PR body claims OHOS build and test success only for the heads covered by those runs.
