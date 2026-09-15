# miniupnpc 2.3.11 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-11
- 编译器: clang/clang++
- 状态: built
- 目标平台: HarmonyOS aarch64 (OHOS 6.0, clang 15, libc++)

## 版本与源码说明

- 任务命名 miniupnpc 2.3.11，任务给定 daemon 包 `miniupnpd-2.3.11.tar.gz`（`.../miniupnpd_2_3_11/miniupnpd-2.3.11.tar.gz`，sha256 `91994b127da735b2c97f19992e34420648c0e8c4ace8a4bcb0596e7685c48678`）仅含 daemon（miniupnpd.c/configure/iptables/nftables 后端），不含客户端库头文件与 `upnpDiscover` API，无法用于构建 miniupnpc。
- 上游无独立 `miniupnpc-2.3.11.tar.gz` 发布（验证 `miniupnpc_2_3_11` 下载 404；monorepo tag `miniupnpd_2_3_11` 中 `miniupnpc/VERSION` 仍为 `2.3.3`，`CMakeLists.txt` 中 `VERSION 2.3.3`）。
- 本配方源码取自 monorepo tag `miniupnpd_2_3_11` 的 codeload 归档（官方 GitHub，tag 即 2.3.11），`strip_root` 后顶层为仓库根，`layout` 取 `.` 并用 `cmake.configure(build_script_folder="miniupnpc")` 指向 CMake 工程（`get()` 解压到 `source_folder`，`src_folder="miniupnpc"` 会造成 `miniupnpc/miniupnpc` 双重嵌套导致找不到 `CMakeLists.txt`）。客户端代码与 2.3.3 发布包一致（`d52a0afa614ad6c088cc9ddff1ae7d29c8c595ac5fdd321170a05f41e634bd1a`），包版本 2.3.11 遵循任务命名。
- codeload URL 无文件扩展名，`source()` 须传 `filename` 供 Conan 解包（沿用 zfp 1.0.1 经验）。

## 编译步骤

CMake 流程（Conan 配方）：

```python
tc.variables["UPNPC_BUILD_STATIC"] = True   # 默认静态
tc.variables["UPNPC_BUILD_SHARED"] = False
tc.variables["UPNPC_BUILD_TESTS"] = True    # 启用上游 7 项 CTest
tc.variables["UPNPC_BUILD_SAMPLE"] = False
tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True  # OHOS/Linux
cmake.configure()
cmake.build()
ctest --output-on-failure   # 在 build_folder 运行
cmake.install()
```

## 上游测试审计

- 源码 `miniupnpc/CMakeLists.txt` 中 `UPNPC_BUILD_TESTS` 段注册 7 项 CTest：
  - `validateminixml`（`minixmlvalid` 二进制）
  - `validateminiwget`（`testminiwget.sh` + `minihttptestserver`，需 `TESTSERVER`/`TESTMINIWGET` 环境，脚本用 `mktemp -d`，依赖 HMBS 注入的 writable TMPDIR）
  - `validateupnpreplyparse`（`testupnpreplyparse.sh`，遍历 `testreplyparse/*.xml`）
  - `validateportlistingparse`
  - `validateigddescparse1`（`new_LiveBox_desc.xml`）
  - `validateigddescparse2`（`linksys_WAG200G_desc.xml`）
  - `validateaddr_is_reserved`
- 历史 2.3.3 配方将 `UPNPC_BUILD_TESTS=False` 关闭了上游测试；本配方改为 `True` 并在 `build()` 真实运行 `ctest`，结果写入 `build_folder/upstream_test_result.json`，`package()` 拷贝至 `package/res/` 供 `test_package` 回显，避免 conan cache 跳过 `build()` 时标记丢失（沿用 balboa/balloon 经验）。
- `testminiwget.sh` 在无 `ip`/`ifconfig` 时回退 `localhost`，在 HarmonyOS 真机可跑；若出现 HDFS `mktemp` 只读问题，依赖 HMBS 注入的 `TMPDIR/TMP/TEMP` 与 `HMBS_AUTOCONF_MKTEMP_FALLBACK`，不另行发明探测。

## Build route (direct-cc, no CMake)

