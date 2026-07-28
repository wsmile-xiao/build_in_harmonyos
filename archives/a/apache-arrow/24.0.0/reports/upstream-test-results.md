# apache-arrow 24.0.0 上游测试结果记录

## 结果摘要

| 测试范围 | 结果 | 说明 |
| --- | --- | --- |
| 核心模块初始范围 | 45/52 passed | 当前 recipe 启用模块对应 CTest target |
| Parquet 聚焦测试 | 11/11 passed | 补齐 `PARQUET_TEST_DATA` / `ARROW_TEST_DATA` 后通过 |
| Dataset/Acero 聚焦测试 | 26/26 passed | Dataset 12 个 target, Acero 14 个 target 全部通过 |
| 89 target 扩展范围 | 81/89 passed | 未通过项仍集中在核心 Arrow 已知失败, 没有新增 Parquet/Dataset/Acero 失败 |
| P1 文件 IO / Filesystem 完整目标 | 248/248 passed | 重新链接测试辅助库为 basename `NEEDED` 后, `arrow-io-file-test` 50/50 passed, `arrow-filesystem-test` 198/198 passed |
| 核心失败目标复验 | 1410 个非缺口用例 passed | 复用 basename `NEEDED` 和 GTest TMPDIR 方案后, `arrow-array-test` 完整通过; `buffer/misc/stl/cast` 排除已定位 OOM/timezone 缺口后主体通过 |
| 低风险增量复验 | 627 passed, 14 skipped | 复用 relink/TMPDIR 方案重新验证 `arrow-scalar-test`、`arrow-compute-internals-test` 和 testing 工具层 target |

当前最大完成的完整 CTest target 范围为 89 个, 其中 81 个通过, 通过率约 91%。该结果不等同于 Apache Arrow 全部上游测试套件 100% 通过。

## Parquet 聚焦测试

命令:

```sh
ctest --output-on-failure -R parquet
```

结果:

```text
100% tests passed, 0 tests failed out of 11
```

关键前置:

- 启用 `ARROW_PARQUET=ON`。
- 补齐 Apache `parquet-testing` 数据。
- 设置 `PARQUET_TEST_DATA`。
- 补齐 Apache `arrow-testing` 中 `testing/data/parquet/ARROW-17100.parquet`。
- 设置 `ARROW_TEST_DATA`。
- 处理 HarmonyOS loader 对相对 `NEEDED` 路径解析的差异。

## Dataset/Acero 聚焦测试

命令:

```sh
ctest --output-on-failure -R 'arrow-(dataset|acero)'
```

结果:

```text
100% tests passed, 0 tests failed out of 26
Label Time Summary:
arrow_acero      =  66.30 sec*proc (14 tests)
arrow_dataset    =  49.12 sec*proc (12 tests)
unittest         = 115.42 sec*proc (26 tests)
```

结论:

- Dataset/Acero 新增 26 个 target 全部通过。
- 扩展到 89 个 target 后, 未通过项仍为此前核心 Arrow 8 个已知失败项。
- 没有新增 Parquet、Dataset、Acero 失败项。

## 89 target 扩展范围

命令:

```sh
ctest -j1 --output-on-failure
```

结果:

```text
91% tests passed, 8 tests failed out of 89
```

未通过 target:

- `arrow-array-test`
- `arrow-buffer-test`
- `arrow-misc-test`
- `arrow-stl-test`
- `arrow-compute-scalar-cast-test`
- `arrow-compute-scalar-temporal-test`
- `arrow-io-file-test`
- `arrow-filesystem-test`

失败类型归纳:

- 全局析构阶段 SIGTRAP / 退出码 133。
- OOM/内存分配语义差异。
- 历史 timezone/DST offset 期望差异。
- `posix_fadvise` 零长度 range 行为差异。
- 目录尾斜杠 append/open 文件系统语义差异。

### 89 target 剩余失败归因闭环

`81/89` 是未应用后续测试工具链 relink、GTest TMPDIR 和 TZDIR 收敛前的最大 CTest 扩展统计。对 8 个原始失败 target 的后续复验结论如下:

