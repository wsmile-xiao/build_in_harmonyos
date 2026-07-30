# watcher 0.14.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: HarmonyOS (HongMeng Kernel 1.12.0, aarch64)
- 状态: published

## 源码信息
- 下载地址: `https://github.com/e-dant/watcher/archive/refs/tags/0.14.5.tar.gz`
- 实际下载: 配方和 manifest 保持官方 GitHub archive URL，由 CI 的 GitHub 镜像 fallback 接管网络受限场景
- SHA256: `190bbe5e19923083db2beb3aa68f4e99a563c8f685d8037b0536780b0116c4d3`
- 源码目录: `~/tmp/builds/watcher-0.14.5.work`
- 原始目录: `~/tmp/builds/watcher-0.14.5.orig`

## 编译步骤（详细）

### 1. init-build
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build watcher 0.14.5 \
  --url=https://github.com/e-dant/watcher/archive/refs/tags/0.14.5.tar.gz \
  --no-download
```
- 源码 URL 使用官方 GitHub archive 地址；CI 下载由镜像 fallback 处理
- init-build 因 SSL 证书下载步骤超时被中断，手动补充 `.build-context-watcher-0.14.5` 文件
- 档架骨架自动创建（manifest.yaml, notes.md, patches/, packaging/, reports/）

### 2. cmake 配置（R1 最少化参数, R20 DESTDIR 模式）
```bash
cmake -S $BUILD_SRC_DIR -B $BUILD_SRC_DIR/build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF
```
- 仅使用 `--prefix` 和必要选项（R1 铁律）
- cmake 识别平台为 HarmonyOS-HongMeng Kernel 1.12.0/Clang 15.0.4
- 自动找到 Threads::Threads (pthread)
- 编译目标: watcher-c-shared, watcher-c-static, wtr.watcher, tw, 头文件, pkg-config

### 3. make 编译
```bash
cd $BUILD_SRC_DIR/build && make -j2
```
- **首次编译失败**: 缺少 `FAN_REPORT_DIR_FID`, `FAN_REPORT_NAME`, `FAN_EVENT_INFO_TYPE_DFID_NAME` 常量
- 修复后重新 cmake + make 成功

### 4. DESTDIR 安装（R20）
```bash
make install DESTDIR=$TEST_PREFIX
```
- 安装 8 个产物到 staging 目录:
  - bin/wtr.watcher (76288 字节)
  - bin/tw (68032 字节)
  - include/wtr/watcher.hpp (2429 行)
  - include/wtr/watcher-c.h (74 行)
  - lib/libwatcher-c.so (88448 字节)
  - lib/libwatcher-c.a (92522 字节)
  - lib/pkgconfig/watcher.pc
  - lib/pkgconfig/watcher-c.pc

### 5. 上游测试口径
- watcher 0.14.5 上游源码包含测试，不应记为“上游测试用例为 0”。
- 上游 CMake 默认 `BUILD_TESTING=OFF`；在本适配/Conan 打包配置下关闭上游 FetchContent 测试，因此 `ctest -N` 报 `Total Tests: 0`，这只代表当前打包配置未注册上游 CTest。
- 若启用 `-DBUILD_TESTING=ON` 且提供 snitch 测试框架，上游默认非 sanitizer 配置会注册 3 个 CTest entry：`wtr.test_watcher`、`portable-destructive-rename` 与 `wtr.test_tool_test_all`。
- `wtr.test_watcher` 内含 6 个 snitch `TEST_CASE`：Concurrency、Simple、New Directories、Event Targets、Performance、Rapid Open and Close。
- `portable-destructive-rename` 是上游 CMake 注册的独立 CTest entry，无参数运行时打印帮助并返回 0；虽然也被 shell tool 测试作为辅助工具使用，统计上不能忽略该 CTest entry。
- `wtr.test_tool_test_all` 通过 `tool/test/all` 执行 8 个 shell 测试文件：access-events-are-not-reported、create-dir-accuracy、create-file-accuracy、rename-dir-accuracy、rename-dir-does-not-report-old-dir-in-new-events、rename-event-without-source、rename-events-are-associated-events、rename-file-accuracy。
- `make check`: No rule to make target 'check'。
- 当前 Conan 配方使用非空壳 `test_package` 做消费侧验证；上游 release 源码测试不能用该 `test_package` 结果替代。
- 2026-07-26 真机上游测试最终结果（0001-0005 后）：共 15 项，15 通过、0 失败，通过率 100.00%。`wtr.test_watcher` 的 6 个 snitch TEST_CASE 全通过（553 assertions）；`portable-destructive-rename` CTest 1/1 通过；8 个 shell tool 测试整组 8/8 通过。
- 历史失败项（0005 前）：`rename-events-are-associated-events`。整组运行日志显示期望的尾部 rename 事件及最终 destroy 事件缺失；timing probe 显示真机执行 100 次外部 `mv` 约需 3.55s，超过原始 `wtr.watcher -s 3` 运行窗口。
- 相关真机日志：最终 upstream-only `/storage/Users/currentUser/ohos-test-runs/codex-watcher-watcher-watcher-0.14.5-upstream-only-0005-20260726-113232-4337`；timing probe `/storage/Users/currentUser/ohos-test-runs/codex-watcher-watcher-watcher-0.14.5-rename-timing-probe-20260726-112715-1276`；0005 前 shell 整组确认 `/storage/Users/currentUser/ohos-test-runs/codex-watcher-watcher-shell-only-confirm-0.14.5-20260726-003900-62233`。

### 5.1 2026-07-26 真机上游测试复盘

当前进度：`0004-linux-drain-events-before-close.patch` 已在真机 upstream-only 中确认生效，但未解决 `rename-events-are-associated-events` 截尾；后续 timing probe 确认根因是该 shell 用例在 HarmonyOS 真机上执行 100 次外部 `mv` 约需 3.55s，超过原始 `wtr.watcher -s 3` 运行窗口。

正确做法：

- 真机结果只认 `ohos-test-runner.sh` 隔离环境；工具、PATH、shebang、TMPDIR、Conan home、编译器 wrapper 先做 runner 最小探针。
- job-local 工具写已确认可执行的绝对 shebang；不要假定 `/usr/bin/env`、`/bin/sh` 可用。
- 只读取最新 run-specific 日志；失败后只复跑受影响范围，不能反复跑完整流程刷结果。
- 上游测试按 CTest entry、框架 case、shell 子测试分层统计。watcher 0.14.5 非 sanitizer 口径为 15 项。
- 单个失败用例孤立通过不能覆盖整组失败。

当前真实未通过项（0005 前）：

- `rename-events-are-associated-events` 在 8 个 shell tool 测试整组运行中复现失败。
- 差异：expected 含 `path_name` 77-100 的 rename 关联事件和最终 `destroy 100`，actual 到 `path_name` 76 后缺尾部事件。
- 当前判断：这不是 watcher 事件关联逻辑失败，而是上游 shell 测试窗口过短；watcher 在尾部 `mv`/`rm` 发生前已按 3 秒窗口退出。

本地修复：

- `patches/0004-linux-drain-events-before-close.patch`：Linux adapter 收到 stop 请求后先处理同一批 epoll 文件系统事件，并非阻塞 drain 已排队事件再关闭。
- `patches/0005-tool-test-rename-timeout.patch`：将 `tool/test/rename-events-are-associated-events` 中 watcher 运行窗口从 3s 延长到 8s；断言仍覆盖 100 次 rename 关联事件和最终 destroy 事件，不减少验证项。

最终验证：干净 upstream-only 流程应用 0001-0005 后在真机复跑 15 项上游测试口径，返回码 0，`UPSTREAM_PASS_RATE=100.00%`。

### 6. verify-build（质量门禁）
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build watcher 0.14.5 \
  --install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX
```
- G1 二进制完整性: ✅3（3 个 ELF 二进制验证通过）
- G2 功能可用性: ⚠️1（--version 部分输出需注意）
- G3 可移植性: ⚠️4（RPATH/签名警告）
- G4 档案完整性: ✅（全部字段正确）
- 总体: PASS

