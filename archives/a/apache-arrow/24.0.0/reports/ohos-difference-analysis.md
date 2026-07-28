# apache-arrow 24.0.0 HarmonyOS 差异分析

## 已进入正式 PR 的适配点

### CMake processor 识别

- 现象: OHOS/CMake 环境中 Arrow `SetupCxxFlags.cmake` 可能看到 `unknown` processor。
- 影响: Arrow 配置阶段无法按 aarch64 正确设置编译参数。
- 处理: `patches/0001-setupcxxflags-unknown-processor.patch`。

### shared library SONAME

- 现象: OHOS 走 CMake unknown platform 路径时, Arrow 的 `VERSION`/`SOVERSION` 属性不稳定地产生 ELF SONAME。
- 影响: 下游 `NEEDED` 可能记录构建树路径, 运行时加载失败。
- 处理: `patches/0002-buildutils-ohos-soname.patch`。

### 受限网络下的 xsimd/mimalloc 风险

- 现象: Arrow 默认可能通过 bundled/vendored 方式从 GitHub 拉取 xsimd 或 mimalloc。
- 影响: CI/真机网络不稳定时出现非代码失败。
- 处理: 设置 `ARROW_SIMD_LEVEL=NONE`、`ARROW_RUNTIME_SIMD_LEVEL=NONE`、`ARROW_MIMALLOC=OFF`。

### CMakeDeps target 契约

- 现象: `cmake_target_name` 若随 shared/static 变化, 消费者或 test_package 容易硬编码错误 target。
- 影响: `shared=False` 时只生成 static target, 下游链接 shared target 会 configure 失败。
- 处理: 固定 `cmake_target_name` 为 `Arrow::arrow`, 同时保留 `Arrow::arrow_shared` / `Arrow::arrow_static` alias。

### 文件 IO 边界行为

- 现象 1: `ReadableFile::WillNeed({{10, 0}})` 在 OHOS 上经 `posix_fadvise` 返回 `EINVAL`。
- 处理 1: `patches/0003-ohos-file-io-edge-cases.patch` 在 Arrow `ReadRange` 语义下跳过零长度 range, 保留 range 校验和非零长度 `posix_fadvise` 路径。
- 现象 2: `LocalFileSystem::OpenAppendStream(dir + "/")` 可能接受目录尾斜杠路径。
- 处理 2: 同一 patch 拒绝尾斜杠 output/append path, 保持 Arrow FileSystem “输出流目标必须是文件”的契约。

### IANA zoneinfo 发现路径

- 现象: Arrow vendored date 库只探测 `/usr/share/zoneinfo`、`/usr/share/zoneinfo/uclibc` 等固定路径, 当前 HarmonyOS 真机缺少这些目录。
- 影响: `arrow-compute-scalar-cast-test` 中 timezone cast 用例报 `Cannot locate or parse timezone ... discover_tz_dir failed to find zoneinfo`; 下游若使用 timezone 相关 temporal cast, 也需要可配置的 IANA tzdb 入口。
- 处理: `patches/0004-vendored-date-tzdir.patch` 在固定系统路径前优先检查通用环境变量 `TZDIR`, 指向有效目录时直接使用。
- 验证: 真机上将 `TZDIR` 指向 Python `tzdata/zoneinfo` 后, timezone lookup 错误收敛; `arrow-compute-scalar-cast-test` 由 103/106 提升为 105/106, 剩余 1 个 Broken_Hill 历史 DST offset 与 tzdb 数据版本/规则差异相关。

## 扩展测试阶段确认的环境差异

### GTest 临时目录

- 现象: GTest 默认使用 `/tmp/gtest_captured_stream.*`, 当前真机 `/tmp` 不可写或不可访问。
- 处理方式: 扩展测试阶段临时调整 GTest, 使其优先使用 `TEST_TMPDIR` / `TMPDIR`。
- 验证: `arrow-array-test` 从 `/tmp` 捕获失败收敛为 1038 passed, 1 skipped, exit code 0。
- 当前状态: 属于上游测试框架迁移差异, 未作为正式库 patch 提交。