| 原始失败 target | 后续状态 | 归因/处理边界 |
| --- | --- | --- |
| `arrow-array-test` | `1038 passed, 1 skipped` | GTest 捕获输出默认使用 `/tmp`，在当前真机上不可写或不可访问；测试框架临时迁移到 `TEST_TMPDIR` / `TMPDIR` 后完整 target 通过。 |
| `arrow-io-file-test` | `50/50 passed` | `WillNeed({{10, 0}})` 已通过 `0003` 的零长度 range 跳过逻辑收敛；退出码 133 归因为测试工具链相对 `NEEDED` 导致 GTest/GMock 重复加载，relink 后通过。 |
| `arrow-filesystem-test` | `198/198 passed` | 目录尾斜杠 append/open 已通过 `0003` 收敛；退出码 133 同样归因为测试工具链相对 `NEEDED`，relink 后通过。 |
| `arrow-buffer-test` | 非 OOM 子集 `45/45 passed` | 剩余 `TypedTestBuffer/0.ResizeOOM`、`TypedTestBuffer/1.ResizeOOM` 为极限分配/OOM 语义差异，其中单用例复测 `TypedTestBuffer/0.ResizeOOM` 为 `Signal 11`。 |
| `arrow-misc-test` | 非 OOM 子集 `180/180 passed` | 剩余 4 个 OOM/Reallocate 期望失败；单用例复测 `Default/TestMemoryPool/0.OOM` 为期望 `OutOfMemory` 但返回 OK。 |
| `arrow-stl-test` | 非 OOM 子集 `44/44 passed` | `allocator.TestOOM` 单用例复测为期望 `std::bad_alloc` 但实际未抛异常。 |
| `arrow-compute-scalar-cast-test` | `105/106 passed`; 非 timezone 子集 `103/103 passed` | `TZDIR` 支持后 timezone lookup 错误已收敛；剩余 Broken Hill 历史 DST offset 与 tzdb 规则/测试期望差异相关。 |
| `arrow-compute-scalar-temporal-test` | 全量 `46 passed, 1 skipped, 7 failed`; 过滤已定位差异后 `46 passed, 1 skipped` | 失败集中在 ambiguous/nonexistent time、Brussels rounding 和历史 DST offset；Python `tzdata 2026.3` 是当前最稳定 TZDIR，系统 `/etc/zoneinfo` 或 unset 会扩大失败范围。 |

因此, 当前 89 target 的剩余风险已经从“入口不可运行”收敛为三类明确边界:

- 测试工具链迁移差异: GTest TMPDIR 和相对 `NEEDED` relink，可通过复现脚本稳定处理。
- OHOS 内存极限语义差异: OOM/allocator 相关用例，不建议为了提高通过率扩大库行为 patch。
- 历史 timezone/DST 规则差异: 保留通用 `TZDIR` 注入能力，不把具体 tzdb 版本差异硬编码为库行为。

## P1 文件 IO / Filesystem 完整目标复验

构建 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-p1-build-fixed0003-v3-arm64-20260725-100004-36838
```

过滤项运行 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-p1-run-filters-fixed0003-v3-arm64-20260725-102349-63272
```

重新链接完整运行 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-p1-io-filesystem-relinked-full-fixed0003-v3-20260725-110742-34304
```

结果:

```text
arrow-io-file-test
50/50 passed, exit code 0

arrow-filesystem-test
198/198 passed, exit code 0
```

对照:

- 未重新链接时, `TestReadableFile.Close`、`TestReadableFile.Read` passed 且退出码 0。
- 未重新链接时, `TestReadableFile.SeekTellSize`、`TestReadableFile.WillNeed`、`TestReadableFile.NonexistentFile` test body passed 后退出码 133。
- macro-only probe 证明, 链接 `libarrow_testing.so` 且触发 `ASSERT_OK_AND_EQ` / `ASSERT_RAISES` / 非 OK `Status` message 路径时会在 `RUN_ALL_TESTS()` 返回前收到 `SIGTRAP`。
- `/proc/self/maps` 显示同一进程重复加载多份 `libarrow_gtest.so` / `libarrow_gmock.so`。

判断:

- `0003-ohos-file-io-edge-cases.patch` 对 `OpenAppendStream("abc/")` 的修复已被上游过滤项验证。
- `WillNeed({{10, 0}})` 原断言和完整 `arrow-io-file-test` 目标均已收敛。
- 退出码 133 根因不是文件 IO 行为, 而是 OHOS loader 对测试构建树相对 `NEEDED` 的解析导致 GTest/GMock 重复加载。
- 重新链接测试辅助库和测试二进制, 使 NEEDED 统一为 `libarrow_gtest.so`、`libarrow_gmock.so` 等 basename 后, P1 两个完整目标通过。
- 该处理属于上游测试工具链运行适配, 不应扩大为库行为补丁。

## 核心失败目标进一步复验

基础 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-failed-targets-build-relinked-fixed0003-v6-20260725-112704-45074
```

