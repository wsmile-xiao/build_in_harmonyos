# apache-arrow 24.0.0 质量验证报告

## Conan 包验证

### shared 验证

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-apache-arrow-isolated-base-conan-shared-localprofile-fixed0003-20260725-092157-9871
```

结果:

- `conan create` 通过。
- CI 脚本 L1a/L1b/L1e/L4/L5 通过。
- CMakeDeps 声明固定 target `Arrow::arrow`。
- `test_package` 输出:
  - `OK: Arrow Int32Array created with 1 element(s)`
  - `OK: Arrow compute add returned 43`
  - `OK: Arrow file IO edge cases validated`

### static 验证

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-apache-arrow-isolated-base-conan-static-localprofile-fixed0003-20260725-093006-15935
```

结果:

- `conan create ... -o apache-arrow/*:shared=False -c tools.build:jobs=6` 通过。
- `test_package` 同样输出 Int32、Compute add、file IO 三个 OK。
- 验证固定 `Arrow::arrow` target 和 static 链接顺序。

### 增强 test_package 复验

shared RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-conan-shared-enhanced-testpackage-0003-20260725-025002-36058
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-conan-shared-localprofile-0004-20260725-121655-15887
```

static RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-conan-static-enhanced-testpackage-0003-20260725-025033-36330
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-conan-static-localprofile-0004-20260725-122504-19830
```

结果:

- 两轮均通过。
- CMakeDeps 均声明 `Arrow::arrow`。
- `test_package` 均输出 Int32、Compute add、file IO 三个 OK。
- `0004-vendored-date-tzdir.patch` 加入后, shared/static localprofile 重新验证均通过。

## test_package 覆盖范围

文件:

- `test_package/test_arrow.cpp`
- `test_package/CMakeLists.txt`
- `test_package/MANIFEST.yml`

可观测断言数: 15

覆盖:

- `arrow::Int32Builder::Append`
- `arrow::Int32Builder::Finish`
- Arrow array length check
- `arrow::compute::Initialize`
- `arrow::compute::CallFunction("add")`
- `arrow::io::FileOutputStream::Open`
- file write and close
- `arrow::io::ReadableFile::Open`
- `ReadableFile::WillNeed({{0, 4}, {10, 0}})`
- `arrow::fs::LocalFileSystem::CreateDir`
- `LocalFileSystem::OpenAppendStream(dir + "/")` must fail
- `LocalFileSystem::DeleteDir`

## 本地静态检查

已执行:

```text
python -m py_compile archives\a\apache-arrow\24.0.0\conanfile.py archives\a\apache-arrow\24.0.0\test_package\conanfile.py
```

结果: 通过。

已执行 YAML 解析:

```text
archives/a/apache-arrow/24.0.0/conandata.yml
archives/a/apache-arrow/24.0.0/test_package/MANIFEST.yml
```

结果: 通过。

已执行:

```text
git diff --check -- archives/a/apache-arrow/24.0.0
```

结果: 未发现空白错误; Windows 工作区仅提示 LF/CRLF 配置警告。

## 上游 P1 文件 IO / Filesystem 目标

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-p1-io-filesystem-relinked-full-fixed0003-v3-20260725-110742-34304
```

执行方式:

- 基于已构建 P1 测试树重新链接测试辅助库和测试二进制。
- 将 `libarrow_gtest.so`、`libarrow_gmock.so`、`libarrow_gmock_main.so`、`libarrow_testing.so` 和测试二进制的 `NEEDED` 统一生成为 basename。
- 运行时只使用单一 relinked 目录作为 `LD_LIBRARY_PATH`, 避免 OHOS loader 因相对 `NEEDED` 路径加载多份 GTest/GMock。

结果:

- `arrow-io-file-test`: 50/50 passed, exit code 0。
- `arrow-filesystem-test`: 198/198 passed, exit code 0。

## 核心失败目标扩展复验

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-failed-targets-build-relinked-fixed0003-v6-20260725-112704-45074
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-array-gtest-tmpdir-fixed0003-v8-20260725-113941-49922
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-core-filtered-relinked-fixed0003-v1-20260725-114542-52288
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-cast-filtered-timezone-fixed0003-v3-20260725-114748-53871
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-cast-tzdir-srcpatch-fixed0003-v1-20260725-115002-54567
```

