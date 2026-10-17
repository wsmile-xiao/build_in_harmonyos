# tinyalsa 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 make / cmake / meson 三入口，manifest `build.system` 选定 cmake）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（HNP `/data/service/hnp/bin/clang`，OHOS SDK 26.0.0.18 sysroot）
- 状态: built

## 编译步骤

1. 源码：`conan` `get()` 上游官方 tag 归档
   `https://github.com/tinyalsa/tinyalsa/archive/refs/tags/v2.0.0.tar.gz`
   （sha256 `573ae0b2…47994ef1`，与 conan-center-index 同条目逐字一致），`strip_root=True`。
2. 配置（配方 `generate()` → CMakeToolchain + CMakeDeps）：
   `cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=generators/conan_toolchain.cmake
   -DCMAKE_INSTALL_PREFIX=<package> -DCMAKE_BUILD_TYPE=Release <src>`
   并额外在**命令行**加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（见问题 1），
   `-DBUILD_SHARED_LIBS=ON`、`-DTINYALSA_BUILD_UTILS=OFF`、`-DTINYALSA_BUILD_EXAMPLES=OFF`。
3. 构建：`cmake --build <build> -- -j4`（7 个 C 源 → `libtinyalsa.so.2`）。
4. 上游测试（层 1）：配方在 `<build>/upstream-tests/` 生成 CMake 子工程（写入
   build 目录，不改上游源码），编译上游 `tests/src/*.cc` 6 个文件 + 自带
   `gtest_main.cpp`，链 build 目录里的 `libtinyalsa.so`，经 `ctest --test-dir` 运行。
5. 安装：`cmake.install()` → `<package>/{lib,include/tinyalsa,licenses}`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 3.1)` 报 `Compatibility with CMake < 3.5 has been removed` | 设备/CI 的 CMake 4.1.2 移除了 <3.5 兼容；该判断在 CMakeLists 解析阶段、**早于** toolchain 文件加载，写进 `tc.variables`/`cache_variables` 的同名变量来不及生效（实测首轮即因此失败） | 配方 `cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])`（CMake 官方逃生口），上游源码零改动；已有知识条目 E321 |
| 2 | `NotADirectoryError: .../b/build/Release` | 上游根目录有 Bazel `BUILD` 文件，本设备文件系统大小写不敏感 ⇒ `cmake_layout` 默认 `build/` 目录撞上已有文件 | `cmake_layout(self, src_folder=".", build_folder="cmake-build")`（已有知识条目 E470；**不能删上游 BUILD**） |
| 3 | `find_package(gtest)` 找不到配置文件 | 配方把 gtest 写在名为 `test_requirements()` 的**方法**里——Conan 2.x 只调用 `requirements()` / `build_requirements()` 钩子，该方法从未被执行，依赖没进图 | 改写进 `build_requirements()` 并调用 conan 注入的 `self.test_requires("gtest/1.17.0")` |
| 4 | 无 gtest_main 目标（`gtest_LIBS_RELEASE=gtest`） | conan gtest 1.17.0 的 `cpp_info.libs` 只声明 `gtest`，不导出 `gtest_main` | 测试子工程自带 4 行 `gtest_main.cpp`（等价上游 `BUILD` 里链接的 `@googletest//:gtest_main`） |
| 5 | 上游 68 条 gtest 用例里 66 条在设备上失败 | 设备 `/dev/snd` 目录与 `controlC0/C1/C2` 全部 `EACCES`（tinyalsa 报 `cannot open card(N) device (N): Permission denied`），OHOS 无可用 ALSA 设备节点 | 配方先跑 `os.open` 探针把 errno 逐字打进日志；按环境限制把 66 条设备依赖用例记 **SKIP（不计 PASS）**，只跑 2 条与设备无关的用例并由 ctest 把关；同时保留一次全量试跑作归因证据（`ignore_errors`，不参与构建判据） |
| 6 | 上游没有 CMake/meson 测试入口 | `tests/` 只接了 Bazel（`BUILD` 的 `cc_test` + `@googletest`），`CMakeLists.txt`/`meson.build`/`Makefile` 均无 check/test 目标 | 配方生成测试子工程补 CMake 入口（见「编译步骤 4」），未改任何上游测试文件 |
| 7 | 共享库缺 `DT_SONAME`（W3 L5a 实测 `[fail] soname_gate_failed`），且只产出 `libtinyalsa.so`、没有 `.so.2`/`.so.2.0.0` | `uname -s`=`HarmonyOS`，conan 把 `os=OHOS` 映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`，设备 cmake 4.1.2 无 `Platform/HarmonyOS.cmake` ⇒ 平台模块不加载 ⇒ `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 未定义 | `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`（全仓 370 个配方同解；实测修复后产出 `libtinyalsa.so.2.0.0` + `DT_SONAME=libtinyalsa.so.2`）；相关知识草稿 `DRAFT-cmake-harmonyos-platform-soname-flag` |