GTest TMPDIR patch 验证 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-array-gtest-tmpdir-fixed0003-v8-20260725-113941-49922
```

过滤主体复验 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-core-filtered-relinked-fixed0003-v1-20260725-114542-52288
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-cast-filtered-timezone-fixed0003-v3-20260725-114748-53871
```

TZDIR 源码补丁验证 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-cast-tzdir-srcpatch-fixed0003-v1-20260725-115002-54567
```

结果:

```text
arrow-array-test
1038 passed, 1 skipped, exit code 0

arrow-buffer-test
full run: TypedTestBuffer/0.ResizeOOM and TypedTestBuffer/1.ResizeOOM trigger SIGSEGV
filtered run: 45/45 passed, exit code 0

arrow-misc-test
full run: 180/184 passed, 4 OOM/Reallocate expectation failures
filtered run: 180/180 passed, exit code 0

arrow-stl-test
full run: 44/45 passed, allocator.TestOOM failed
filtered run: 44/44 passed, exit code 0

arrow-compute-scalar-cast-test
without TZDIR support: 103/106 passed, timezone lookup failed
with vendored date TZDIR patch and Python tzdata: 105/106 passed
filtered non-timezone run: 103/103 passed, exit code 0
```

判断:

- `arrow-array-test` 的剩余问题不是 Arrow 数组语义, 而是 GTest 在只读 `/tmp` 下捕获输出失败; 临时补丁为通用 `TEST_TMPDIR`/`TMPDIR` 支持后完整目标通过。
- `arrow-buffer-test`、`arrow-misc-test`、`arrow-stl-test` 的剩余未通过点集中在 OOM/超大分配期望; 非 OOM 主体均已通过。
- `arrow-compute-scalar-cast-test` 的 timezone lookup 已通过 `0004-vendored-date-tzdir.patch` 收敛为可配置 `TZDIR`; 剩余 1 个 Broken_Hill 历史 DST offset 与 tzdb 数据版本/规则差异相关。
- 本节中的过滤结果用于证明主体路径可执行和失败归因, 不写作完整 target 通过。

## 低风险增量复验

轻量探针 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-next-stage-light-probe-20260726-005620-9456
```

Core/Compute 已生成 target 复验 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-existing-core-relinked-v1-20260726-005955-10534
```

Testing 工具层 target 复验 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-testing-tools-relinked-v1-20260726-010338-13845
```

结果:

```text
arrow-scalar-test
164/164 passed, exit code 0

arrow-compute-internals-test
71/71 passed, exit code 0

arrow-generator-test
11/11 passed, exit code 0

arrow-gtest-util-test
11/11 passed, exit code 0

arrow-random-test
370 passed, 14 skipped, exit code 0
```

判断:

- 单一 relinked 测试库目录 + basename `NEEDED` 方案可继续复用于更多已生成 target。
- GTest `TEST_TMPDIR` / `TMPDIR` 迁移后, `arrow-gtest-util-test` 本身可稳定通过。

## ARROW_COMPUTE=ON 专项扩展验证

compute-on 构建 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-v2-20260726-012420-29629
```

说明:

- 新建独立 build tree: `build-upstream-tests-compute-temporal-v2`。
- 配置 `ARROW_COMPUTE=ON`、`ARROW_BUILD_TESTS=ON`、`CMAKE_SYSTEM_PROCESSOR=aarch64`、`BOOST_CONTEXT_ARCHITECTURE=arm64`、`BOOST_CONTEXT_ABI=aapcs`。
- v1 未指定处理器时 Boost.Context 误选 x86_64 汇编; v2 明确 aarch64/arm64 后构建通过。
- 使用与 P1 相同的测试工具链重链接方案, 将测试二进制和 `libarrow_gtest.so`、`libarrow_gmock.so`、`libarrow_gmock_main.so`、`libarrow_testing.so`、`libarrow_compute.so` 的 `NEEDED` 统一为 basename。

temporal 重链接 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-relinked-v3-20260726-020424-61875
```

temporal 正确 `TZDIR` 全量运行 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-tzdir-v4-20260726-020520-65347
```

结果:

```text
arrow-compute-scalar-temporal-test
54 tests from 3 suites ran
46 passed, 1 skipped, 7 failed, exit code 1