### 7. package（R19 禁止手动打包）
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package watcher 0.14.5
```
- 打包产物: `watcher-0.14.5-ohos-aarch64.tar.gz` (486493 字节)
- 调试符号包: `watcher-0.14.5-ohos-aarch64-debug.tar.gz` (154667 字节)
- 包含 ELF 签名、Strip 符号、RPATH 设置、权限修复

### 8. 本地安装验证
```bash
cd $BUILD_SRC_DIR/build && make install
```
- 不带 DESTDIR，安装到 ~/usr/local（模拟用户部署）
- 验证结果: `wtr.watcher --version` → `0.14.5` ✅

### 9. finish
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish watcher 0.14.5 published
```
- 补丁生成: 1 个（0001-include-wtr-watcher.hpp.patch）
- 归档关闭: published
- G1-G4 全 PASS
- SUMMARY.md 已生成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报错: `FAN_REPORT_DIR_FID`, `FAN_REPORT_NAME`, `FAN_EVENT_INFO_TYPE_DFID_NAME` 未定义 | HarmonyOS sys/fanotify.h 缺少 Linux 5.9+ 引入的 fanotify 常量；LINUX_VERSION_CODE=330240 (5.13.0) >= 5.9.0 导致 fanotify 代码段被编译，但系统头文件不含这些常量 | 在 watcher.hpp 的 `#include <sys/fanotify.h>` 后添加 `#ifndef` 保护定义: FAN_REPORT_DIR_FID=0x400, FAN_REPORT_NAME=0x800, FAN_EVENT_INFO_TYPE_DFID_NAME=2 |
| 2 | GitHub 源码下载超时 (SSL + 网络不通) | HarmonyOS 环境无法直连 GitHub HTTPS（SSL CERT_VERIFY_FAILED + 连接超时） | `conandata.yml` 和 `manifest.yaml` 仍使用官方 GitHub archive URL；CI 由 GitHub 镜像 fallback 接管下载 |
| 3 | Conan 打包配置下 `ctest -N` 为 0 | 上游 CMake 默认 `BUILD_TESTING=OFF`，且启用上游测试需要 snitch（默认 FetchContent 从 GitHub 获取） | 记录上游真实测试基线：启用测试时默认 3 个 CTest 目标，包含 6 个 snitch TEST_CASE、1 个 portable CTest entry 与 8 个 shell 工具测试；Conan 配方另设 `test_package` 消费侧验证 |
| 4 | verify-build G4 报 manifest 缺少 build_system | manifest.yaml 使用 `build.system: cmake` 而非顶级 `build_system:` 字段 | 添加顶级 `build_system: cmake` 字段 |
| 5 | verify-build 查找 TEST_PREFIX/bin/ 为空 (DESTDIR 模式) | DESTDIR 模式产物在 TEST_PREFIX/DEFAULT_PREFIX/bin/ 而非 TEST_PREFIX/bin/ | 使用 `--install-prefix` 指定正确路径重跑 verify |
| 6 | init-build SSL 证书下载步骤超时 | check_env() 尝试从 curl.se 下载 CA 证书，网络不通 | 手动补充 .build-context 文件（所有其余步骤已完成） |
| 7 | G0 clean-verify 失败 (exit 127) | clean-verify 对 cmake 项目调用 `./configure`，cmake 项目无此文件 | 已手动验证构建自包含性（补丁 + cmake 命令可从头重建） |

