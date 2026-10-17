# btag 1.4.1 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-09-10
- 目标平台：HarmonyOS PC aarch64（Conan profile：`ohos-aarch64`）
- 本机补充验证：macOS arm64、AppleClang 17、CMake 4.4.3、Conan 2.29.1
- 状态：`failed`；本机完整构建通过，PR #9096 的 HarmonyOS CI 已进入链接阶段，但构建 #43203 因系统只有版本化 `libtinfo.so.6`、原配方使用 `-ltinfo` 而失败；修复后等待 CI 重跑

## 源码与构建步骤

1. 使用上游官方 `release-1.4.1` 标签源码：
   `https://github.com/fernandotcl/btag/archive/refs/tags/release-1.4.1.tar.gz`。
2. 校验 SHA256：
   `a4a7b907f01ac6c65689fc7b12b0fa2a77645c488bcafab2049bb4965cd15e80`。
3. 应用四个由 `refresh-patch --auto` 从原始源码与工作源码生成的补丁。
4. Conan 使用 `BUILD_SHARED_LIBS=OFF`、`BOOST_LOCALE_SUPPORT=OFF`、`CUESHEET_SUPPORT=OFF`、`ENABLE_TESTS=ON` 配置 CMake，静态链接
   TagLib、libedit 和 zlib，构建并安装 `bin/btag`。
5. 构建阶段运行上游完整 CTest；`test_package` 再对已安装的命令执行功能检查。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libcue/2.3.0` 无法从制品仓解析 | libcue 是上游可选功能，但当前 OHOS Conan 仓无此配方 | 按上游开关设置 `CUESHEET_SUPPORT=OFF`；仅 cue sheet 读取功能不可用，核心音频标签编辑功能保留 |
| 2 | Boost.Locale 组件不可用 | OHOS 的 `boost/1.84.0` 只打包 filesystem、regex、program_options、iostreams；不含 locale 二进制库 | 增加默认开启的 `BOOST_LOCALE_SUPPORT` 能力开关以保持其他平台的上游行为；本配方显式关闭后使用标准 C++ 进程 locale，待 OHOS runner 用上游两项标题测试验证 |
| 3 | CMake 找到 Conan 配置却未填充上游旧式 `TAGLIB_*` / `LIBEDIT_*` 变量 | btag 1.4.1 的 CMake 仍依赖自带 Find 模块变量接口 | 明确使用 `MODULE` 模式，并由配方注入 Conan 包的 include 与静态库路径 |
| 4 | 动态 libedit 会把 Conan 缓存绝对路径带入产物 | `find_library` 优先选到了共享库 | 配方显式选择 `libedit.a`，并补齐终端库、zlib、m 等静态依赖链 |
| 5 | 本机无法执行 HarmonyOS G2 | 当前 macOS 环境没有 `/data/service/hnp` 下的 HarmonyOS clang/CMake 工具链 | 已运行规定门禁确认 G0/G1 通过；G2 在启动 CMake 时因 runner 缺少 HarmonyOS 工具链停止，不将其冒充平台通过 |
| 6 | Boost.Locale 默认 ON 路径最初无法编译 | `BOOST_LOCALE_SUPPORT` 由生成的 `config.h` 定义，但 `main.cpp` 和 `titles_base.cpp` 在包含该文件前就判断了宏，导致 Boost.Locale 头文件被跳过 | 将两处 `#include "config.h"` 移到 Boost.Locale include 守卫之前，并补做默认 ON 的完整编译与上游测试 |
| 7 | HarmonyOS CI 链接失败：`unable to find library -ltinfo` | OHOS 系统只有版本化的 `/usr/lib/libtinfo.so.6`，没有供 `-ltinfo` 查找的 `libtinfo.so` 链接器名称；下载的 OHOS `libedit.a` 确实仍引用 `tgetent` 等 terminfo 符号 | OHOS 配方改为显式链接系统 `/usr/lib/libtinfo.so.6`；Linux 和 macOS 的既有选择保持不变 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-CMakeLists.txt.patch` | CMake 最低版本升至 3.5；移除 `/usr/local`；增加默认开启的 Boost.Locale 能力开关；强制 TagLib/libedit 使用上游 Find 模块 |
| `0002-src-config.h.in.patch` | 将 Boost.Locale 能力开关导出给 C++ 源码 |
| `0003-src-main.cpp.patch` | 默认保留上游 Boost.Locale 路径，仅能力关闭时使用 `std::locale("")` |
| `0004-tests-titles_base.cpp.patch` | 默认保留上游 UTF-8 测试 locale，仅能力关闭时使用进程 locale |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Boost | 1.84.0 | filesystem、system 与头文件组件 |
| libedit | 20240808 | 交互式终端输入；静态链接 |
| TagLib | 1.13.1 | 音频标签读写；静态链接 |
| zlib | 1.3.1 | 由 TagLib 传递引入；静态链接 |
| libcue | — | 制品仓缺失的非核心可选依赖，已关闭对应上游功能 |

## 测试口径与结果

统一计数口径为“独立执行场景”：上游 CTest 2 项，安装后消费者检查 2 项，共 4 项。

| 上游测试 | 结果 |
|----------|------|
| `english_titles_test` | PASS |
| `spanish_titles_test` | PASS |

| 安装后检查 | 结果 |
|------------|------|
| `btag --help` 输出 Usage | PASS |
| `btag --dry-run <空目录>` 正常完成 | PASS |

本机默认 ON 路径（`BOOST_LOCALE_SUPPORT=ON`、`CUESHEET_SUPPORT=OFF`）已实际编译
`btag`、`english_titles_test` 和 `spanish_titles_test`，上游测试 2/2 通过。本机配方 OFF 路径
重新执行 `conan create`，上游 2/2、消费者 2/2 均通过；产物为单一 `bin/btag`，动态依赖
仅为 macOS 系统库。PR #9096 的 HarmonyOS 构建 #43203 中，全部源文件完成编译，两个上游
测试目标也完成链接，但 `btag` 主程序因 `-ltinfo` 无法解析而在运行 CTest 前失败。现已依据 CI
使用的 OHOS `libedit.a` 未解析符号和 `libedit.so` 的 `NEEDED libtinfo.so.6` 信息，改为显式链接
`/usr/lib/libtinfo.so.6`；该修改仍须由远程 HarmonyOS CI 重跑确认，不作为平台通过证据。

## 注意事项

- btag 的 cue sheet 元数据读取功能未包含；其余批量标签编辑、过滤、重命名和标题大小写功能保留。
- `commands.json` 的 `binary` 在远程 release 发布前保持 `false`。
- 只有具备 HarmonyOS SDK 的 runner 完成 G2/W3 与远程 CI 后，才能标记 `published`。
---

**编译结束**: 2026-09-09 04:01
**最终状态**: failed