failed tests:
ScalarTemporalTest.TestZoned2
ScalarTemporalTest.TestAssumeTimezoneAmbiguous
ScalarTemporalTest.TestAssumeTimezoneNonexistent
ScalarTemporalTest.TestCeilFloorRoundTemporalBrussels
ScalarTemporalTestMultipleSinceGreaterUnit.CeilZoned
ScalarTemporalTestMultipleSinceGreaterUnit.FloorZoned
ScalarTemporalTestMultipleSinceGreaterUnit.RoundZoned
```

temporal 过滤已定位差异后 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-filtered-v5-20260726-020638-570
```

结果:

```text
arrow-compute-scalar-temporal-test
47 tests from 3 suites ran
46 passed, 1 skipped, exit code 0
```

compute scalar/core RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-scalar-batch-v1-20260726-020807-1090
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-core-batch-v1-20260726-021148-4888
```

结果:

```text
arrow-compute-scalar-if-else-test
420/420 passed, exit code 0

arrow-compute-scalar-math-test
521 passed, 25 skipped, exit code 0

arrow-compute-scalar-type-test
196/196 passed, exit code 0

arrow-compute-scalar-utility-test
95/95 passed, exit code 0

arrow-compute-kernel-utility-test
6/6 passed, exit code 0
```

compute vector/row RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-vector-row-batch-v1-20260726-021842-12033
```

结果:

```text
arrow-compute-vector-test
1103/1103 passed, exit code 0

arrow-compute-vector-selection-test
168/168 passed, exit code 0

arrow-compute-vector-sort-test
283/283 passed, exit code 0

arrow-compute-vector-swizzle-test
16/16 passed, exit code 0

arrow-compute-row-test
77/77 passed, exit code 0
```

compute aggregate/expression RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-aggregate-expression-v1-20260726-022734-17441
```

结果:

```text
arrow-compute-expression-test
47/47 passed, exit code 0

arrow-compute-aggregate-test
340/340 passed, exit code 0
```

判断:

- compute-on 专项验证新增 12 个完整通过 target, 合计 3272 passed, 25 skipped。
- temporal 目标在正确 `TZDIR` 下仍有 7 个历史 DST/offset 相关失败; 过滤已定位差异后主体 46 passed, 1 skipped。
- temporal 失败集中在 timezone ambiguous/nonexistent、Brussels rounding 和 Broken_Hill/DST 历史边界, 不应写成完整 target 通过。
- 本轮错误尝试的 `arrow-compute-scalar-arithmetic-test`、`arrow-compute-scalar-boolean-test`、`arrow-compute-scalar-compare-test`、`arrow-compute-scalar-validity-test` 并非当前 CMake 配置生成的 target, 因此不计入上游 target 失败。

## temporal DST 轻量风险探针

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-temporal-dst-probe-v1-20260726-192802-38911
```

环境探针:

```text
Python tzdata: 2026.3
Python TZDIR: /storage/Users/currentUser/.local/lib/python3.12/site-packages/tzdata/zoneinfo
system TZDIR: /etc/zoneinfo
missing: /usr/share/zoneinfo, /system/usr/share/zoneinfo
```

对照结果:

```text
TZDIR=Python tzdata 2026.3
failing set: 0/7 passed
filtered passing set: 46 passed, 1 skipped, exit code 0

TZDIR=/etc/zoneinfo
failing set: 0/7 passed
filtered passing set: 29 passed, 1 skipped, 17 failed

TZDIR unset
failing set: 0/7 passed
filtered passing set: 29 passed, 1 skipped, 17 failed
```

判断:

- Python `tzdata 2026.3` 是当前真机上最稳定的 IANA zoneinfo 来源。
- 系统 `/etc/zoneinfo` 和未设置 `TZDIR` 均会扩大失败范围, 不适合作为本 PR 的默认回退策略。
- 剩余 7 个 temporal 失败不是 `TZDIR` 缺失导致, 而是历史 timezone/DST 规则或测试期望差异; 暂不扩大为库行为 patch。

## OOM / allocator 轻量风险探针

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-stl-single-v1-20260726-193736-42432
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-buffer-single-v1-20260726-193822-42713
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-misc-single-v1-20260726-193854-42969
```

执行方式:

- 复用 `build-upstream-tests-p1-fixed0003-arm64-v3/relinked-needed-run-core-filtered-v1` 中已重新链接的测试二进制。
- 使用 runner `--mode smoke --try-lock`, 不触发重新构建。
- 仅执行已知 OOM/allocator 风险中的单个用例, 避免在当前真机低空闲内存状态下批量施压。

单用例结果:

```text
arrow-stl-test --gtest_filter=allocator.TestOOM
exit code 1
Expected std::bad_alloc, actual throws nothing