- CMake project() repeatedly fails on the OHOS device with "The C compiler
  identification is unknown" for /data/service/hnp/bin/clang: first with the
  default Conan mapping (HarmonyOS system name, no Platform module), then
  again with the Linux-override variant (CMAKE_SYSTEM_NAME=Linux,
  PROCESSOR=aarch64, writable TMPDIR). Two red preflights with the same
  error fingerprint, so per the anti-repeat rule this round drops CMake
  try_compile probes entirely (critnib 1.1 / ddate 0.2.2 / clamav-libunrar
  1.4.5 precedent).
- build() compiles the 14 pure-C TUs from miniupnpc/src/ straight with the
  profile clang (-std=c99 -fPIC -Wall, upstream non-Windows defines,
  generated miniupnpcstrings.h with OS_STRING=Linux and project version
  2.3.3 as CMake configure_file would emit) and archives libminiupnpc.a
  (plus .so when shared=True). A trivial compile+link smoke test runs first
  so a genuinely broken toolchain shows real stderr.
- The 7 upstream CTest harnesses are compiled from the exact source lists in
  miniupnpc/CMakeLists.txt and all 7 cases run for real (minixmlvalid,
  testminiwget.sh with TESTSERVER/TESTMINIWGET, testupnpreplyparse.sh with
  TESTUPNPREPLYPARSE, testportlistingparse, testigddescparse x2 datasets,
  testaddr_is_reserved); fixtures are checked non-empty before running.
  Results are emitted as HMBS_UPSTREAM_TEST_RESULT with framework
  "direct-cc" and persisted to build/upstream_test_result.json, copied to
  package res/ for the test_package re-emit (cache-hit rounds).
- test_package compiles test_miniupnpc.c straight against the packaged
  headers + library (no CMakeToolchain, no find_package), so the CMake
  compiler-ID probe cannot fail that phase either.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务给定 daemon 包无客户端头文件 | miniupnpd 与 miniupnpc 为独立发布包，daemon 包不含 `miniupnpc.h`/`upnpDiscover` | 改用 monorepo tag 归档并取 `miniupnpc` 子目录，notes 与 PR 补充说明中如实声明 |
| 2 | codeload URL 无扩展名导致 Conan 解包失败 | `get()` 无法推断格式 | `source()` 传 `filename="miniupnp-miniupnpd_2_3_11.tar.gz"`（zfp 经验） |
| 3 | 历史配方关闭上游测试 | `UPNPC_BUILD_TESTS=False` | 改为 `True` 并在 `build()` 运行 `ctest`，输出 `HMBS_UPSTREAM_TEST_RESULT` |

## 源码修改

无补丁。`patches/` 未创建，`conandata.yml` 中 `patches: {}`。

## 依赖版本

无编译依赖与运行依赖，仅需标准 C 库与 socket API。

## 验证结果

待 HMBS 真机预检返回后填写。本地未运行 conan（按任务守则，真机验证由 HMBS 后台统一执行）。

- `conan create` 应含 `ctest --output-on-failure` 7/7 痕迹与 `Testing package` 痕迹。
- `test_package` 应运行 `test_miniupnpc` 二进制并输出 `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount 为真实计数）。
- 上游测试标记 `HMBS_UPSTREAM_TEST_RESULT` 由 `build()` 产生、`test_package` 从 `package/res/upstream_test_result.json` 回显。

## 交付物

- 静态库 `libminiupnpc.a`，头文件 `include/miniupnpc/*.h`，`pkg-config miniupnpc.pc`，CMake 包 `lib/cmake/miniupnpc`（`miniupnpc::miniupnpc`）。
- 样例二进制默认不构建（`UPNPC_BUILD_SAMPLE=OFF`）；需要时可开 `build_samples=True` 得到 `upnpc`/`upnp-listdevices`。

## 注意事项

- 本包为纯库，无 `bin/` 可执行产物，不创建软件级 `commands.json`（R38：库类型不需要）。
- `package_info()` 设置 `cmake_file_name=miniupnpc`、`cmake_target_name=miniupnpc::miniupnpc`、`pkg_config_name=miniupnpc`，静态时追加 `MINIUPNP_STATICLIB`。
- 平台判断使用 `self.settings.os in ("Linux", "OHOS")`（R32），编译器从 Toolchain 获取，不裸用 shell 环境变量（R33）。