### 官方测试数据

- 现象: release 源码包不包含完整 `testing/data`、`parquet-testing` 数据。
- 处理方式: 补齐 `ARROW_TEST_DATA` 和 `PARQUET_TEST_DATA` 指向的官方测试数据。
- 验证: Parquet 11/11 通过, IPC 相关资源缺失项收敛。

### IANA zoneinfo

- 现象: Arrow vendored date 库找不到可解析的 IANA zoneinfo 目录。
- 处理方式: 新增通用 `TZDIR` 支持后, 使用 Python `tzdata` 的 zoneinfo 目录验证。
- 当前状态: “找不到 timezone”类错误已收敛; 剩余为历史 timezone/DST offset 期望差异。

### OHOS LLVM 15 libc++ C++20 ranges 支持

- 现象: 上游测试代码使用 `std::ranges::equal` 时编译失败。
- 处理方式: 扩展测试阶段临时替换为等价 `std::equal`。
- 当前状态: 属于上游测试兼容差异, 未进入正式库 patch。

### HarmonyOS loader 相对 NEEDED 路径

- 现象: 上游测试二进制启动时报 `Error loading shared library ../../release/libarrow_gtest.so`。
- 进一步现象: 直接把测试动态库复制到多个 `release` 层级虽然可让 loader 找到库, 但会在同一进程中重复加载多份 `libarrow_gtest.so` / `libarrow_gmock.so`, 导致部分 GTest 目标在 test body passed 后于 `RUN_ALL_TESTS()` 返回前收到 `SIGTRAP` / 退出码 133。
- 处理方式: 对上游测试工具链使用重新链接方案, 将 `arrow-io-file-test`、`arrow-filesystem-test`、`libarrow_testing.so`、`libarrow_gmock*.so` 的 `NEEDED` 统一生成为 basename, 并只使用单一 `LD_LIBRARY_PATH` 目录。
- 验证: `arrow-io-file-test` 50/50 passed, `arrow-filesystem-test` 198/198 passed; compute-on 专项测试中同一方案继续用于 `libarrow_compute.so` 和 12 个 compute target。
- 当前状态: 作为测试运行环境差异记录; 正式 recipe 中已通过 SONAME patch 降低包产物风险。后续扩展 CTest 应沿用“单一测试库目录 + basename NEEDED”, 避免多目录复制。

### make jobserver FIFO

- 现象: 并行构建出现 `make: jobserver mkfifo: ... Operation not permitted`。
- 处理方式: 扩展测试使用单线程或受控并发。
- 当前状态: 属于 HarmonyOS 用户目录文件系统对 FIFO 的限制, 作为测试/构建环境差异记录。

### Boost.Context 架构识别

- 现象: 上游测试构建中 Boost.Context 可能误选 x86_64 汇编。
- 触发条件: 新建 `ARROW_COMPUTE=ON` 测试树时, `CMAKE_SYSTEM_PROCESSOR` 为 `unknown`, Boost.Context 选择 `make_x86_64_sysv_elf_gas.S`, aarch64 clang 编译 x86_64 汇编失败。
- 处理方式: 显式指定 `CMAKE_SYSTEM_PROCESSOR=aarch64`、`BOOST_CONTEXT_ARCHITECTURE=arm64`、`BOOST_CONTEXT_ABI=aapcs`。
- 验证: `build-upstream-tests-compute-temporal-v2` 成功生成 `arrow-compute-scalar-temporal-test` 和后续 compute target。
- 当前状态: 作为测试依赖工具链差异记录。

### compute temporal 历史 timezone/DST 规则

