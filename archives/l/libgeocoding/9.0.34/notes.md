# libgeocoding 9.0.34 适配笔记

## 编译环境

- 构建系统：**cmake（上游真实构建入口 `cpp/CMakeLists.txt`）**，生成器 **Ninja**
- 编译器：`/data/service/hnp/bin/clang` / `clang++`（OHOS aarch64，Clang 15.0.4，libc++，C++17）
- 平台：HarmonyOS PC aarch64（本机原生，非交叉编译 → 上游测试可真实执行）
- 依赖：abseil-cpp/20260107.1、protobuf/33.6、icu4c/78、googletest/1.12.1（test_requires）
- 编译日期：2026-09-21
- 状态：**built**（上游测试 329/329 通过；`conan create` exit 0；conan-verify PASS；W3 本地 CI PASS）

## 构建步骤（真实命令）

```bash
conan create archives/l/libgeocoding/9.0.34 \
  -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64
```

配方内部：`apply_conandata_patches()` → `cmake.configure(build_script_folder=<source>/cpp)`
→ `cmake.build()` → 运行上游测试（`libphonenumber_test`、`tools/generate_geocoding_data_test`、
示例 `geocoding_test_program`）→ `cmake.install()`（使用上游 install 规则）。

## 问题与解决（首个错误 → 根因 → 修复 → 重新验证）

### 1. 上游 `-Wall -Werror` × abseil 弃用 API（编译失败）

首跑报错（`cpp/src/phonenumbers/geocoding/phonenumber_offline_geocoder.cc`）：

```
phonenumber_offline_geocoder.cc:80:19: error: 'MutexLock' is deprecated:
  Use the constructor that takes a reference instead [-Werror,-Wdeprecated-declarations]
  absl::MutexLock l(&mu_);
absl/synchronization/mutex.h:620: [[deprecated("Use the constructor that takes a reference instead")]]
2 errors generated.
```

- **根因**：abseil 20260107.1 弃用取指针的 `MutexLock` 构造；上游 `cpp/CMakeLists.txt:420`
  `if (NOT WIN32) add_definitions ("-Wall -Werror")` 把警告升级为硬错误。全树仅 2 处命中，
  且都在**目标库自身源码**内。
- **修复**：改用非弃用构造 `absl::MutexLock l(mu_);`（保留上游 `-Werror` 语义，不禁用告警）。
- **重新验证**：同命令重跑，编译通过（95/95 目标）。

### 2. 静态依赖闭包缺失（链接失败）

```
ld.lld: error: undefined symbol: icudt78_dat                （libicuuc.a 需要 libicudata.a）
ld.lld: error: undefined symbol: absl::...log_internal::LogMessageFatal::LogMessageFatal(...)
                                                             （libprotobuf.a 需要 Abseil log/status 族）
ld.lld: error: undefined symbol: utf8_range_IsValid          （libprotobuf.a 需要 utf8_range/utf8_validity）
```

- **根因**：上游只 `find_library` 出 `icuuc/icui18n/protobuf` + 三个 Abseil 目标
  （`cpp/CMakeLists.txt:430 LIBRARY_DEPS`）；静态归档不携带自身依赖，`libprotobuf.a`
  的其余依赖与 `libicudata.a`、`zlib` 无人链接。
- **修复**：`patches/0001` 在 `LIBRARY_DEPS` 与 `TEST_LIBS` 末尾追加
  `${LIBPHONENUMBER_CONAN_LIBS}`；配方按真实依赖图（`cpp_info`）生成该闭包并包在
  `-Wl,--start-group/--end-group` 内（含 `ut8_range`/`utf8_validity` 绝对路径）。
- **重新验证**：链接通过，`libgeocoding.a`/`libphonenumber.a`/`libphonenumber_test`/
  `geocoding_test_program`/`tools/generate_geocoding_data_test` 全部产出。

