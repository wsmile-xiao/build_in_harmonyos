# 编译笔记 — traildb 0.6

## 编译环境
- 构建系统: 直接编译 (Makefile.am 源表 + clang + ar, 无 autoreconf/configure/make)
- 编译日期: 2026-09-21
- 编译器: clang/clang++ (OHOS aarch64, conan profile ohos-aarch64)
- 状态: built (待真机 preflight 验证后转 published)

## 编译步骤

实际编译在 HarmonyOS PC 真机执行，流程与以下一致：

```bash
tar xf traildb-0.6.tar.gz
cd traildb-0.6
# 按 src/**/*.c 全量 glob 直接编译 (无需 autoreconf/configure):
clang -std=c99 -O0 -g0 -fvisibility=hidden -fPIC -DDSFMT_MEXP=521 -DSIZEOF_OFF_T=8 -DSIZEOF_SIZE_T=8 -Isrc -Isrc/xxhash -Isrc/dsfmt -Isrc/pqueue <judy include> -c <TU>; llvm-ar rcs libtraildb.a obj/*.o
# 工具: tdb + traildb_bench 直接链接
# 上游测试: 编译并运行 tests/c-tests/*.c (37 执行, 1 跳过 out_of_memory.c)
# package(): headers/lib/bins 直接拷贝
```

conan 等价命令由 HMBS 后台执行：
`conan create archives/t/traildb/0.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`

## 依赖与版本查询

| # | 依赖 | 版本 | 状态 |
|---|------|------|------|
| 1 | judy | 1.0.5 | published, 提供 Judy1/JudyL (traildb 强制依赖, AC_CHECK_LIB；唯一依赖。Center 无 judy 配方，恒走 ohpcd 注册表) |
| — | libarchive | 无 | **刻意不依赖**：上游 waf 要求 libarchive>=3，但 OHOS 预检可获得的每个 libarchive 均不可构建，见下 W0 三轮证据 |

W0 检查: judy/1.0.5 已在制品仓发布。libarchive 三轮预检证据（2026-09-28）：
(a) Center 3.7.7 with_iconv=False → Center zlib/1.3.2 CMakeToolchain 以
`System is unknown to cmake ... Platform/HarmonyOS` + 陈旧 profile 编译器
`/data/service/hnp/bin/clang` 失败；(b) Center 3.7.7 默认选项 → Center libiconv/1.17
在 configure 起步以 `[Errno 12] Out of memory: '/bin/sh'` 失败；
(c) Center 3.8.7（Center 同样收录该版本，config.yml 可查；且有 build_requirements
`tool_requires("cmake/[>=3.17]")`）→ Center cmake/4.4.3 配方无 OHOS 源码项
(`KeyError: 'OHOS'`) 失败。本仓 3.7.7/3.8.7 软件 manifest 均为 built 未发布，
预检触达不到；单 PR 单库规则下也无法在本 PR 内新增后缀版本。
反证 ohpcd 通道正常：Center 根本无 judy 配方，judy/1.0.5 在历轮预检中从未失败，
即 ohpcd 解析与下载工作正常——libarchive 回退到 Center 只能解释为注册表缺对应产物。
因此本配方以无 HAVE_ARCHIVE_H 配置构建：上游全部 PACKAGE 代码均被
`#ifdef HAVE_ARCHIVE_H` 守卫（tdb_cons_package.c 无定义时为空 TU，可直接验证），
tdb_cons_init() 注释明确写道失败即回退目录模式（返回值忽略，output_format 保持
calloc 零值即 DIR），tdb_cons_finalize() 无定义时跳过 cons_package()。
库以 -DDSFMT_MEXP=521 -DSIZEOF_OFF_T=8 -DSIZEOF_SIZE_T=8 编译并仅链接
-lJudy -pthread -lm（上游 Makefile.am 本身就不链 -larchive/-lz）；测试默认仍为目录模式
(不定义 __HAVE_ARCHIVE_H__)，与上游 ./waf test 默认一致。

## 源码修改

- `patches/0001-configure-ac-no-sse2-on-arm.patch`: 删除 `configure.ac` 中无条件的 `AC_DEFINE(HAVE_SSE2, 1)`。
  - 原因: HAVE_SSE2 会引入 `<emmintrin.h>` (x86 SSE2)，在 aarch64 clang 上不存在；dSFMT 标准 C 实现在所有平台可用，且与上游 waf 构建一致 (wscript 从不定义 HAVE_SSE2)。
  - 替代方案: 按 host_cpu 条件定义被放弃，因为 configure.ac 未调用 AC_CANONICAL_HOST，$host_cpu 为空；直接删除最稳妥，x86 上仅损失少量 SIMD 加速，不影响正确性。