## 源码修改

### 补丁: 0001-include-wtr-watcher.hpp.patch

**修改文件**: `include/wtr/watcher.hpp`（位于 fanotify 适配器代码段，第 1018 行附近）
**修改内容**: 在 `#include <sys/fanotify.h>` 之后添加 3 个 `#ifndef` 保护的常量定义

```cpp
/*  HarmonyOS (HongMeng Kernel) sys/fanotify.h may not define
    some newer fanotify constants introduced in Linux 5.9.
    We provide fallback definitions here. */
#ifndef FAN_REPORT_DIR_FID
#define FAN_REPORT_DIR_FID 0x400
#endif
#ifndef FAN_REPORT_NAME
#define FAN_REPORT_NAME 0x800
#endif
#ifndef FAN_EVENT_INFO_TYPE_DFID_NAME
#define FAN_EVENT_INFO_TYPE_DFID_NAME 2
#endif
```

**补丁设计说明**:
- 使用 `#ifndef` 保护，确保当 HarmonyOS 内核升级包含这些常量时自动适配，不会重复定义
- 仅修改头文件，不修改运行时逻辑（watcher 运行时自动 fallback 到 inotify）
- 补丁类型: platform_only（仅针对 HarmonyOS 平台）

**运行时影响**:
- 补丁使 fanotify 代码段可编译，但运行时 fanotify_init 调用仍会失败（普通用户无 CAP_SYS_ADMIN）
- watcher 自动 fallback 到 inotify 适配器，功能完全正常（见 test-report.md T4）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| cmake | 4.1.2 | 构建系统 |
| clang/clang++ | 15.0.4 | 编译器 |
| Threads::Threads | pthread | 多线程支持 |
| libc++_shared.so | 系统自带 | C++ 标准库 |
| libc.so (musl) | 系统自带 | C 标准库 |

## 手动功能验证结果摘要

（完整测试报告见 `reports/test-report.md`，12/12 全通过）

