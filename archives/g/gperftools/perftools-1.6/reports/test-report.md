# test-report.md — gperftools perftools-1.6（R04 口径同步）

## 上游测试（双口径台账，R04 按 Makefile.am TESTS 全量口径更新）

> 数据来源：R03 全量 `make check`（`r03-makecheck.log`，静态构建）。R04 仅同步台账口径，
> 不做任何源码/配方/测试改动。上游声明总数以上游 perftools-1.6 Makefile.am `TESTS +=` 注册项全量计数。

### source_declared_total（上游 Makefile.am TESTS 全量注册声明总数）
上游 `Makefile.am` 中 `TESTS +=` 全量注册 **43 项**（33 个二进制测试目标 + 10 个 .sh 脚本驱动测试，
含 debug/both/large 变体），Linux 默认全特性配置下全部生效：

| # | TESTS 注册项 | 类型 | 当前配置注册 | 结果 / 未注册原因 |
|---|---|---|---|---|
| 1 | low_level_alloc_unittest | 二进制 | 是 | PASS |
| 2 | atomicops_unittest | 二进制 | 是 | PASS |
| 3 | stacktrace_unittest | 二进制 | 是 | PASS |
| 4 | tcmalloc_minimal_unittest | 二进制 | 是 | PASS |
| 5 | tcmalloc_minimal_large_unittest | 二进制 | 是 | PASS |
| 6 | maybe_threads_unittest.sh | .sh 脚本 | 否 | **未注册①**：`if !ENABLE_STATIC` 守卫，静态构建（--enable-static/--disable-shared）下不成立 |
| 7 | addressmap_unittest | 二进制 | 是 | PASS |
| 8 | system_alloc_unittest | 二进制 | 是 | PASS |
| 9 | packed_cache_test | 二进制 | 是 | PASS |
| 10 | frag_unittest | 二进制 | 是 | PASS |
| 11 | markidle_unittest | 二进制 | 是 | PASS |
| 12 | malloc_extension_test | 二进制 | 是 | PASS |
| 13 | malloc_extension_c_test | 二进制 | 否 | **未注册①**：`if !ENABLE_STATIC` 守卫，静态构建下不成立 |
| 14 | memalign_unittest | 二进制 | 是 | PASS |
| 15 | page_heap_test | 二进制 | 是 | PASS |
| 16 | pagemap_unittest | 二进制 | 是 | PASS |
| 17 | realloc_unittest | 二进制 | 是 | PASS |
| 18 | stack_trace_table_test | 二进制 | 是 | PASS |
| 19 | thread_dealloc_unittest | 二进制 | 是 | PASS |
| 20 | tcmalloc_minimal_debug_unittest | 二进制 | 是 | PASS |
| 21 | malloc_extension_debug_test | 二进制 | 是 | PASS |
| 22 | memalign_debug_unittest | 二进制 | 是 | PASS |
| 23 | realloc_debug_unittest | 二进制 | 是 | PASS |
| 24 | debugallocation_test.sh | .sh 脚本 | 是 | PASS |
| 25 | tcmalloc_unittest | 二进制 | 是 | PASS |
| 26 | tcmalloc_both_unittest | 二进制 | 是 | PASS |
| 27 | tcmalloc_large_unittest | 二进制 | 是 | PASS |
| 28 | raw_printer_test | 二进制 | 是 | PASS |
| 29 | sampler_test | 二进制 | 是 | PASS |
| 30 | sampling_test.sh | .sh 脚本 | 是 | FAIL（pprof 符号解析平台差异，见下） |
| 31 | heap-profiler_unittest.sh | .sh 脚本 | 是 | FAIL（GetCallerStackTrace 空栈，见下） |
| 32 | heap-checker_unittest.sh | .sh 脚本 | 是 | FAIL（MemoryRegionMap regions_，见下） |
| 33 | heap-checker-death_unittest.sh | .sh 脚本 | 是 | FAIL（同上） |
| 34 | tcmalloc_debug_unittest | 二进制 | 是 | PASS |
| 35 | sampler_debug_test | 二进制 | 是 | PASS |
| 36 | sampling_debug_test.sh | .sh 脚本 | 是 | FAIL（同 #30） |
| 37 | heap-profiler_debug_unittest.sh | .sh 脚本 | 是 | FAIL（同 #31） |
| 38 | heap-checker_debug_unittest.sh | .sh 脚本 | 是 | FAIL（同 #32） |
| 39 | getpc_test | 二进制 | 否 | **未注册②**：`if WITH_CPU_PROFILER` 守卫，CPU profiler 未启用 |
| 40 | profiledata_unittest | 二进制 | 否 | **未注册②**：同上 |
| 41 | profile_handler_unittest | 二进制 | 否 | **未注册②**：同上 |
| 42 | profiler_unittest.sh | .sh 脚本 | 否 | **未注册②**：同上 |
| 43 | tcmalloc_and_profiler_unittest | 二进制 | 否 | **未注册②**：同上 |