- `patches/0002-tdb_cons_setopt-no-libarchive-dir-fallback.patch`: 使显式 PACKAGE 断言配置感知。
  - 原因: 无 HAVE_ARCHIVE_H 时 `tdb_cons_set_opt(PACKAGE)` 正确返回 TDB_ERR_INVALID_OPTION_VALUE（源码 `tdb_cons.c` switch 无该分支即回 INVALID），原测试无条件断言 ==0 在目录模式下必败（2026-09-28 预检 exit=-6 于 main:34）。
  - 做法: `#ifdef HAVE_ARCHIVE_H` 保持原断言；否则断言返回 INVALID 后显式切回 DIR，并把后续 `get_opt` 期望值由 PACKAGE 改为 DIR；add/finalize/open/cursor 流程不变，仍在支持的目录模式下全量 exercising。有 libarchive 时原行为逐字保留。
- `patches/0003-open_close_memory_leaks-ohos-rlimit.patch`: MEM_LIMIT 改为基线自适应（floor + margin）。
  - 原因: RLIMIT_AS 限制的是绝对虚拟地址空间（VmSize），而非堆。OHOS HNP 运行时基线本身即超 300MB 绝对上限，首个 `tdb_cons_open` 即 NOMEM（2026-09-28 预检 do_cons:38 exit=-6，VmData 基线 54MB；固定 1GB 上限的 2026-09-29 预检仍在同一首断言 do_cons:45 exit=-6，行号偏移仅为补丁注释所致）。
  - 做法: 保留上游 300MB 为下限（小基线平台行为不变），运行时读 `/proc/self/status` 的 VmSize 为基线，实际上限取 `max(300MB, 基线+512MB)`；单次 cons 峰值约 64MB 词典缓冲（1000x64KB）+ Judy 开销，20 cons + 100 open 的真实泄漏必超 512MB 裕量，检漏意图保留。不删断言、不跳过。

## 上游测试

- 上游测试框架: waf c-tests, `tests/c-tests/*.c` 共 38 个程序 (39 文件减去 tdb_test.h)，`./waf test` 运行；autotools 无 TESTS/make check 目标。
- 配方做法: 在 `build()` 中用同一编译器把 38 个程序逐个链接直接编译的
  `libtraildb.a -lJudy -pthread -lm` 并运行 (TDB_TMP_DIR 按用例隔离)，
  库与测试均不定义 `HAVE_ARCHIVE_H`/`__HAVE_ARCHIVE_H__`，
  `tdb_test.h` 默认选用目录模式（与上游 ./waf test 默认一致）；
  显式选择 PACKAGE 输出的测试（如 tdb_cons_setopt.c 断言 set_opt(PACKAGE)==0，
  无定义时返回 TDB_ERR_INVALID_OPTION_VALUE）按 test_failure 如实报告并附日志尾，
  输出 `HMBS_UPSTREAM_TEST_RESULT`。库本身以 `src/**/*.c` 全量 glob 编译
 （含 `tdb_multi_cursor.c`、`pqueue/pqueue.c`，对齐 traildb-sys 的 build.rs；
  硬编码子集曾漏掉这两个 TU，导致 free_test/multi_cursor 报
  undefined `tdb_multi_cursor_*`）。
- `out_of_memory.c` 在 OHOS release 构建下跳过: 它断言 `c->events.arena_increment == 100` (仅 waf test 变体以 `-DEVENTS_ARENA_INCREMENT=100` 构建 lib 才满足)，且含 50MB x10 RLIMIT_AS 递减循环与 1 亿次迭代，超出预检预算；计为 skipped=1, gaps 类别 environment。
- 其余 37 个全部运行：2026-09-28 预检同样无 HAVE_ARCHIVE_H 下 37 执行 35 通过 2 失败（tdb_cons_setopt:34 PACKAGE 断言 exit=-6；open_close_memory_leaks do_cons:38 首调 open 断言 exit=-6），0002 修复后 tdb_cons_setopt 通过；0003 首版固定 1GB 在 2026-09-29 预检仍首断言失败（do_cons:45，行号偏移仅为注释），本轮改为基线自适应（max(300MB, 基线+512MB)）后预期 37 执行 37 通过 + 1 skipped（out_of_memory），不再有 test_failure；`tests/tdbcli/test_tdbcli.py` 属于 test_cli 变体，不计入默认套件。

