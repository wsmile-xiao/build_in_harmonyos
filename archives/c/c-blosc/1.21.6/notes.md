# c-blosc 1.21.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-27
- 编译器: clang
- 状态: published

## 编译步骤
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DBUILD_BENCHMARKS=OFF ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 不支持 cmake_minimum_required(VERSION 2.8.12) | 版本兼容性 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | bench.c 编译失败 — CLOCK_MONOTONIC 不可用 | 平台不支持 clock_gettime | 设置 -DBUILD_BENCHMARKS=OFF |
| 3 | CMake 报告 "System is unknown" | 平台未识别 | 使用 generic 实现，功能完整 |

## 源码修改
无补丁。

## 依赖版本
无外部依赖（内置 LZ4 1.9.4, zlib 1.3.1, ZSTD 1.5.6）

## 验证结果
- 1632 测试全部通过 (100%)
- pkg-config --modversion blosc = 1.21.6

## 交付物
- libblosc.so / libblosc.a
- blosc.h, blosc-export.h

## 2026-07-25 Conan/Windows 本地前置验证

本次按“一库一分支并行适配工作流”在独立 worktree `H:\OpenHarmonyOsCompetition\worktrees\c-blosc`、分支 `feat/c-blosc-1.21.6` 中补充 Conan 2 配方与非空壳 `test_package`，只修改 `archives/c/c-blosc/1.21.6/`。

新增文件/变更：
- `conandata.yml`：记录官方源码 URL 与 SHA256 `9fcd60301aae28f97f1301b735f966cc19e7c49b6b4321b839b4579a0c156f38`。
- `conanfile.py`：使用 `CMakeToolchain` / `cmake_layout`，默认静态库，使用内置 LZ4/zlib/ZSTD，关闭 tests/fuzzers/benchmarks。
- `test_package/`：编译 C 消费者，调用 `blosc_compress()` / `blosc_decompress()`，断言解压长度和原始数据一致。

验证命令（MSVC/Ninja）：
```bat
conan create H:\OpenHarmonyOsCompetition\worktrees\c-blosc\archives\c\c-blosc\1.21.6 ^
  --profile:host H:\OpenHarmonyOsCompetition\.tools\profiles\win-msvc ^
  --profile:build H:\OpenHarmonyOsCompetition\.tools\profiles\win-msvc ^
  --build=missing
```

结果：
- `blosc_static` 构建成功，安装静态库 `lib/libblosc.lib`。
- 包内容包含 `include/blosc.h`、`include/blosc-export.h`、`lib/libblosc.lib`、`lib/pkgconfig/blosc.pc`、`licenses/LICENSE.txt`。
- `test_package` CTest：`1/1` 通过，`test_c_blosc` 用时约 `0.03s`。
- Windows 静态库包设置 `CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP=ON`，避免上游 `InstallRequiredSystemLibraries` 把 MSVC runtime DLL 打入 Conan 包。

## 2026-07-26 OHOS 真机单包验证

本次按真机多用户 runner 规范，在隔离 job `/storage/Users/currentUser/ohos-users/codex/c-blosc-1.21.6-20260726` 中运行，仅验证单包 `archives/c/c-blosc/1.21.6`。运行日志目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-c-blosc-conan-build-c-blosc-1.21.6-cachevar-20260726-124938-41995
```

验证入口：

```sh
CI_PACKAGES=archives/c/c-blosc/1.21.6 zsh ci/conan/build_and_test.sh archives/c/c-blosc/1.21.6
```

结果：
- Build Summary：`Total: 1`、`Success: 1`、`Failed: 0`。
- L0：`pass`，质量门禁通过。
- L1：`pass`，`test_package` 被 `conan create` 执行，且负向破坏测试确认测试确实依赖 `c-blosc`。
- L2：`skip`，该包无 `bin/` 目录，是纯库包。
- L4：`pass`，无 patches。
- L5：`pass`，`lib/` 有实际产物。
- 产物包含 `include/blosc.h`、`include/blosc-export.h`、`lib/libblosc.a`、`lib/pkgconfig/blosc.pc`、`licenses/LICENSE.txt`。
- `test_package` 执行 `./test_c_blosc`，输出 `c-blosc roundtrip: OK (145 bytes compressed)`。

本次 OHOS 验证前发现 `CMAKE_POLICY_VERSION_MINIMUM` 用 `tc.variables` 注入时不会进入 CMake 4.x 的早期 policy 检查，因此改为 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`。

## 2026-07-26 OHOS 真机上游 release 测试

按长期记忆中的“上游测试用例”口径，本次不使用 Conan recipe 中 `BUILD_TESTS=OFF` 的空 CTest 结果，而是在 v1.21.6 release 源码树中启用并运行上游测试入口：

- `tests/test_*.c`，含 CSV 参数化测试项。
- `compat/*.cdata` 兼容性测试；因上游默认 `DEACTIVATE_SNAPPY=ON`，snappy 兼容数据不注册。
- `tests/fuzz/fuzz_*.c` standalone fuzz runner。

正式运行使用真机 runner heavy 模式与隔离 job：

```text
runner job: /storage/Users/currentUser/ohos-users/codex/c-blosc-1.21.6-20260726
run dir:    /storage/Users/currentUser/ohos-test-runs/codex-c-blosc-upstream-tests-v1.21.6-r7-20260726-142946-13266
```

运行方式：

```sh
zsh /storage/Users/currentUser/ohos-users/codex/c-blosc-1.21.6-20260726/work/run-upstream-tests.sh
```

上游测试配置：

```sh
cmake -S "$SRC" -B "$BUILD" -G Ninja \
  -DCMAKE_C_COMPILER="$JOB/tools/clang" \
  -DCMAKE_CXX_COMPILER="$JOB/tools/clang++" \
  -DCMAKE_ASM_COMPILER="$JOB/tools/clang" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DBUILD_TESTS=ON \
  -DBUILD_FUZZERS=ON \
  -DBUILD_BENCHMARKS=OFF \
  -DBUILD_STATIC=ON \
  -DBUILD_SHARED=ON \
  -DDEACTIVATE_SYMBOLS_CHECK=ON
```

事前统计：
- release 源码有效测试入口合计 `1632` 项。
- `ctest -N` 执行前确认 `Total Tests: 1632`。

事后结果：
- `UPSTREAM_TEST_TOTAL=1632`
- `UPSTREAM_TEST_PASSED=1632`
- `UPSTREAM_TEST_FAILED=0`
- `UPSTREAM_PASS_RATE=100.00%`
- `CTEST_EXIT_CODE=0`

调试记录：
- 初始预统计只包含 `tests/test_*.c` 与符号检查，漏掉 `compat/*.cdata` 和 fuzz runner，已纠正为上游默认口径。
- 早期运行因测试二进制运行目录找不到 `blosc/libblosc_testing.so` 全失败，已通过在测试子目录提供 job-local `blosc/` 路径修正。
- 人为打开 `DEACTIVATE_SYMBOLS_CHECK=OFF` 会额外注册 `blosc_test_shared_symbols` / `blosc_test_static_symbols`，其中静态/共享符号检查在 OHOS 下会报告内置 zstd/lz4 等额外导出；该检查不是上游默认测试口径，最终按上游默认 `DEACTIVATE_SYMBOLS_CHECK=ON` 执行。

## 注意事项
- 硬件加速 shuffle (AVX2/SSE2) 不可用，使用 generic 实现
- 内置压缩算法: blosclz, lz4/lz4hc, zlib, zstd