- 现象: `arrow-compute-scalar-temporal-test` 在正确 `TZDIR` 下仍有 7 个历史 DST/offset 相关失败。
- 失败项: `ScalarTemporalTest.TestZoned2`、`TestAssumeTimezoneAmbiguous`、`TestAssumeTimezoneNonexistent`、`TestCeilFloorRoundTemporalBrussels`、`ScalarTemporalTestMultipleSinceGreaterUnit.CeilZoned`、`FloorZoned`、`RoundZoned`。
- 验证: 全量 54 tests 中 46 passed, 1 skipped, 7 failed; 过滤已定位差异后 47 tests 中 46 passed, 1 skipped, exit code 0。
- 轻量对照: `codex-apache-arrow-upstream-temporal-dst-probe-v1-20260726-192802-38911` 确认 Python `tzdata 2026.3` 的 zoneinfo 是当前真机上最稳定的 TZDIR; 系统 `/etc/zoneinfo` 或 unset `TZDIR` 会将已通过主体用例扩大为 17 failed。
- 当前状态: 属于历史 timezone/DST 规则差异和测试期望差异, 暂不扩大为库行为 patch; 正式方案保留通用 `TZDIR` 注入能力, 由测试或下游显式提供 IANA tzdb。

### bundled zlib 静态库命名

- 现象: bundled zlib 产物为 `libzlibstatic.a`, 链接规则查找 `libz.a`。
- 处理方式: 扩展测试中临时复制为 `libz.a`。
- 当前状态: 有明确 patch/recipe 修复空间, 但当前正式 recipe 未启用 Parquet/zlib, 暂不纳入基础包改动。

### Boost.UUID `-latomic` 误判

- 现象: Parquet 扩展构建中 Boost.UUID CMake 检测加入 `-latomic`, OHOS 工具链找不到该库。
- 处理方式: 扩展测试中移除链接脚本里的 `-latomic` 后通过。
- 当前状态: 记录为 Boost/Arrow 扩展构建适配点, 暂不纳入当前基础 recipe。

## 暂缓继续修复的未通过项

- `arrow-array-test`: 经 GTest `TEST_TMPDIR` / `TMPDIR` 临时 patch 后完整目标 1038 passed, 1 skipped; 作为测试框架迁移差异记录。
- `arrow-buffer-test`: 仅 `TypedTestBuffer/0.ResizeOOM`、`TypedTestBuffer/1.ResizeOOM` 触发 SIGSEGV; 过滤 OOM 后 45/45 passed。单用例复测 `TypedTestBuffer/0.ResizeOOM` 仍为 exit code 139 / `Signal 11`。
- `arrow-misc-test`: 4 个 OOM/Reallocate 期望失败; 过滤后 180/180 passed。单用例复测 `Default/TestMemoryPool/0.OOM` 为期望 `OutOfMemory` 但返回 OK。
- `arrow-stl-test`: `allocator.TestOOM` 失败; 过滤后 44/44 passed。单用例复测为期望 `std::bad_alloc` 但未抛异常。
- `arrow-compute-scalar-cast-test`: 新增 `TZDIR` 支持后 105/106 passed, 剩余 Broken_Hill 历史 timezone offset 期望差异; 非 timezone 用例 103/103 passed。
- `arrow-compute-scalar-temporal-test`: 全量 46 passed, 1 skipped, 7 failed; 过滤历史 DST/offset 差异后 46 passed, 1 skipped。
- temporal DST 对照探针: Python `tzdata 2026.3` 最稳定, `/etc/zoneinfo` 和 unset `TZDIR` 不作为默认回退。
- `arrow-io-file-test`: P1 完整目标在重新链接测试辅助库后 50/50 通过。
- `arrow-filesystem-test`: P1 完整目标在重新链接测试辅助库后 198/198 通过。

## 申报边界

本分析用于路径 B 证明材料。当前 PR 将可稳定、窄范围、低风险的库行为修复纳入正式补丁; 对测试环境、运行时差异和扩展模块重依赖问题保留为报告和 draft, 不将其写成完整上游测试通过。