arrow-buffer-test --gtest_filter=TypedTestBuffer/0.ResizeOOM
exit code 139
Signal 11 (core dumped)

arrow-misc-test --gtest_filter=Default/TestMemoryPool/0.OOM
exit code 1
Expected OutOfMemory, but got OK
```

判断:

- OOM/allocator 残留项不是 GTest 临时目录、相对 `NEEDED` 或测试数据缺失造成。
- 当前失败形态分别覆盖“未抛异常”、“SIGSEGV”、“未返回 OutOfMemory”, 更接近 OHOS allocator / 虚拟内存 overcommit / 极限分配语义差异。
- 暂不为提高通过率引入宽泛内存分配行为 patch; 后续若继续推进, 应在独立内存压力窗口中逐项定位, 并优先记录为环境/系统差异。

## 当前结论

apache-arrow 已完成可迁移 C++ CTest 子集的分层验证。当前证据适合路径 B:

- 真机上真实执行上游 C++ CTest target。
- 明确统计通过率和未通过 target。
- 明确说明不可执行和暂缓范围。
- 将消费者 `test_package` 与上游测试结果分开统计。

## ORC / Flight 重依赖模块探针

ORC 首轮探针 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-orc-probe-v1-20260726-224750-37131
```

执行方式:

- 通过隔离 runner `--mode heavy --try-lock` 执行。
- 配置 `ARROW_ORC=ON`、`ARROW_BUILD_TESTS=ON`。
- 复用已缓存 Boost / GoogleTest FetchContent 源码。
- 代表 target 为 `arrow-orc-adapter-test`。

结果:

```text
exit code 124
timeout: 1200 seconds
last configure stage: Protobuf: Building Protocol Buffers from source using FetchContent
```

判断:

- ORC 探针未进入 `arrow-orc-adapter-test` 构建/运行阶段。
- 当前证据说明 ORC 会牵出 protobuf 等重依赖源码构建, 在当前真机/CI 资源窗口下不适合直接纳入基础 recipe。
- 该结果记录为重依赖环境/工具链缺口, 不写作 ORC 上游 target 失败。

Flight 首轮探针:

v2 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v2-20260727-040342-62286
```

v2 结果:

```text
exit code 1
gRPC 1.46.3 tarball download: done
failure: CMake/libarchive extract failed on link entries
example: examples/python/auth/helloworld.proto -> ../../protos/helloworld.proto
manual tar reproduction: link creation returned Permission denied
```

处理:

- 当前真机文件系统不允许创建 symlink/hardlink。
- 新增 `scripts/ohos_extract_tar_no_links.py`, 将 gRPC tarball 中 12 个 link 条目展开为普通文件/目录副本。
- 新增 `--grpc-src` probe 参数, 允许 Flight 探针复用预解包 gRPC source。

v3 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v3-20260727-042031-3517
```

v3 结果:

```text
exit code 1
gRPC FetchContent source: pre-extracted no-links source
progress: passed gRPC source extraction
failure: Flight tests require static Arrow when bundled static gRPC/protobuf is used
```

处理:

- Flight probe 切换为静态 Arrow 测试树: `ARROW_BUILD_STATIC=ON`, `ARROW_BUILD_SHARED=OFF`, `ARROW_DEPENDENCY_USE_SHARED=OFF`。

v4 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v4-20260727-043233-9482
```

v4 结果:

```text
exit code 1
configure: done
generate: failed
failure: missing OpenSSL::SSL and OpenSSL::Crypto targets
```

判断:

- Flight 首轮探针已从 inventory 推进到真实 CMake 配置链路。
- gRPC 源码包 link 条目问题可通过 no-links 预解包方式绕过。
- 当前阻塞边界为 OpenSSL/BoringSSL 依赖闭环; 隔离 Conan cache 和当前测试 build tree 未发现 `libssl` / `libcrypto` 可复用产物。
- `arrow-flight-internals-test` 尚未进入构建/运行阶段, 因此不写作 Flight target 失败或通过。
- OpenSSL/BoringSSL 属于 Flight/gRPC 额外依赖适配范围, 不纳入当前 apache-arrow 基础 recipe。
