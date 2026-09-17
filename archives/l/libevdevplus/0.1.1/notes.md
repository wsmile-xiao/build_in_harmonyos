# libevdevplus 0.1.1 — 适配笔记

> 建档：2026-09-15 ｜ 任务：开源鸿蒙PC专项积分赛（contrib-13152）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libevdevplus |
| 版本 | 0.1.1（上游 tag `v0.1.1`） |
| 状态 | built（conan create 通过；未合并/未 release 上传，故不标 published） |
| 构建系统 | cmake（CMAKE_CXX_STANDARD 11） |
| 源码 | https://github.com/YukiWorkshop/libevdevPlus/archive/refs/tags/v0.1.1.tar.gz |
| sha256 | c941b6b45f784c1e6c6f316f59256fabd604ac392db405cf7fd99de2686aaab0（9448 字节，gzip magic `1f 8b` 已核） |
| 依赖 | 无第三方依赖（`conanfile.py` 无 `self.requires()`） |
| 平台 | OHOS aarch64（`ci/conan/profiles/ohos-aarch64`，clang 15.0.4，Release） |

## 二、上游调查

- 官方仓库：https://github.com/YukiWorkshop/libevdevPlus （MIT，Copyright (c) 2018 YukiWorkshop）
- 发行版侧线索：AUR `libevdevplus`（0.2.1-2，`provides: libevdevPlus.so`）、Debian 源码包
  `libevdevplus` 0.1.1-2.2 —— 与任务卡名/版本一致，无别名归一化需要。
- 上游内容（11 个文件）：`CMakeLists.txt`、`evdevPlus.{hpp,cpp}`、`InputEvent.hpp`、
  `CommonIncludes.hpp`、`Resource.cpp`、`test.cpp`、`evdevPlus.pc.in`、`LICENSE`、`README.md`、`.gitlab-ci.yml`
- 产物：`libevdevPlus.so*`(SHARED 目标 `evdevPlus`) 与 `libevdevPlus.a`(STATIC 目标 `evdevPlus_Static`，OUTPUT_NAME 同 `evdevPlus`)，
  头文件装到 `include/evdevPlus/`，另装 `lib/pkgconfig/evdevPlus.pc`
- 上游测试：**无自动化套件** —— `CMakeLists.txt` 全文无 `enable_testing()`/`add_test()`，
  也无 `make check`/ctest 目标；唯一测试性文件 `test.cpp` 是手工演示程序
  （`Usage: <event device>`，链接后 `while(true)` 读真实事件设备），上游不安装、不注册为测试。
  构建机 `/dev/input` 存在但无读权限（`Permission denied`），故其不可自动化运行 → **上游 N = 0**。

## 三、编译步骤

```sh
# 采信轮实际入口（容器层工具：清缓存 → conan-verify → 证据副本 → finish 前快照）
sh "$HOME/ws/tools/conan_verify_round.sh" libevdevplus 0.1.1 \
   --repo "$HOME/ws/worktrees/libevdevplus-0.1.1" --task-dir "$HOME/tmp/libevdevplus-0.1.1"

# 等价的手工复现（探索期实测命令）
conan create archives/l/libevdevplus/0.1.1 \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方本身不注入任何平台参数；`generate()` 只生成标准 CMakeToolchain。

## 四、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake.configure()` 直接失败：`CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake.` | 上游首行 `cmake_minimum_required(VERSION 3.0)`；本机/CI 的 CMake 4.1.2 已移除对 `<3.5` 的兼容（不是警告，是 hard error） | 配方 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`。**不能用 `tc.variables`/`tc.cache_variables`**：该策略检查发生在 CMakeLists 第一行，早于 `conan_toolchain.cmake` 加载（device-facts §17 coordgen 先例）。不改上游 CMakeLists、不加补丁 |
| 2 | `options.shared` 无法通过 `BUILD_SHARED_LIBS` 生效 | 上游 `add_library(evdevPlus SHARED ...)` 与 `add_library(evdevPlus_Static STATIC ...)` 是硬编码两个目标，两条 `install(TARGETS ...)` 都会装；上游不读 `BUILD_SHARED_LIBS` | 配方不设 `BUILD_SHARED_LIBS`（避免"设了但无效"的假开关），改在 `package()` 里按 `options.shared` 删除未选变体；默认静态（与仓库 CMake 模板一致）。实测 shared=False 的包内只有 `lib/libevdevPlus.a`。**与知识图谱 E288 的关系**：E288 收录同族问题、推荐打补丁把双目标改为单个未指定类型的 `add_library`（仓库先例 `libcork/0.9.0` 的 `0003-src-CMakeLists-shared-libs.patch`）；本包选零补丁的 packaging 级方案，理由：R8 不改上游逻辑流（上游是刻意同时交付两种产物）、目标状态与 E288 推荐方案一致、无机械门禁依赖 `BUILD_SHARED_LIBS`（已核 `ci/conan/build_and_test.sh` 与 `preflight.py`）。若需统一到 E288 形态，改动面仅为一个小补丁 + `tc.variables["BUILD_SHARED_LIBS"]`（已用最小夹具实测：单目标 + 仅 `LIBRARY DESTINATION` 在 static/shared 下 install 均正常） |
| 3 | 源码下载：GitHub 直连与本机 `ghfast.top` 镜像当时均不可达（`init-build` urllib `Errno 110`；`conan-verify` 的 E017 注入镜像亦超时） | 设备出网间歇不可用；`conan-verify` 会就地把 `https://github.com` 改写成 `https://ghfast.top/https://github.com`，而该镜像当时不可达 | 用 Conan 官方 `core.sources:download_cache` 预置**任务私有**离线种子（键 = sha256），并按 device-facts 口径"用完立即摘除 `global.conf` 修改"。种子 json 预写官方/ghfast/gh-proxy/ghproxy 四种 URL 形态，避免同一 sha256 在第二轮因请求 URL 不同被强制重下。实测 `Source ... retrieved from local download cache`；`global.conf` sha256 前后一致（`8a2f217d…`） |
| 4 | `make: jobserver mkfifo: <TMPDIR>/GMfifo*: Operation not permitted`（非致命，构建继续） | 本机任何可写目录都不支持 `mkfifo`（`$TMPDIR`、`$HOME/tmp` 均 EPERM，`/tmp` 只读），GNU make 无法建 jobserver fifo | 本包 6 个源文件、构建量极小，实测不受影响（一次通过）；已作为设备事实记入容器层反馈，未改配方 |

