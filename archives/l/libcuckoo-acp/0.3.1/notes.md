# libcuckoo-acp 0.3.1 适配笔记

**日期**: 2026-10-10（首轮：工作树已完成，真机预检待 HMBS 后台执行）
**状态**: 待真机预检回填实测证据
**分支**: feat/libcuckoo-acp-0.3.1
**上游**: https://github.com/efficient/libcuckoo/archive/refs/tags/v0.3.1.tar.gz

## 1. 上游审计

- 构建系统：CMake（顶层 `cmake_minimum_required(VERSION 3.1.0)`，C/C++ 双语言）。
- 产物：纯头文件。`libcuckoo/CMakeLists.txt` 安装 4 个头文件到
  `include/libcuckoo/`（cuckoohash_map.hh、cuckoohash_config.hh、
  cuckoohash_util.hh、bucket_container.hh）+ `libcuckoo-config*.cmake`；
  `libcuckoo-c/CMakeLists.txt` 只安装模板源到 `include/libcuckoo-c/`。
  无二进制库、无可执行文件（纯库，无 `commands.json`）。
- 依赖：仅 `find_package(Threads)`（系统 libc 提供），无 Conan 依赖。
- 测试体系（`tests/CMakeLists.txt`，选项全 OFF 默认，需 `BUILD_TESTS=ON`）：
  | 位置 | add_test 注册 | 数量 |
  |------|--------------|------|
  | tests/unit-tests（Catch 单头，11 个 test_*.cc 编入同一二进制） | unit_tests | 1 |
  | tests/stress-tests | stress_checked、stress_unchecked | 2 |
  | tests/universal-benchmark | pure_read/pure_insert/pure_erase/pure_update/pure_upsert/insert_expansion/read_insert_expansion | 7 |
  | **合计（ctest_entries 口径）** | | **10** |
- Catch/pcg 均为仓内目录（无 `.gitmodules`），tag 归档自带测试源码。
- sha256 指纹 `a87122b9...9a7ba8` 与历史归档及 conan-center 同版本一致；
  历史 `init-build` 曾成功下载该归档（见 archives/l/libcuckoo/0.3.1/notes.md）。

## 2. 历史经验比对（W0b）

- 同上游版本的 archives/l/libcuckoo/0.3.1/（状态 built，2026-08-10）结论复用：
  header-only、CMake 仅安装；`cmake_minimum_required` 运行时改写
  3.1.0→3.5.0...3.31（CMake 4.x 兼容）；消费者测试覆盖 insert/find/erase/update。
- 该历史配方未开启上游测试，理由是“Catch 与 OHOS stdlib 不兼容”。
  本轮不照搬该结论：其一，环境语义已变（当年工具链 vs 当前 clang 15 + libc++）；
  其二，仓内已有 Catch 系上游测试在 OHOS 实测通过的先例（cxxopts 以自带
  catch.hpp 做 `CXXOPTS_BUILD_TESTS=ON` + ctest；brynet 9 项“实测全部通过”）。
  因此本配方以 `BUILD_TESTS=ON` 开启全套 10 项，真机实测说了算。
- 若预检证实 Catch 在当前工具链下确有编译错误，再凭真实日志做最小修复
  （POSIX 兼容方式，不碰 `__OHOS__` 平台宏），并在“上游测试用例修改说明”中申报。

## 3. 配方设计要点

- 包名 `libcuckoo-acp`（任务命名），`package_type="header-library"`，
  `package_id` 清空（header-only 单一 ID，仓内同类惯例）。
- `package_info()` 保留上游规范 CMake 名（`cmake_file_name=libcuckoo`、
  `cmake_target_name=libcuckoo::libcuckoo`），消费方 CMakeLists 与上游示例一致；
  `system_libs=["pthread"]`（历史配方在 OHOS 工具链上链接已验证）。