### 3. `find_package(absl)` 落空 → FetchContent 拉 GitHub（CI 无外网必炸）

conan 流程下 configure 日志出现：

```
CMake Warning (dev) ... FetchContent_Populate(abseil-cpp) is deprecated ...
CMake Deprecation Warning at .../_deps/abseil-cpp-src/CMakeLists.txt:22
CMake Error at CMakeLists.txt:39 (message): Can't find Google Protocol Buffers compiler (protoc)
```

- **根因**：Conan 的 `CMakeToolchain` 只把依赖目录写入 `CMAKE_LIBRARY_PATH` /
  `CMAKE_INCLUDE_PATH`（`find_path/find_library` 因而命中），**不写 `CMAKE_PREFIX_PATH`**，
  于是上游 `find_package(absl)` 找不到 `abslConfig.cmake` → 走 `FetchContent` 从 GitHub 拉
  abseil 源码。本机有外网会静默成功，CI 无外网则必然失败。
- **同时暴露**：`protoc` 由 protobuf 依赖包 `bin/` 提供，不在系统 PATH。
- **修复**：配方显式设置 `absl_DIR=<abseil-cpp 包>/lib/cmake/absl` 与
  `CMAKE_PROGRAM_PATH=<protobuf 包>/bin`。
- **重新验证**：configure 通过，日志中不再出现 FetchContent 拉取。

### 4. Makefile 生成器删除随包发布的 `test_metadata.cc`（编译失败）

```
[ 67%] Generating .../cpp/src/phonenumbers/test_metadata.cc, .../test_metadata.h
skip metadata generation from .../resources/PhoneNumberMetadataForTesting.xml to ... test_metadata
clang-15: error: no such file or directory: '.../cpp/src/phonenumbers/test_metadata.cc'
```

- **根因（可复现证明）**：上游在 `REGENERATE_METADATA=OFF` 分支把「生成元数据」写成了
  **空 `echo` 自定义命令**（声明了 OUTPUT 却不产出文件）。CMake 的 **Makefile 生成器**会为
  这些自定义命令写 `.DELETE_ON_ERROR`（`CMakeFiles/generate-test-metadata.dir/build.make:5`），
  规则一执行，随包发布的 `cpp/src/phonenumbers/test_metadata.cc` 就被删除；而该文件是
  `phonenumber_testing` 的必需源文件。最小复现：单独执行
  `cmake --build <mkbuild> --target generate-test-metadata` 后该文件即消失。
- **修复**：配方改用 **Ninja 生成器**（`CMakeToolchain(self, generator="Ninja")`，
  Ninja 不删除未更新的目标）。不修改上游生成逻辑、不跳过任何测试。
- **重新验证**：`cmake --build` 95/95 成功，`test_metadata.cc` 保留，上游测试全绿。

### 5. 逐条用例解析漏 1 条（证据完整性）

- **现象**：包内逐条清单 326 条，而 gtest 汇总为 `[ PASSED ] 327 tests.`。
- **根因**：`RegExpAdapterTest.TestFindAndConsume` 的结果行前有测试自身输出
  （`previous input: Present input: [       OK ] ...`），非行首匹配被漏掉。
- **修复**：结果标记解析改用 `re.search` 并要求带耗时括号（避免把失败汇总清单重复计入）。
- **重新验证**：清单 329 条 = `libphonenumber_test` 327 + `generate_geocoding_data_test` 2，
  与上游测试源静态 `TEST` 宏计数完全一致（327+2），无漏测。

## 上游测试实测

| 套件 | 命令 | 执行 | 通过 | 失败 | 跳过 |
|---|---|---|---|---|---|
| libphonenumber_test | `./libphonenumber_test` | 327 | 327 | 0 | 0 |
| generate_geocoding_data_test | `./tools/generate_geocoding_data_test` | 2 | 2 | 0 | 0 |
| **合计** |  | **329** | **329** | **0** | **0** |