**source_declared_total = 43**（33 二进制 + 10 .sh 脚本；Makefile.am `TESTS +=` 全量注册，Linux 默认全特性配置全部生效）。
此前 R01-R03 声明 24 为窄口径少报，R04 已按分析端 PR 正文口径修正为 43。

### 7 项未注册（声明 43 与注册 36 之差，逐项原因，不得静默改写声明数）
- **① 静态构建排除（`--enable-static`/`--disable-shared` 使 `!ENABLE_STATIC` 不成立）**，共 2 项：
  `maybe_threads_unittest.sh`（#6）、`malloc_extension_c_test`（#13）
- **② CPU profiler 未启用（`WITH_CPU_PROFILER` 不成立）**，共 5 项：
  `getpc_test`（#39）、`profiledata_unittest`（#40）、`profile_handler_unittest`（#41）、
  `profiler_unittest.sh`（#42）、`tcmalloc_and_profiler_unittest`（#43）

### configured_executable_total（当前 OHOS 配置实际实例化/注册的独立可执行用例数）
`make check` 在当前静态构建下实际注册 = **36**（28 二进制 + 8 .sh 脚本）= 43 − 7 未注册。

### executed_passed_total / failed / not_run
- **executed_passed_total = 29**（R03 实测 `make check` PASS 计数）
- **failed = 7**（脚本类真实平台差异，计入分母 43、不计通过）：
  - sampling_test.sh / sampling_debug_test.sh（#30/#36）：pprof 符号解析对 OHOS 静态二进制输出裸地址（0x…）而非 AllocateAllocate 符号，断言 `grep '^ *[5-9][0-9]\.[0-9].*AllocateAllocate'` 失败
  - heap-profiler_unittest.sh / heap-profiler_debug_unittest.sh（#31/#37）：GetCallerStackTrace 恒 0（backtrace 栈浅 + fallback skip 深 → 空栈），`didn't account for 90% of executable memory` 断言失败
  - heap-checker_unittest.sh / heap-checker_debug_unittest.sh / heap-checker-death_unittest.sh（#32/#38/#33）：HEAPCHECK 运行时依赖 MemoryRegionMap（regions_ 空崩溃 / Signal 11 / 超时）
- **not_run = 0**（注册的 36 项均已尝试执行；7 项未注册不计入 not_run）

### 全量通过率（以全部独立上游用例数为分母）
- **全量通过率 = `29/43 (67.4%)`**（43 个 source_declared 独立用例中 29 个实际运行通过）
- 配置集合通过率 = `29/36 (80.6%)`

### 7 项失败逐项证据（入口/命令/退出码/首错/阻塞归属/恢复条件）
证据日志：`r03-ev-*.log`（R03 固化）：
- `r03-ev-hp.log` / `r03-ev-hpd.log`（heap-profiler ×2，exit=4，`didn't account for 90% of executable memory`）
- `r03-ev-hc.log` / `r03-ev-hcd.log` / `r03-ev-hcdd.log`（heap-checker ×3，exit=4/1，`regions_` / Signal 11 / Wrong exit code）
- `r03-ev-dbg.log`（debugallocation，R03 已修复转绿）
阻塞归属：OHOS 静态库下 GetStackTrace/backtrace 栈深与符号解析差异、MemoryRegionMap mmap hook 时序差异（真实平台行为差异）。
恢复条件：加 `-fno-builtin` 与观察分配指针已修复 hook 类；heap-profiler/heap-checker/sampling 需栈回溯与符号解析平台能力或按测试适配放宽断言（由分析端决定是否返工）。

## 测试统计结论
- 编译成功；conan-verify G0-G4/L2/L4/L5 全 PASS（R03 复验）；finish/W2/W3 通过（R04 复验）
- 双口径台账（R04 同步）：source_declared_total=43 / configured_executable_total=36 / executed_passed_total=29 / failed=7 / not_run=0
- 全量通过率 `29/43 (67.4%)`；配置集合通过率 `29/36 (80.6%)`