## 五、依赖版本

无第三方依赖（W0 空集成立：上游 `CMakeLists.txt` 无 `find_package()`、库目标无 `target_link_libraries`，
源码 include 全为标准库 + POSIX/Linux UAPI 头；运行期仅 libc/libstdc++，见
`$HOME/tmp/libevdevplus-0.1.1/w0-deps.txt` 的三条依据）。

## 六、验证结果

```text
# 1) 采信轮（conan-verify G0..G4 + L2/L4/L5）
见 reports/conan-verify-report.md 与 reports/conan-create.log

# 2) conan create（干净源码重建）+ test_package
[test_libevdevplus] checks=23 failures=0
[test_libevdevplus] OK
1/1 Test #1: test_libevdevplus ................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1

# 3) 包内产物（shared=False）
include/evdevPlus/CommonIncludes.hpp
include/evdevPlus/InputEvent.hpp
include/evdevPlus/evdevPlus.hpp
lib/libevdevPlus.a            (105182 字节)
lib/pkgconfig/evdevPlus.pc
```

## 七、上游测试与消费者测试分账

| 口径 | N | 结果 | 依据 |
|------|---|------|------|
| 上游自动化测试（清点） | **0** | N′=0（无套件可跑） | `CMakeLists.txt` 无 `enable_testing()`/`add_test()`、无 ctest/make check 目标；`test.cpp` 为需真实 `/dev/input` 的手工 demo，未注册、未安装，构建机无读权限 |
| test_package 消费者测试（本任务新增） | 23 项断言 | 23 PASS / 0 FAIL / 0 SKIP | `test_package/test_libevdevplus.cpp` 的 CHECK 宏输出 `checks=23 failures=0`；ctest 1/1 |

> 两类**不混算**：上游 0 项不因消费者测试通过而变成"上游已测"，消费者测试也不计入上游 N。

## 八、注意事项

- `test_package` 用自带 `CHECK` 宏而非 `assert()`：profile 为 Release，`NDEBUG` 会关掉 `assert`，
  用 `assert` 会让"断言数>0 但实际不判"变成假绿。
- 上游 `.pc.in` 的 `Version:` 写死 `0.1.0`（上游文件未随 0.1.1 更新），安装出的
  `evdevPlus.pc` 因此自报 0.1.0；本仓库不改上游该字段。
- 上游无 CMake config 导出，故只对齐 `pkg_config_name = "evdevPlus"`；CMake 侧走 Conan 默认
  （`find_package(libevdevplus)` + `libevdevplus::libevdevplus`）。
- 本包为**新包**（`archives/l/libevdevplus/` 在 `upstream/main` 不存在），建 PR 时按容器层口径
  会命中 PF9 确定性误报，需 `--no-preflight` 并在 PR 正文留痕。
