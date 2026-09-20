# libbfio 20170123 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64（设备原生构建与运行）
- Clang 15.0.4（`/data/service/hnp/bin/clang`，目标 `aarch64-unknown-linux-ohos`）
- Conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`，设备共享
  `CONAN_HOME=~/.conan2`（采信轮前已按 `tools/clean_conan_cache.sh` 四步清理，
  recipes/packages 两表对 libbfio 回查为空）
- 采信轮：`tools/conan_verify_round.sh libbfio 20170123`，rc=0（干净轮：
  `conan-create.log` 构建标志计数 run_make=6 / calling_build=2 / apply_patch=0）

## Verification

| Step | Command | Result |
|------|---------|--------|
| 配方验证 | `conan-verify libbfio 20170123` | exit 0，verdict=PASS — G0/G1/G2/G3 PASS；G4 报「无法找到程序包 ID」，L2/L4/L5 报「跳过（无 cache 路径）」（官方工具对库类型包的 package_id 解析形态，逐字见 `conan-verify-report.md`） |
| 本地 CI 模拟 (W3) | `build_and_test.sh libbfio/20170123` | exit 0 — L0 pass，L1 pass，L1e pass，L2 skip，L4 pass，L5 pass |
| 上游测试套件（探索树，与配方 `build()` 同一组内联适配） | `make -j1 check LOG_COMPILER=/data/service/hnp/bin/bash` | exit 0 — `# TOTAL: 2 / # PASS: 2 / # FAIL: 0` |

W3 gate detail（5 条 `*_RESULT` 逐字取自 `w3-local-ci.log`；L1e 一行为该
日志中 `[step] L1e: Destructive negative test (R34)...` / `[ok] L1e: Negative
test confirmed — …` 两行的合并摘要，非逐字）：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L1e: Destructive negative test confirmed — test genuinely depends on libbfio
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
```

Conan artifact identity（本轮采信轮的完整包引用，= 采纳验证的 attempt 证据）:

```
recipe_revision:  b12b2eb279d149153d54c674792b966e6
package_id:       6b129b068851896169fae42d399fa922d239ce8a
package_revision: d147d336706a2fbf76721d5847409cba
cache_path:       ~/.conan2/p/b/libbf72bfa705cf483/p
```

完整引用逐字：`libbfio/20170123@ohpcd/stable#b12b2eb279d149153d54c674792b966e6:6b129b068851896169fae42d399fa922d239ce8a#d147d336706a2fbf76721d5847409cba`
（`recipe_revision` 与 `package_id` 与上一轮验证一致——配方与配置未变；`package_revision`
随重建前移，差异来自 `ar` 归档内嵌的构建路径与成员时间戳）。

L1e（破坏性反向验证，R34）移走 `lib/` 与 `include/` 后消费者构建失败，
门禁确认测试真实依赖被测包，不是无库也能过的空壳。

## Test case comparison

计数单位：**automake `tests/Makefile.am` 注册的可执行测试单元**（每计 1 个
`check_PROGRAMS` 程序算 1，每计 1 个 `TESTS` 入口脚本算 1；`test_package`
消费者可执行程序另计 1，单独成行）。按此单位，上游合计 12 个单元 = 10 个
`check_PROGRAMS` 程序（tests/Makefile.am L31–L41）+ 2 个 `TESTS` 入口
（test_library.sh、test_write_functions.sh，L15–L17）。测试源全集 11 个
（10 程序 + 支持源 `bfio_test_memory.c`，无独立入口/无 main，编入 handle/pool
的 SOURCES）在说明中单独披露，不与本计数混用；`check_SCRIPTS` 的 3 个脚本
（含被两个 runner `source` 复用的 test_runner.sh）是测试支撑脚本、
不是测试注册项，亦不混入；断言/参数档位数同样不混入。

| Set | Source | Cases | PASS | FAIL | SKIP |
|-----|--------|------:|-----:|-----:|-----:|
| Upstream | tests/Makefile.am `check_PROGRAMS` 10 + `TESTS` 2 | 12 | 12 | 0 | 0 |
| HarmonyOS-specific (test_package) | test.c（test_bfio） | 1 | 1 | 0 | 0 |
| **Total** | | **13** | **13** | **0** | **0** |

- Upstream 12/12 全部真实执行、无跳过、无未执行：
  - `TESTS` 2 个入口：设备原生 `make check` 实跑，`# TOTAL: 2 / # PASS: 2 /
    # FAIL: 0`（`test_library.sh` 内驱动 error、support、handle、pool 4 个程序；
    `test_write_functions.sh` 内驱动 handle_write、pool_write 2 个程序，
    写测试按官方参数形态 0 与 1000 两档）。
  - `check_PROGRAMS` 10 个程序：6 个由上述 runner 驱动实跑；其余 4 个
    （handle_read、handle_seek、pool_read、pool_seek）在 20170123 的
    `tests/*.sh` 中没有任何引用（`make check` 只编译不执行），按
    `test_library.sh` 的 `run_test_with_input` 同一调用约定补跑，
    10 个程序逐个 rc=0。
  - 支持源 `bfio_test_memory.c` 无独立执行形态，其失败注入功能随所编入的
    handle/pool 两程序实跑覆盖。
  - 执行形态（用 automake `LOG_COMPILER` 指定设备可用 bash、源码目录名与
    上游 `test_write_functions.sh` 的 TEST_PREFIX 缺陷）与逐字记录见
    [upstream-tests.md](upstream-tests.md)。
- HarmonyOS-specific 1/1：消费者 `test_bfio` 在 W3 test_package 中实跑，
  14 项 CHECK 断言全部 `ok`，rc=0（覆盖面含对上游注入源错误路径的
  正常路径对照）：
  文件创建/写入、get_version、file_initialize、file_set_name、handle_open、
  get_size、读字节数、顺序读内容比对、SEEK_SET 定位、seek 后读取与内容、
  handle_close。
- L2 skip 为库类型包口径（无可执行 bin/ 目录），非未执行失败。

## Consistency

- test_package/MANIFEST.yml：`upstream_tests` 12 条（10 程序 + 2 入口脚本）、
  `test_package_tests` 1 条、`assertion_count: 14` — 与本表及 PR 正文同源同单位。
- notes.md「上游测试」节：12 个测试单元、12/12、消费者 1 程序 14 项 — 与本表一致。
- reports/upstream-tests.md：N=12 的四口径候选表与差额归因、逐字执行记录 — 与本表一致。
- manifest.yaml：不含计数（无冲突）。