结果:

- `arrow-array-test`: GTest `TEST_TMPDIR` / `TMPDIR` 临时 patch 后 1038 passed, 1 skipped。
- `arrow-buffer-test`: OOM `ResizeOOM` 2 项定位为 SIGSEGV; 过滤后 45/45 passed。
- `arrow-misc-test`: OOM/Reallocate 4 项失败; 过滤后 180/180 passed。
- `arrow-stl-test`: `allocator.TestOOM` 失败; 过滤后 44/44 passed。
- `arrow-compute-scalar-cast-test`: `0004` 的 `TZDIR` 支持验证后 105/106 passed; 非 timezone 子集 103/103 passed。

## 低风险增量 target 复验

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-next-stage-light-probe-20260726-005620-9456
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-existing-core-relinked-v1-20260726-005955-10534
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-testing-tools-relinked-v1-20260726-010338-13845
```

结果:

- `arrow-scalar-test`: 164/164 passed。
- `arrow-compute-internals-test`: 71/71 passed。
- `arrow-generator-test`: 11/11 passed。
- `arrow-gtest-util-test`: 11/11 passed。
- `arrow-random-test`: 370 passed, 14 skipped。

本轮合计新增复验 627 passed, 14 skipped。该复验主要用于确认 relinked basename `NEEDED` 和 GTest TMPDIR 方案可稳定复用于更多已生成 target。

## compute-on 专项扩展验证

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-v2-20260726-012420-29629
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-relinked-v3-20260726-020424-61875
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-tzdir-v4-20260726-020520-65347
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-filtered-v5-20260726-020638-570
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-scalar-batch-v1-20260726-020807-1090
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-core-batch-v1-20260726-021148-4888
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-vector-row-batch-v1-20260726-021842-12033
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-aggregate-expression-v1-20260726-022734-17441
```

执行方式:

- 新建 `ARROW_COMPUTE=ON`、`ARROW_BUILD_TESTS=ON` 的独立 compute 测试树。
- 显式设置 `CMAKE_SYSTEM_PROCESSOR=aarch64`、`BOOST_CONTEXT_ARCHITECTURE=arm64`、`BOOST_CONTEXT_ABI=aapcs`, 避免 Boost.Context 在 `unknown` processor 下误选 x86_64 汇编。
- 继续复用“单一 relinked 测试库目录 + basename `NEEDED`”方案, 避免 OHOS loader 重复加载 GTest/GMock。
- `TZDIR` 指向 Python `tzdata/zoneinfo`。

完整通过 target:

- `arrow-compute-scalar-if-else-test`: 420/420 passed。
- `arrow-compute-scalar-math-test`: 521 passed, 25 skipped。
- `arrow-compute-scalar-type-test`: 196/196 passed。
- `arrow-compute-scalar-utility-test`: 95/95 passed。
- `arrow-compute-kernel-utility-test`: 6/6 passed。
- `arrow-compute-vector-test`: 1103/1103 passed。
- `arrow-compute-vector-selection-test`: 168/168 passed。
- `arrow-compute-vector-sort-test`: 283/283 passed。
- `arrow-compute-vector-swizzle-test`: 16/16 passed。
- `arrow-compute-row-test`: 77/77 passed。
- `arrow-compute-expression-test`: 47/47 passed。
- `arrow-compute-aggregate-test`: 340/340 passed。

本轮 compute-on 完整通过 target 合计 3272 passed, 25 skipped。

temporal 专项:

- `arrow-compute-scalar-temporal-test` 全量运行: 54 tests, 46 passed, 1 skipped, 7 failed。
- 失败集中在 timezone ambiguous/nonexistent、Brussels rounding 和 Broken_Hill/DST 历史边界。
- 过滤已定位差异后: 47 tests, 46 passed, 1 skipped, exit code 0。
- temporal 全量结果不写作完整 target 通过, 仅作为历史时区规则差异和主体路径验证证据。

### temporal DST 轻量风险探针

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-temporal-dst-probe-v1-20260726-192802-38911
```

结果:

- Python `tzdata 2026.3` 的 zoneinfo 路径下, 已过滤主体 temporal 用例保持 46 passed, 1 skipped。
- 系统 `/etc/zoneinfo` 或不设置 `TZDIR` 时, 同一主体用例扩大为 17 failed。
- 剩余 7 个失败用例在三种 TZDIR 配置下均未通过, 判断为历史 timezone/DST 规则或测试期望差异, 暂不作为库行为 patch 扩大修复。

### OOM / allocator 轻量风险探针

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-stl-single-v1-20260726-193736-42432
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-buffer-single-v1-20260726-193822-42713
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-misc-single-v1-20260726-193854-42969
```

结果:

- `allocator.TestOOM`: exit code 1, 期望 `std::bad_alloc`, 实际未抛异常。
- `TypedTestBuffer/0.ResizeOOM`: exit code 139, `Signal 11`。
- `Default/TestMemoryPool/0.OOM`: exit code 1, 期望 `OutOfMemory`, 实际返回 OK。

结论: OOM/allocator 剩余项不是测试运行入口缺失导致, 更接近 OHOS allocator / 虚拟内存极限分配语义差异; 当前不纳入基础包源码 patch。

## 当前正式补丁

- `patches/0001-setupcxxflags-unknown-processor.patch`
- `patches/0002-buildutils-ohos-soname.patch`
- `patches/0003-ohos-file-io-edge-cases.patch`
- `patches/0004-vendored-date-tzdir.patch`

## 当前风险和限制

- 当前 recipe 为基础消费包, 未启用 Parquet/Dataset/Flight/ORC/Gandiva/CUDA 等重依赖模块。
- 上游 C++ CTest 最大完成范围为 81/89; 另有 compute-on 专项 12 个 target 完整通过, temporal 主体过滤通过。不声明完整上游全量通过。
- Python、Java、R、Flight、CUDA/Gandiva 等运行时或硬件相关测试子集未声明通过。
- `arrow-io-file-test` / `arrow-filesystem-test` 的 133 已定位为测试工具链相对 `NEEDED` 导致的 GTest/GMock 重复加载, P1 两目标已通过; 后续 89 target 扩展需复用同一 relinked 方案。
- `arrow-compute-scalar-temporal-test` 已在 compute-on 测试树中验证, 全量剩余 7 个历史 DST/offset 相关失败。
- temporal DST 轻量探针确认 Python `tzdata/zoneinfo` 是当前真机上最稳定的 IANA tzdb 来源; 系统 `/etc/zoneinfo` 或 unset `TZDIR` 不适合作为默认回退。
- OOM/allocator 单用例探针确认剩余失败不是构建或测试工具链问题, 暂作为 OHOS 内存极限语义差异记录。
- 仍需继续定位 timezone 历史偏移、OOM/allocator 以及 Parquet/Dataset/Flight/ORC/Gandiva/CUDA 等重依赖模块问题。

## 质量结论

当前 apache-arrow 24.0.0 已满足路径 A 基础消费验证, 并具备路径 B 申报所需的分层测试迁移证据。质量判断应以 shared/static Conan 真机验证、增强 test_package 15 项断言、上游 C++ CTest 81/89 扩展结果和 compute-on 专项验证共同说明, 不应将其中任一项单独表述为完整上游测试通过。