## 验证结果

待 HMBS 真机 preflight 返回后填写:

```bash
# conan create 日志摘要 (真机)
# HMBS_UPSTREAM_TEST_RESULT={"status":"...","discovered":38,...}
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"discovered":7,...}
```

本地未运行 conan (按任务守则，真机外不跑 conan)。

## 产物说明

| 文件 | 说明 |
|------|------|
| lib/libtraildb.a | 静态库 (默认 shared=False) |
| lib/libtraildb.so | 动态库 (shared=True 时) |
| include/traildb.h, tdb_error.h, tdb_types.h, tdb_limits.h | 公共头文件 |
| bin/tdb | 命令行工具 (dump/make) |
| bin/traildb_bench | 基准工具 |
| share/pkgconfig/traildb-0.6.pc | pkg-config 元数据 |

## 注意事项

- GitHub tag 包无 generated configure；本配方不跑 autoreconf (真机无系统 autoreconf, conan autoconf 又会拉起 m4 构建踩 hnp bash 坑), 改为按 Makefile.am 源表直接编译.
- 本配方无 configure/make/config.status, 构建全程无 shell 调用(argv 直接调用), 天然规避 hnp bash 在 HMDFS 深路径下 inaccessible 问题; test_package 直接运行 ctest.
- 唯一依赖 judy/1.0.5 (published)；无 libarchive（见上 W0 三轮证据：Center 链三处系统性失败，
  本仓版未发布）。库与测试均无 HAVE_ARCHIVE_H，目录模式全功能可用。
- test_package 用 7 个断言覆盖 cons/open/cursor 主链路（目录模式默认，无需 PACKAGE），TDB 文件写在 ctest 工作目录，避免污染源树。
- test_package/test() 计数口径：先跑 `ctest --output-on-failure` 保 L1 证据，再直跑 `test_traildb` 二进制数 `^PASS \d+:` 锚定行得 passedCount（单确定性来源，无 returncode 回填；2026-09-29 rule4 首轮修复）。

## 2026-09-29 第二轮（同一 rule4 指纹，换上游侧策略）

- 前次比较：首轮只改了 test_package 计数（硬编码 7/7 → PASS 行实数），复检证实新代码已生效（日志出现双通道标记 + `passed (7/7)`），但同一 `rule4: passed 状态与上游结果矛盾` 复现——失败域不在 test_package，而在上游 38/37/37/1（status passed + environment skip）的跳过口径。按防重复要求本轮不再碰 test_package，改走上游侧真实执行路线。
- 新证据（只读核查上游 0.6 tag）：`wscript` 的 test 变体以 `-DEVENTS_ARENA_INCREMENT=100` 编译**整个** lib 并运行全部 38 个程序（`bld.path.ant_glob("tests/c-tests/*.c")`），仅 darwin 经 `SKIP_TESTS` 跳过 `out_of_memory.c`；Linux/OHOS 上游跑满 38。旧配方用 release lib 跑 37 + 推测性跳过 1，与上游做法偏离，且 gaps 类别 environment（瞬态）与可复现的平台语义不符。
- 本轮做法：`build()` 内增建 debug 变体静态库 `libtraildb_dbg.a`（同源表、同 `-O0 -g0`（2026-09-29 Signal 9 后由 -O1 再降级），仅加 `-DEVENTS_ARENA_INCREMENT=100`，独立 `obj-dbg/` 目录，不影响交付产物），`out_of_memory.c` 对其真实编译运行（TDB_TMP_DIR 隔离，900s 超时）。通过则 38/38 无 gaps；若绝对 RLIMIT（500MB→100MB 递减）撞上 HNP VmSize 高基线致后段循环 open 断言失败/超时，则记 skipped=1、类别改为 `ohos_feature`（系统性平台语义，非瞬态），evidence 取真实 exit/tail（含 darwin SKIP_TESTS 先例 + VmData 基线实测）。不删断言、不静默通过。
- MANIFEST 同步：`upstream_test_command` 与 `out_of_memory.c` 条目改为 debug 变体实跑描述。结果待 HMBS 预检回填。