## 源码修改

无（本包 `patches: []`：全部适配都在配方层，上游 7 个 C 源、6 个测试文件与构建脚本零改动）。

## 依赖版本

- 运行：**零**（内核 UAPI 头 `<sound/asound.h>` 由 OHOS SDK sysroot 提供，`libdl` 随平台）
- 构建：设备 HNP cmake 4.1.2 / make 4.4.1 / clang 15.0.4
- 测试（仅 build 面）：`gtest/1.17.0`（`self.test_requires`，visible=False，不进消费面）

## 验证结果

```bash
# 采信轮（清缓存 → conan create → 证据副本）：见 reports/conan-create.log
conan create archives/t/tinyalsa/2.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#   上游测试：total=68 ran=2 passed=2 skipped=66 failed_unexpected=0（ctest 1/1 Passed）
#   test_package：assertions_run=10 failures=0（ctest 1/1 Passed）
# 四分项（本版本二进制口径）：TOTAL 68 = PASS 2 + FAIL 0 + SKIP 66 + NOT_RUN 0
# 声明 N（PR 正文，候选数法最大值）：70 = 上游当前 HEAD(9fab97ca) 框架注册数；
#   与本版本 68 的差额 2 = HEAD 在 v2.0.0 之后新增 3 项、删除回环用例 1 项，
#   归因见 reports/pr-body.md 与 reports/upstream-tests.md。
```

## 发现与知识

- ✅ 上游 tests/ 只接 Bazel 的包可在 build() 内生成 CMake 子工程补层 1 测试入口（ctest），上游文件零改动。
- ✅ conan gtest 1.17.0 只导出 `gtest::gtest`、`cpp_info.libs` 只有 `gtest`，gtest_main 需配方自带；钩子必须是 `build_requirements()` + `self.test_requires()`。
- ✅ OHOS `/dev/snd` 与 `controlC*` 全 EACCES ⇒ 音频设备依赖用例按环境限制记 SKIP，探针读数进日志留证，不写 PASS。
- ✅ Bazel `BUILD` 文件 × 大小写不敏感 FS × cmake_layout 默认 `build/`（E470）、CMake 4.x `<3.5` 拒绝须命令行 `-DCMAKE_POLICY_VERSION_MINIMUM`（E321）两条既有知识本次实测复证。

## 注意事项

- 本包按**纯库**交付（`TINYALSA_BUILD_UTILS=OFF`）：`tinyplay/tinymix/tinycap/tinypcminfo` 是面向音频设备的人工演示工具，安装 `bin/` 会触发 R38/L0k 的 `commands.json` 要求与 PF9 包级路径要求；与 conan-center `with_utils=False` 默认一致。需要工具链时可用 `-DTINYALSA_BUILD_UTILS=ON` 重建。
- 设备有可用 ALSA 节点的环境下，配方探针会自动放开 `--gtest_filter=*` 跑全量 68 条。
