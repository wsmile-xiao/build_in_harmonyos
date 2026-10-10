# islamic-menus 1.0.5 适配笔记

## 编译环境
- 构建系统: custom（XDG 资源包；Conan 配方生成本地化目录文件）
- 编译日期: 2026-10-04
- 编译器: HarmonyOS Clang 15.0.4（用于 test_package 消费者）
- 状态: built

## 软件内容与移植方式

`islamic-menus` 是 XDG 桌面数据包，不包含 C/C++ 库或可执行程序。配方保留上游菜单分类、目录描述、SVG 图标和 gettext 翻译；将泛用与 GNOME 菜单片段放在 `etc/xdg/menus/`，生成的目录描述与图标分别放在 `share/desktop-directories/` 和 `share/icons/hicolor/scalable/categories/`。Conan runenv 暴露 `XDG_CONFIG_DIRS` 与 `XDG_DATA_DIRS`。

## 编译步骤

1. Conan 从 `conandata.yml` 中固定的 Debian 官方地址获取上游源码，并校验 SHA-256。
2. 通过 `intltool-merge -d` 将两个 `.directory.in` 模板与 gettext 翻译目录合并为 `.directory` 文件。
3. 将菜单片段、生成的目录描述、SVG 图标和许可证安装到包目录；通过 Conan runenv 暴露 `XDG_CONFIG_DIRS` 与 `XDG_DATA_DIRS`。
4. `test_package` 编译 C 语言资源消费者，并在 HarmonyOS 设备上读取菜单、翻译目录和 SVG 图标。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者 CMake 配置提示 `System is unknown to cmake` | 当前 CMake 未内置 HarmonyOS 平台模块 | 此消费者不依赖 Linux 专有分支；Clang 配置、编译、链接及设备运行均通过，无需改包配方 |
| 2 | 并行 make 提示 jobserver FIFO 不可用 | HMDFS 环境限制 GNU make jobserver FIFO | 该提示未阻止消费者构建或运行；无需为纯资源包添加平台补丁 |
| 3 | PR #14595 的消费者 CMake 配置在编译器探测阶段失败，make 返回 `resource temporarily unavailable` | Worker 在启动 CMake `try_compile` 子进程时失败；上游包已构建并打包成功，错误发生在消费者真正构建之前 | 在 test_package 工具链中设置 `CMAKE_C_COMPILER_FORCED=ON`，跳过 HarmonyOS 上不可靠的编译器 ABI/可用性探测；后续 `cmake.build()` 仍会编译实际消费者程序 |
| 4 | PR #14595 / Worker #73654 的 `test_package` 在 CMake 配置成功后，`make -j20` 报 `resource temporarily unavailable` | CI Worker 的进程资源限制无法承受 Conan 自动设置的 20 路并行；上游包本身已构建和打包成功 | 在消费者的 CMake build 调用中指定 `cmake.build(build_tool_args=["-j1"])`，采用仓库中其他 HarmonyOS 包的串行构建方式 |

## 上游测试清点

按 R51 检查上游 1.0.5 源码：没有测试目录或测试运行器，Makefile 没有 `check` 目标，也没有 CTest/pytest 注册项，因此上游测试为 0 项。源码归档 SHA-256：`b09ba6f1c769d6d16e2459cc34238646f2c9ae144aa700354325c4ec3e58f51d`。

## 发现与知识

- 用 `intltool-merge -d` 生成保留 gettext 翻译的 `.directory` 文件。
- 菜单片段安装到 `etc/xdg/menus/`，并通过 Conan runenv 暴露配置与数据目录。
- 真机测试由 `/system/bin/sh` 启动平台脚本，再由 HNP Bash 执行 AArch64 ELF 消费者。

## 源码修改

无上游源码修改，无补丁。

## 依赖版本

- `intltool/0.51.0`：构建依赖，用于生成含 gettext 翻译的 `.directory` 文件；依赖预检通过。

## 验证

### 验证结果

```text
conan create archives/i/islamic-menus/1.0.5 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build="islamic-menus/*"

PASS: 消费者资源检查 16/16
PASS: HarmonyOS 设备及 XDG 运行检查 6/6
PASS: 合计 22/22
PASS: conan-verify（G1-G4、L2、L4、L5）
PASS: W3 本地 CI
```

PR #14595 / Worker #71225 的回归构建在 test_package 的 CMake 编译器探测阶段报错，
未进入消费者编译或运行。上一轮在 test_package 工具链中设置 `CMAKE_C_COMPILER_FORCED=ON` 后，
后续 Worker #73654 已确认 CMake 配置通过；该轮消费者构建失败原因是 `make -j20` 触发进程资源限制（见问题 4）。

上一轮 `CMAKE_C_COMPILER_FORCED=ON` 调整后的 HarmonyOS aarch64 真机 Conan 回归：`conan create` exit 0；
CMake 配置与消费者编译完成，C 资源检查 16/16 通过，HarmonyOS/XDG shell 检查通过。

本次串行构建修复后的 HarmonyOS 6.0 aarch64 真机 Conan 回归：`conan create` exit 0；
消费者 CMake 实际命令为 `cmake --build ... -- -j20 -j1`，编译、链接和运行均通过；
Islamic/Quran 菜单资源检查 16/16 通过，HarmonyOS 专项检查通过：AArch64 架构、HongMeng 内核、
系统 shell/HNP Bash 可用性及 Conan runenv 的 XDG 配置与数据目录。CMake 的 HarmonyOS 平台未知提示、
`/proc/meminfo` 解析提示及测试结束后的 `getcwd` 提示均未影响构建和测试结果。
本次真机 Conan 日志保存在设备临时目录 `tmp/islamic-menus-ci-20261008-8683981/conan-create.log`。
Worker #73654 的新 CI 结果待 PR 状态确认。

## 注意事项

- 该包提供 XDG 菜单数据，不包含桌面程序或 GUI；设备验证覆盖资源读取和消费者运行，不代表系统桌面已显示这些菜单。
- `finish` 的全仓知识完整性检查报告了既有条目 E219、E253、E305 的字段缺失；本包知识检查通过，且未修改这些无关条目。通用 G0 clean-verify 未找到传统本地 tarball；该步骤对 Conan 源码获取流程非阻塞，Conan 构建与消费者验证均通过。