- `build()` 末尾 `_run_upstream_tests()`：`ctest -N` 取分母，
  `ctest --output-on-failure` 全量执行并落盘解析；`Test #N` 行是唯一计数源，
  无字符串数数回退、无算术修正分支；恒等式
  `passed+failed==executed`、`executed<=discovered`、
  `executed+skipped<=discovered` 校验不通过即判证据失败。
  标记落盘 `hmbs_upstream_result.json`，`package()` 收入 `res/` 供复发；
  非全绿即抛异常（缺口留待真实证据再走 gaps 路径，不做推测性 gaps 分支）。
- test_package 消费者二进制 10 项 `LIBCUCKOO_ACP_CHECK`（insert/find/
  find-missing/size/erase/update/upsert/locked-table/clear-empty/find-throws），
  汇总行 `LIBCUCKOO_ACP_TEST total=10 passed=N` 为唯一计数源；
  `test()` 先 `cmake.test()` 再直接运行二进制取日志，双 HMBS 标记缺一即失败。
- Catch URNG 可移植修复改为运行时单行替换（见 §3d；conandata 无补丁声明）；
  `self.run` 中无裸 shell 环境变量（R33）。

## 3b. E092 真机 configure 失败修复（2026-10-10 第二轮）

- 预检失败：cmake configure 期报 System is unknown to cmake（Platform/HarmonyOS），随后 CMAKE_C/CXX_COMPILER（/data/service/hnp/bin/clang）检查失败，Configuring incomplete。
- 根因：OHOS 适配版 Conan 把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，而真机 CMake 4.4.3 无 Platform/HarmonyOS.cmake（仅有 Platform/OHOS.cmake），未知平台丢失 Linux 语义致编译器检查失败；与编译器缺失无关。
- 修复：主包与 test_package 的 generate() 均经 tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux" 固定（必须走 cache_variables 经 -D 预置，tc.variables 无法阻止 GenericSystemBlock 的 HarmonyOS 注入；参照 vvenc/1.14.0 E092 落地）。
- header-only 安装本身不变；BUILD_TESTS=ON 与 ctest 口径不变。

## 3c. 编译器探测回退（2026-10-10 第三轮，与上一轮不同策略）

- 上一轮仅固定 CMAKE_SYSTEM_NAME=Linux 后复测仍失败：project() 报 The C/CXX compiler identification is unknown，编译器仍为 profile 钉死的 /data/service/hnp/bin/clang{,++}。
- 本轮改用聚合经验#1 的存在即用策略：conf 路径存在时零改动；缺失时经 PATH（含 ~/usr/local/bin）探测同类编译器，仅覆盖 CC/CXX（cache_variables 显式传入 + 生成的 conan_toolchain.cmake 同步替换 + build 域 CC/CXX 导出），不碰 CFLAGS/LDFLAGS；主包与 test_package 同步。
- build() 增加 HMBS diag（compiler_executables 原值 + 解析后 --version），供下轮区分真缺编译器与真实工具链失败。

## 3d. Catch URNG portability fix (2026-10-10 fourth round)

- Preflight failed at cmake.build() compiling tests/unit-tests/test_runner.cc:
  libc++-ohos uniform_int_distribution.h:235 static_assert
  __libcpp_random_is_valid_urng<Catch::RandomNumberGenerator> failed,
  instantiated from shuffle.h via RandomNumberGenerator::shuffle(sorted).
- Root cause: bundled Catch v1.5.9 declares
  `typedef std::ptrdiff_t result_type` (signed), but the C++ URNG requirement
  (enforced by new libc++ static_assert) demands an unsigned integer
  result_type; older toolchains silently accepted the violation.
- Fix: conandata patch 0001-catch-urng-ohos-portability.patch changes only
  result_type to `unsigned int` (value range 0..1000000 unchanged, no test
  logic touched); full BUILD_TESTS=ON suite (10 ctest entries) still builds
  and runs. Applied via apply_conandata_patches before configure.