```
$ wtr.watcher --version
0.14.5

$ wtr.watcher --help
（完整帮助信息输出正常）

$ wtr.watcher /tmp/watcher-test -s
（正确检测 create/modify/rename/destroy 事件）

$ pkg-config --modversion watcher
0.14.5

$ pkg-config --modversion watcher-c
0.14.5
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| watcher-0.14.5-ohos-aarch64.tar.gz | 486493 字节 | 预编译包（ELF 已签名, 已 Strip） |
| watcher-0.14.5-ohos-aarch64-debug.tar.gz | 154667 字节 | 调试符号包 |
| 0001-include-wtr-watcher.hpp.patch | 1078 字节 | HarmonyOS fanotify 常量补丁 |
| wtr.watcher | 76288 字节 | CLI 二进制（本地安装） |
| tw | 68032 字节 | Tiny watcher CLI 二进制（本地安装） |
| libwatcher-c.so | 88448 字节 | C 共享库 |
| libwatcher-c.a | 92522 字节 | C 静态库 |
| watcher.hpp | 2429 行 | C++ single-header 库头文件 |
| watcher-c.h | 74 行 | watcher-c C API 头文件 |
| watcher.pc | — | watcher pkg-config 文件 |
| watcher-c.pc | — | watcher-c pkg-config 文件 |

## 2026-07-25 Conan/Windows 本地前置验证

本次按“一库一分支并行适配工作流”在独立 worktree `H:\OpenHarmonyOsCompetition\worktrees\watcher`、分支 `feat/watcher-0.14.5` 中补充 Conan 2 配方与非空壳 `test_package`，只修改 `archives/w/watcher/0.14.5/`。

新增文件/变更：
- `conandata.yml`：记录官方源码 URL 与 SHA256，并纳入 `0001` / `0002` 补丁。
- `conanfile.py`：使用 `CMakeToolchain` / `cmake_layout`，关闭上游 FetchContent 测试，按 `BUILD_SHARED_LIBS` 构建库。
- `patches/0002-CMakeLists.txt.patch`：上游 CMake 原本同时生成 shared/static 的 `watcher-c`，MSVC 下二者 import library 都叫 `watcher-c.lib`，Ninja 报 `multiple rules generate watcher-c.lib`；补丁按 `BUILD_SHARED_LIBS` 二选一生成。
- `test_package/`：编译并运行 C++ 消费者，启动 `wtr::watch`、创建文件、确认 watcher 生命周期事件并关闭；同时执行打包出的 `wtr.watcher --version`。

验证命令（MSVC/Ninja）：
```bat
conan create H:\OpenHarmonyOsCompetition\worktrees\watcher\archives\w\watcher\0.14.5 ^
  --profile:host H:\OpenHarmonyOsCompetition\.tools\profiles\win-msvc ^
  --profile:build H:\OpenHarmonyOsCompetition\.tools\profiles\win-msvc ^
  --build=missing
```

结果：
- `watcher-c-static`、`wtr.watcher.exe`、`tw.exe` 构建成功。
- 安装产物包含 `include/wtr/watcher.hpp`、`include/wtr/watcher-c.h`、`lib/watcher-c.lib`、`bin/wtr.watcher.exe`、`bin/tw.exe`、两个 pkg-config 文件。
- `test_package` CTest：`1/1` 通过，`test_watcher` 用时约 `0.54s`。
- `wtr.watcher.exe --version` 输出 `0.14.5`。

Windows 本机 MinGW 预检未作为有效验证使用：本机 `E:\mingw64\bin\g++.exe` 为 GCC 8.1.0 / win32 thread model，最小 C++17 探针和 Conan 构建都会在 `std::filesystem`、`std::future`、`std::thread` 支持处失败，属于本机工具链能力不足，不是 watcher 配方本身的失败。

## 2026-07-26 补丁生成规则说明

R3 要求优先通过 `refresh-patch --auto` 生成补丁。本归档中 `0001` 来自 legacy finish/auto 流程；`0002`-`0005` 是为后续 Conan/MSVC 构建冲突和 OHOS 真机上游测试问题补充的定向修复，当前 worktree 的自动刷新流程未能覆盖这些后续差异，故保留为人工整理的 unified diff。申请对 `0002`-`0005` 作 R3 例外处理；补丁均为单一职责，已在 `manifest.yaml` 的 `patch_classification` 中标注类型和 guard。

## 注意事项

1. **运行时行为**: watcher 在 HarmonyOS 上运行时优先尝试 fanotify（需 root/CAP_SYS_ADMIN），失败后自动 fallback 到 inotify 适配器。经实测验证，inotify 适配器功能完整
2. **BUILD_TESTING**: 上游测试并非 0 个；默认关闭。启用正式测试需要手动提供 snitch 框架并设置 `WTR_WATCHER_USE_SYSTEM_SNITCH=1`，再用 `-DBUILD_TESTING=ON` 编译。默认非 sanitizer 配置下 CTest 目标为 3 个。
3. **fanotify 常量**: 补丁使用 `#ifndef` 保护，未来 HarmonyOS 内核升级包含这些常量时可自动适配
4. **网络限制**: GitHub 直接 HTTPS 访问受限时，保持官方 GitHub archive URL 不变，由 CI 镜像 fallback 或手动预置 tarball 处理下载，不把 CDN 临时地址写入元数据
5. **G0 干净构建**: clean-verify 脚本对 cmake 项目调用 `./configure`（不适用），手动验证确认补丁 + cmake 命令可从原始源码从头重建成功

---
**编译结束**: 2026-06-01 23:41
**最终状态**: published
