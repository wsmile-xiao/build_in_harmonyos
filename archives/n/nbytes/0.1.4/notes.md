# nbytes 0.1.4 适配笔记

## 编译环境

- 构建系统：cmake（上游要求 CMake >= 3.28，C++20）
- 上游仓库：https://github.com/nodejs/nbytes
- 源码归档：https://github.com/nodejs/nbytes/archive/refs/tags/v0.1.4.tar.gz
- 校验和：`67f4b8363f12abb64c07a0cecf2bf2dce7ab47b5f8b9fd2efdb852ea254c2d40`
  （与 Homebrew 公式 `formula/n/nbytes.rb` 记录的官方归档哈希一致；真机 `conan create` 会再次校验）
- 编译日期：2026-09-16
- 编译器：clang/clang++
- 状态：built（待真机预检通过后由 HMBS 统一提交）

## 编译步骤

配方流程（`archives/n/nbytes/0.1.4/conanfile.py`）：

1. `get()` 拉取官方 `v0.1.4` 归档并校验 sha256。
2. `CMakeToolchain` 设置 `BUILD_SHARED_LIBS`（默认静态）、
   `NBYTES_ENABLE_TESTING=ON`、`BUILD_TESTING=ON`；OHOS 下写入
   `cmake_system_name=OHOS`、`cmake_system_processor=aarch64`。
3. `cmake.configure()` → `cmake.build()` 构建 `libnbytes`。
4. `build()` 内运行 `ctest --output-on-failure` 执行上游测试，
   解析真实 ctest 汇总行并双通道输出 `HMBS_UPSTREAM_TEST_RESULT`；
   失败则抛异常使构建失败。证据同时落盘
   `build_folder/hmbs_upstream.json`，并随包安装到 `res/`，
   供 `test_package` 在缓存命中轮次重发。
5. `cmake.install()` 安装库、头文件、`nbytes.pc`；Conan 暴露
   `nbytes::nbytes`（`cmake_file_name=nbytes`）与 pkg-config 名 `nbytes`。

## 上游测试审计

- 上游测试位置：`tests/basic.cpp`（经 `tests/CMakeLists.txt` 注册，
  `add_test(basic_test basic)` + `gtest_discover_tests`）。
- 用例清单（源码审计，`TEST` 宏计数 = 3）：
  1. `basic.swap_bytes16`
  2. `basic.swap_bytes32`
  3. `basic.swap_bytes64`
- 测试框架：gtest（经 CMake `FetchContent` 在构建时拉取
  `google/googletest@03597a0`，构建机需访问 github；与上游默认行为一致，
  未改动上游测试开关语义）。
- 通过标准：`ctest` 汇总 `passed == discovered == 3` 且 `failed == 0`；
  数字全部来自 ctest 输出解析，退出码 0 不单独作为证据。

## 消费者测试

`test_package/test.cpp`（C++20）共 8 组 18 个 `CHECK` 断言，每项打印
`CHECK-OK:` 行，`test_package/conanfile.py` 计数并输出
`HMBS_TEST_PACKAGE_RESULT`（要求 18/18，否则失败）：

| 组 | 内容 | 断言数 |
|----|------|--------|
| 字节交换 | SwapBytes16/32/64 真值比对 | 6 |
| 失败路径 | 非对齐长度返回 false | 2 |
| Hex | `HexEncode` 缓冲与 string 重载 | 3 |
| Base64 | `Base64Decode("SGVsbG8=") == "Hello"` | 2 |
| 搜索 | `SearchString` 命中/未命中 + `RoundUp` | 3 |
| ASCII/版本 | `ForceAscii` 去高位 + 版本宏 0.1.4 | 2 |

上游未覆盖的 Base64/Hex/Search/ForceAscii 在消费者测试中补齐，
未修改任何上游测试文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | profile 默认 `compiler.cppstd=17`，上游要求 C++20 | `ci/conan/profiles/ohos-aarch64` 全局为 17 | 上游 `CMakeLists.txt` 显式 `set(CMAKE_CXX_STANDARD 20)`，工程级设置优先；`test_package` 另设 `CXX_STANDARD 20`，配方不强制覆盖全局 profile |
| 2 | 上游测试依赖 googletest 下载 | `FetchContent` 在配置期拉取 github 归档 | 保持上游行为（`FIND_PACKAGE_ARGS` 优先系统 GTest），真机/CI 均可访问外网下载源；不 vendor、不改测试开关 |

## 依赖版本

无运行时依赖。构建时测试依赖：`google/googletest@03597a0`
（由上游 CMake `FetchContent` 拉取，非 Conan 依赖）。

## 验证结果

```bash
conan create archives/n/nbytes/0.1.4 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=1
```

- 本轮为未提交工作树，按任务要求不本地执行 conan、不 commit、不 push；
  上述命令与测试标记均由 HMBS 后台在 HarmonyOS aarch64 真机统一验证。
- 证伪预案（真机轮执行）：确认 `LastTest.log` 非空；必要时将
  `tests/basic` 替换为 `exit 1` 桩，确认 harness 能抓到失败；
  区分通过与静默跳过（gtest `[SKIPPED]` 计跳过，不计通过）。

## 注意事项

- 本库为纯字节工具库，无 OS 相关代码路径，无需平台补丁（`patches: {}`）。
- 非系统同名库，默认静态（`shared=False`），保留共享选项。
- Windows 工作区存在 `archives/l/libXext` 与 `archives/l/libxext`
  大小写目录碰撞导致的 `git status` 脏显示，与本任务无关，未改动。

## 2026-09-16 test_package fix

- Symptom: preflight test_package compile failed with 5 errors: NBYTES_VERSION_* undeclared, bare CHECK in Vector ctor, GetHighestValueByte ambiguous for char.
- Root: version enum lives in namespace nbytes; upstream header line 255 uses bare CHECK (never instantiated by lib itself, only by SearchString<char> consumers); GetHighestValueByte only overloads uint8_t/uint16_t.
- Fix: patches/fix-consumer-header.patch (CHECK->NBYTES_ASSERT_TRUE + generic GetHighestValueByte template); test.cpp macro renamed to NBYTES_TEST_CHECK and versions qualified as nbytes::NBYTES_VERSION_*.
- Verify: git apply --check passes on upstream tarball copy; py_compile ok; awaiting HMBS preflight.

## 2026-09-16 patch-apply fix (preflight compile failed)

- Symptom: preflight `build()` failed in `apply_conandata_patches`:
  `fix-consumer-header.patch: hunk no.2 doesn't match source file at line 410,
  expected b'}', actual b'static_cast<uint8_t>(character >> 8));'`.
  Patch hunk header `@@ -412,6 +412,19 @@` is byte-identical to `git diff`
  against the pristine v0.1.4 tarball, so the unified-diff path is fragile
  under conan's patch tool on the real machine.
- Root: same header fixes are required (bare CHECK undefined for any consumer
  Vector instantiation; GetHighestValueByte ambiguous for char), but the
  .patch/hunk mechanism is the failure point, not the fix content.
- Fix: deleted `patches/fix-consumer-header.patch`, dropped `patches:` from
  `conandata.yml`, removed `export_sources()`/`apply_conandata_patches`, and
  applied both edits via exact-anchor `replace_in_file` in `source()` after
  `get()` (anchors verified 1 occurrence each in pristine tarball).
- Verify: `py_compile` OK; anchors simulated against fresh tarball OK;
  awaiting HMBS preflight (no local conan run, uncommitted).