- 2026-10-10 fifth round (patch header fix): preflight failed before compile
  with `Failed to parse patch ... extra lines for hunk no.1 at 16`.
  Root cause was a hunk-count typo: body carries 7 old lines (6 context + 1
  removal) and 12 new lines (6 context + 6 additions) but the header declared
  `+6464,11`. Fixed header to `@@ -6464,7 +6464,12 @@`; no content change.
- 2026-10-10 sixth round (drop .patch, runtime replace): header fix parsed
  but preflight then failed with `Failed to apply patch ... source file is
  different - b'tests/Catch/single_include/catch.hpp'` (actual b'').
  The unified-diff context does not match the archived catch.hpp, so the
  .patch strategy was abandoned (different strategy from the header-count
  fix): conandata `patches: {}`, patch file deleted, and build() now calls
  `_fix_catch_urng()` which replaces the single line
  `typedef std::ptrdiff_t result_type;` -> `typedef unsigned int result_type;`
  via replace_in_file. Already-fixed/absent anchor only logs and continues,
  so a genuine compile error would still surface.

## 3e. C-interface read/write tmpfile portability fix (2026-10-10 seventh round)

- Preflight: 9/10 ctest entries green; unit_tests binary 64/65 Catch cases pass,
  1 fails with SIGABRT at tests/unit-tests/test_c_interface.cc:147
  (the C-interface "read/write" SECTION doing a serialization round-trip).
- Root cause: that SECTION uses `FILE *fp = tmpfile()`; tmpfile hard-codes
  P_tmpdir=/tmp and ignores TMPDIR, while HarmonyOS mounts /tmp read-only
  (erofs, knowledge E002), so tmpfile returns NULL and the following
  locked_table_write/fwrite dereferences a NULL FILE* -> SIGABRT.
  Hash logic is unrelated; stress/benchmark suites are all green.
- Fix: build() now calls _fix_c_iface_tmpfile() (runtime replace_in_file,
  same strategy as the Catch URNG fix, no .patch file): tmpfile stays the
  first try; when NULL, fall back to mkstemp in TMPDIR/TMP/TEMP/. (HMBS
  injects a task-private writable TMPDIR) + fdopen("w+b"), explicit
  REQUIRE(fp != NULL) instead of crashing, unlink the fallback file after
  fclose. All assertions and value ranges untouched, no test skipped.

## 3f. ctest Exception-verdict counting fix + insert_expansion flake (2026-10-10 eighth round)

- Previous round's tmpfile fix verified EFFECTIVE: unit_tests is green this
  round (the C-interface read/write SECTION passes with the TMPDIR-aware
  mkstemp fallback). New failure domain: `insert_expansion` SEGFAULTs at
  0.42s in "Running operations", while the other 9/10 ctest entries pass.
- Flake evidence (same preflight client, identical benchmark binary between
  rounds; only test_c_interface.cc changed, which compiles into a different
  binary): round 7 insert_expansion PASSED, round 8 SEGFAULTs. The benchmark
  draws a fresh random seed every run (std::random_device, no --seed arg) and
  hammers 2M concurrent inserts into a table growing 16 slots -> ~4M slots,
  so a seed/scheduling-dependent crash in concurrent expansion fits; a
  systematic OHOS incompatibility would fail every run, and the larger
  read_insert_expansion (8M inserts with growth) passes in both rounds.
- Recipe bug fixed (different strategy from the tmpfile fix): the ctest
  verdict regex only knew Passed|Failed|Timeout|Skipped|Not Run, but a
  crashed test prints `***Exception: SegFault`, so test #9 fell through and
  the marker reported the self-contradictory executed=0/passed=0 (ctest
  itself said "90% tests passed, 1 failed"). The parser now recognizes the
  `Exception` verdict and counts it as failed in the same single pass
  (no fallbacks, no corrective branches); this log would now yield the
  truthful discovered=10 executed=10 passed=9 failed=1 skipped=0. Non-green
  still raises (no gaps claimed, no workload/seed change, no test skipped).
- Diagnostics widened: LastTest.log tail 2000 -> 8000 chars so the next round
  sees crash context above the summary footer, not just the footer.