- 示例程序 `./geocoding_test_program` exit 0，输出 `Mountain View, CA`。
- 逐条用例名称/状态见 `reports/upstream-tests.md`（329 行，全 PASSED）。

## test_package（L1 消费者测试）

`test_package/test.cpp` 只使用已安装包的公开头与 conan 提供的编译链接参数（不做缺失库兜底）：
6 项 CHECK 全通过，其中 **CHECK 6 为 HarmonyOS 专有用例**
（`ohos-concurrent-geocoding-embedded-data`：8 线程并发调用离线 geocoder，覆盖本适配修复的
`absl::Mutex` 加锁路径，并验证 geocoding 数据完全来自编译期嵌入、无外部数据文件/locale 依赖）。

## 注意事项

- 目标库与同源 `libphonenumber` 由同一份 `cpp/` 配置一次产出，故本包导出
  `cpp_info.libs = ["geocoding", "phonenumber"]`；`libgeocoding.a` 实测引用 7 个
  `i18n::phonenumbers::*` 未定义符号，二者必须同时链接。
- `protobuf/33.6` 的 `cpp_info` 未导出 `utf8_range/utf8_validity`，配方在 `package_info()`
  中补齐（避免下游链接 `libprotobuf.a` 失败）。
- 未提交、未推送，等待评审确认后再走 commit/PR 流程。
## 对话记录（适配过程，含真实命令与退出码）

### 对话 #1 — 路线选择：走上游 CMake 还是 direct-cc？

- 先做最小 CMake 探针（`cmake -G Ninja -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang`）：
  `-- The C compiler identification is Clang 15.0.4` → `configure_exit=0`，
  历史「CMake 4.4.3 无法识别 HarmonyOS 编译器」的墙在当前环境（CMake 4.1.2）**未复现**。
- 结论：走**上游真实 CMake 构建入口**（`cpp/CMakeLists.txt`），可一并获得上游 install 规则、
  `tests` 目标（`libphonenumber_test` + `generate_geocoding_data_test`）与示例程序。

### 对话 #2 — 首次真实构建：abseil 弃用 API 触发 -Werror

```
cpp/src/phonenumbers/geocoding/phonenumber_offline_geocoder.cc:80:19: error:
  'MutexLock' is deprecated [-Werror,-Wdeprecated-declarations]
2 errors generated.
```
修复：`absl::MutexLock l(&mu_)` → `absl::MutexLock l(mu_)`（2 处，均在目标库源码内）。
重验：同一构建命令重跑，编译通过。

### 对话 #3 — 链接失败：静态闭包缺口

```
ld.lld: error: undefined symbol: icudt78_dat
ld.lld: error: undefined symbol: absl::...log_internal::LogMessageFatal::...
ld.lld: error: undefined symbol: utf8_range_IsValid
```
修复：上游 `LIBRARY_DEPS`/`TEST_LIBS` 追加 `${LIBPHONENUMBER_CONAN_LIBS}`（配方按 cpp_info 生成闭包，
含 `--start-group`）。重验：全部目标链接成功（95/95）。

### 对话 #4 — Conan 侧：find_package(absl) 落空触发 FetchContent + protoc 不在 PATH

```
CMake Warning (dev) ... FetchContent_Populate(abseil-cpp) is deprecated ...
CMake Error at CMakeLists.txt:39 (message): Can't find Google Protocol Buffers compiler (protoc)
```
修复：`absl_DIR=<abseil 包>/lib/cmake/absl`、`CMAKE_PROGRAM_PATH=<protobuf 包>/bin`。
重验：configure 通过，无 FetchContent 拉取。

### 对话 #5 — Makefile 生成器删除随包发布的 test_metadata.cc