- Next-round discriminator: green => flake confirmed; repeat SEGFAULT =>
  systematic, then dig into concurrent-expansion path with the wider log.

## 3g. Documented upstream flake: gaps for insert_expansion (2026-10-10 ninth round)

- Previous round's parser fix verified EFFECTIVE: the marker is now truthful
  (discovered=10 executed=10 passed=9 failed=1, no zeroed counts). But
  insert_expansion SEGFAULTed a second consecutive round (0.42s, then 0.52s,
  both early in "Running operations"); record is now pass -> SEGFAULT ->
  SEGFAULT on one runner with an unchanged benchmark binary.
- Root cause is UPSTREAM, confirmed by external evidence (different strategy
  from the two source-level fixes before -- this round changes result
  handling, not test sources):
  - efficient/libcuckoo#144 (open, no fix): "insert_expansion randomly
    segfaults no matter what architecture" (x86/ppc64le/aarch64 reporters;
    Debian maintainer confirms random segfaults that come and go).
  - Alpine Linux APKBUILD for libcuckoo 0.3.1 runs
    `ctest -E insert_expansion` with the comment "insert_expansion and
    read_insert_expansion tests can randomly fail", citing issue #144.
  - Our 3-round record fits the documented signature exactly (random across
    runs, crash not assertion failure), while the larger
    read_insert_expansion stays green 3/3 and unit/stress suites are green.
- Fix: keep executing the FULL 10-test suite (unlike Alpine, nothing is
  excluded -- strictly more honest), and attach a `gaps` entry
  (category test_failure, count 1 == discovered - passed) to the marker when
  -- and only when -- every test executed and the single non-passing test is
  insert_expansion with a crash (Exception) verdict. Any other pattern
  (assertion Failed, skip, missing outcome, another test, >1 failure) still
  raises. test_package re-emit accepts a non-green suite only with
  well-formed gaps whose counts cover the shortfall and whose categories are
  from the allowed set; missing/contradictory evidence still fails loudly.
- PR-body consequence (for HMBS when syncing): upstream rate is honestly 9/10
  (90%), not 100%; the one gap is the documented upstream crash above.

## 3h. test_package locked_table find API fix (2026-10-10 tenth round, new failure domain)

- Preflight: upstream suite handling verified EFFECTIVE (marker truthful 10/10/9/1
  with gaps, WARN accepting documented insert_expansion flake). New blocker is
  test_package compile: test_libcuckoo_acp.cpp:67 `locked.find(3, probe)` fails
  with "no matching member function for call to 'find' ... requires single
  argument 'key', but 2 arguments were provided".
- Root cause: consumer test wrongly assumed the concurrent-map overload
  `find(K, mapped_type&)` exists on locked_table; upstream v0.3.1 locked_table
  only has `iterator/find(const K&)` and `const_iterator/find(const K&) const`.
  Previous three rounds touched tmpfile/ctest-counter/gaps logic, never this
  file, so a different fix route is required (second strategy cycle rule).
- Fix: check 8 now uses iterator form (`auto it = locked.find(3);
  it != locked.end() && it->second == "libcuckoo"`); other 9 checks, count (10),
  and marker logic untouched, no assertion deleted or skipped.

## 4. 待真机预检回填（evidence 轮）

- `conan create` 全量日志：上游 10/10 执行与通过数、消费者 10/10。
- 特别关注：Catch 单测在 clang 15 + libc++ 下编译是否一次通过；
  stress 默认参数（2^25 键、16 线程、10 秒）内存/耗时是否超限；
  universal-benchmark 中 `insert_expansion`（13M ops）耗时。
- 数字回填到 `.hmbs/pr-body.md` 验证结果与两张对比表后，再走提交。

## 5. 验证命令（HMBS 后台执行，本轮不手动运行）

```text
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 断言日志含：HMBS_UPSTREAM_TEST_RESULT（10/10/10/0/0）与
# HMBS_TEST_PACKAGE_RESULT（discovered=10/passedCount=10）
```