```
[ 67%] Generating .../cpp/src/phonenumbers/test_metadata.cc, .../test_metadata.h
clang-15: error: no such file or directory: '.../cpp/src/phonenumbers/test_metadata.cc'
```
最小复现：`cmake --build <mkbuild> --target generate-test-metadata` 后该文件消失；
`CMakeFiles/generate-test-metadata.dir/build.make:5:.DELETE_ON_ERROR`。
修复：`CMakeToolchain(self, generator="Ninja")`。重验：95/95 构建成功，上游 327+2 用例全绿。

### 对话 #6 — 逐条用例清单少 1 条

现象：清单 326 条 vs `[ PASSED ] 327 tests.`。根因：`RegExpAdapterTest.TestFindAndConsume`
结果行前有测试输出（`previous input: Present input: [ OK ] ...`）。修复：改 `re.search`。
重验：329 条 = 静态宏计数 327+2，`conan create` exit 0。

### 对话 #7 — W3 本地 CI：JC full 模式误命中 main 既有文件

首次 `finish` 退出码 1：
```
[FAIL] JC5: 3 个 archives 下未登记的隐藏文件:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
       archives/k/kics/2.1.20/.staging-verified
```
- 这 3 个文件是 **origin/main 已提交、且未登记 JC5 白名单**的历史产物（`git ls-files` 命中），
  与本包无关；无提交时 junk_check 会退化为 full（整仓扫描）模式。
- 按 CI 权威口径（`junk_check.sh`：pr.diff 是 PR 文件清单的唯一权威来源，CI 侧 `git apply pr.diff` 不产生 commit）
  生成本包 pr.diff（10 个文件，全部 `archives/l/libgeocoding/`），以 `JUNK_PR_DIFF=<pr.diff>` 复跑。
- 重验：`finish` **exit 0**，W3 `JC_RESULT=pass`、`L0_RESULT=pass`、`L1_RESULT=pass`（含 L1e
  破坏性反向验证：移走 lib/ 与 include/ 后 test_package 确实失败 → 测试真依赖被测包）、
  `L2_RESULT=skip`（纯库无 bin/）、`L4_RESULT=warn`（CI 正则误报，见下）、`L5_RESULT=pass`，
  Pass rate 100%（1/1），`.ci-result.json` 写入 `exit_code=0` + 完整性哈希。

### 已知非阻塞项

- `L4_RESULT=warn: dangerous functions in patches`：CI 规则 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'`
  命中的是补丁注释里的英文单词 "tar**gets**"（`gets\b` 后缀匹配），**非真实危险函数**（补丁仅改
  `MutexLock` 构造与 CMake 变量追加）。属于 CI 规则误报，建议上报而不是改注释绕开。
- `finalize-archive` 的 `packaging/` 与 `packaging/*-ohos-aarch64.tar.gz` 缺失项：`.gitignore`
  明确忽略 `archives/**/packaging/*.tar.gz`，且已合并的同源先例 `libphonenumber/8.13.51` 亦无该目录，
  属预期。
- **CI 预下载改写未回滚（已手工还原）**：`ci/conan/build_and_test.sh:1217` 的预下载把
  `conandata.yml` 的 URL 改写为 `['https://gh-proxy.com/' + url, url]`，靠 `trap _restore_conandata EXIT`
  还原（:1188）。本次 W3 子调用结束后文件仍停留在镜像版（`conandata.yml.orig` 与现文件的 diff
  可见 `gh-proxy.com` 前缀），`conan_verify` 的 `_recover_ghfast_bak` 守卫只识别 `ghfast.top`、
  识别不了 `gh-proxy.com`，故也未能兜底。**已手工还原为官方 URL 并复核**：
  `curl -L -r 0-99 <官方 URL>` → `HTTP=200 SIZE=13041844`（sha256 与 conandata 一致）。
  这条属 SKILL/CI 缺陷，建议上报（还原守卫需同时识别 gh-proxy.com，或在 W3 结束后强制校验
  conandata 与 pr.diff 中记录的版本一致）。
---

**编译结束**: 2026-09-21 01:45
**最终状态**: built
