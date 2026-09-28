# ruli 0.36 适配笔记

## 编译环境
- 构建系统: makefile（裸递归 Makefile，无 configure / 无 automake / 无 CMake）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- 构建主机: B 机（HarmonyOS aarch64，worktree `~/qzy/主理-33-ruli-0.36`，CONAN_HOME `~/tmp/ch/home-z23-ruli`）
- 状态: built（conan-verify 全绿，未 upload）
- 源码: `https://download.savannah.nongnu.org/releases/ruli/ruli_0.36.orig.tar.gz`
  sha256 `11d32def5b514748fbd9ea8c88049ae99e1bb358efc74eb91a4d268a3999dbfa`
  （本轮 `curl` 实取 HTTP 200 / 128290 字节后 `sha256sum` 复算，
  证据 `~/tmp/uc2/z33-ruli/ruli_0.36.orig.tar.gz`；与框架 `.tarball-sha256` 及
  上一棒 `~/tmp/uc2/z23-ruli/upstream/` 副本三向一致）

## 编译步骤

配方不跑 configure，`build()` 只调一次 make（`-j1`，R9）：

```
make -C <src>/src -j1 \
     CC=<resolved clang> \
     OOP_INCLUDE_DIR=<liboop>/include \
     OOP_LIB_DIR=<liboop>/lib \
     CFLAGS='-O2 -pipe -Wall -g -shared -D_REENTRANT -I. -I<liboop>/include' \
     LDFLAGS='-L<liboop>/lib' \
     libruli.a
```

`package()` 不调 `make install`，直接 stage `src/*.h` / `libruli.a`（或
`libruli.so.4` + `libruli.so`）/ `doc/man/*.3` / `COPYING`。原因见下"最终方案"第 4 条。

## 上游台账纠正（接手前必须知道的三条）

1. **依赖面不是空的。** 任务书与交接包写"仅 libc/pthread、`requirements()` 预期为空"，
   实为 **liboop 硬依赖**：
   - `src/ruli_mem.c` 的 `ruli_mem_malloc/realloc/free` 直接转调 `oop_malloc/oop_realloc/oop_free`
   - `src/ruli_sync.c` 用 `oop_sys_new/oop_sys_source/oop_sys_run/oop_sys_delete` 跑同步查询事件循环
   - `src/ruli_fsm.c` 到处调 `oop_source` 的 `on_fd()/on_time()/cancel_*()` 虚表
   - `src/Makefile` 链接行写死 `-loop`
   - **公开头文件也吃它**：`ruli.h → ruli_res.h → ruli_oop.h → #include <oop.h>`
   ⇒ 配方 `self.requires("liboop/1.0.1", transitive_headers=True, transitive_libs=True)`。
   `transitive_headers` 不是可选项：不给它，任何 `#include <ruli.h>` 的消费者都编不过。
   制品仓实测（2026-09-25 审计整改后的正式证据，见上方依赖表旁的 W0 要点）：
   全新空 `CONAN_HOME` 下 `conan download liboop/1.0.1@ --only-recipe -r ohpcd` 打出
   `Downloading recipe 'liboop/1.0.1#31ba5328bca52e3b6b4cd9976971e5c8'`（revision 与申报值
   逐字符一致），同轮对照 `zlib/1.3.1@` / `ncurses/6.5@` 各出一行 `Downloading recipe`，
   `conan install --requires=liboop/1.0.1 --build=never -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`
   在空缓存下真从 ohpcd 取回二进制包 `21b17f8b2bc0e9511e276e3d57a23893067cefe5`
   ⇒ 证据 `~/tmp/uc2/z33-ruli/w0-liboop-publication.log`，W0/R36 满足。
   （早先此处引的是 `probe-liboop.out` / `probe-ncu.out`，其形态为
   `Skip recipe ... already in cache` ⇒ 属缓存命中的**假成功**，不足以证远端可取，已降级为参考。）
   OHOS 二进制的**内容面**另有 `--deployer=full_deploy` 一轮佐证：只有 `include/oop.h` +
   `lib/liboop.a`，静态。
2. **"没有 `INSTALL = install` 程序变量 ⇒ §12.77 M13 不适用"复核通过**：`src/Makefile`
   的 install 目标用裸 `mkdir -p` / `cp` / `ln -s`，确实没有可覆写的 install 程序变量。
3. **上游 C 构建面确实 0 测试目标**，但不是"automake 空 check"而是**根本没定义** `check`/`test`
   规则（裸 Makefile 没有隐式 check）。⚠ 2026-09-25 审计整改补充：这句话的口径**只覆盖 C 构建面**。
   上游发布包里另有 **1 条真注册到测试运行器的用例** `perl/RULI/t/RULI.t`
   （`Test::More tests => 12`，由 `perl/RULI/Makefile.PL` 经 ExtUtils::MakeMaker 注册），
   连同 `php/ruli/tests/001.phpt`、`guile/ruli-test.scm`、`lua/test.lua` 全在语言绑定生态里，
   本配方一行都不构建。逐条审计与不构建/不执行的三条技术理由见
   `test_package/MANIFEST.yml`（`top_level_files` 与 `scan_result` 已按此更正）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 在下载+解压+建骨架之后崩掉，`.build-context-ruli-0.36` 没写出来 | **框架缺陷**：`scripts/ohc/check_env.py:33` 的 `except` 少绑 `as e`，`_check_cmd()` 遇到"路径解析得到但文件不存在"的命令（本机 `automake` 未装）就抛 `NameError: name 'e' is not defined` | **不改 `scripts/`**（框架改动须单独 PR）。init-build 的有用产出（下载/解压/骨架/manifest/notes）已全部落盘，`.build-context` 只是给"手工编译段"用的变量文件，本次直接按 Makefile 手写命令行覆写变量即可 ⇒ 后续只用 `conan-verify`/`finish`，不再碰 init-build |
| 2 | `recipe-search ruli` 与 `recipe-search oop` 都"无相似配方" | 裸 Makefile + liboop 组合在 6173 条语料里无同类 | 首稿按 `templates/conanfile-makefile.py.tmpl` 骨架 + 同仓 `archives/l/liboop/1.0.1`（E092 编译器回退、HMBS 标记、MANIFEST 形状）落地 |
| 3 | G2 第 1 轮 FAIL：`test_ruli.c:84: error: expected expression` | 我自己的测试写错：`#define FAIL(name, fmt, ...)` 在 `__VA_ARGS__` 为空时展开成 `printf(..., (name), )`，C99 不允许空 `__VA_ARGS__`，而上游/本次编译都没开 GNU 的 `, ##__VA_ARGS__` | 把宏换成真函数 `failf(const char *name, const char *fmt, ...)`（`stdarg`），55 处调用一并改名。**不是平台问题，不改配置绕** |
| 4 | G2 第 2 轮 FAIL：`CHECK-FAIL: addr_parse_snprint \| IPv6 snprint gave '2001:db8:0:0:0:0:0:1a'` | **上游行为，不是缺陷**：`ruli_in_snprint` 对 v6 走自家 `ruli_inet6_snprint()` 而不是 `inet_ntop(3)`，不折叠零段 | 断言改成有内容的等价性：snprint 出来的拼写必须能被 `ruli_addr_parse` 解回 PF_INET6 且 16 个八位组逐位相同（比钉死字符串更强） |
| 5 | G2 第 2 轮 FAIL：`negative answer carried a record list` | `ruli_sync_srv_list()` 在否定答复下返回的是**非 NULL 的空表**（`ruli_search_srv_answer_list`），不是 NULL | 断言改成"表存在则 `ruli_list_size()==0`" |
| 6 | G2 第 2 轮 FAIL：`sync_query_roundtrip` 拿 `www.baidu.com` 做正向解析时 `ruli_sync_query()` 直接返回 NULL | 我用错了 API：`ruli_sync_query(txt_service, ...)` 的 service 不能为空串（要拼 `_service._domain`），空 service 时 submit 被拒。同轮另一条 `srv_code=13(FALL_QUERY) rcode=-1` 也说明单发 UDP 查询本身有丢包抖动 | 正向解析改为 `ruli_getaddrinfo("127.0.0.1","80",AI_NUMERICHOST,...)`（`ruli_getaddrinfo.c` 明写"Can't SRV records for numeric hosts"→ 短路给 libc），加 `ruli_getaddrinfo_setoptions/getoptions` 标志位回环 ⇒ **确定性、不吃网络**；网络项只保留 NXDOMAIN 一条，并加 `SYNC_ATTEMPTS=3` 重试（`ruli_search_res_new(source, retry=2, timeout=10)` 已保证单次尝试有界），全部尝试都拿不到答复才 CHECK-SKIP 并把 `srv_code/rcode` 当证据打出来 |
| 7 | G2 第 3 轮 **PASS**（12/12，0 skip，0 fail，两次执行结果一致） | — | — |

### 上游编译标志的两个坑（本轮用命令行变量解决，未打补丁）

- `src/Makefile` 写死 `CC = gcc`，目标机 **没有 `gcc`**（`command -v gcc` 空；clang/ar/make/ld/lld 都在 `/data/service/hnp/bin`）
- `CFLAGS = $(WARN) -Werror $(FLAGS)`，`WARN` 是 2002 年的
  `-pedantic -ansi -Wshadow -Wpointer-arith -Wcast-qual -Wcast-align -Wwrite-strings -Wredundant-decls`
  ⇒ clang 15 下任何一条诊断都直接变编译错误

GNU make 对**命令行变量**的规则是"命令行值优先于 makefile 里的 `=` 赋值，且值本身会被再次展开"，
所以 `make 'CFLAGS=...'` 就能整体替换含 `-Werror` 的那行，`make CC=<clang>` 就能顶掉 `CC = gcc`，
**一个源码补丁都不需要**（`patches/` 为空，`patches_applied: []`）。
代价：`-pedantic -ansi` 也一并去掉了 —— 记录在此备查；保留的是 `-O2 -pipe -Wall -g -shared
-D_REENTRANT -I. -I<oop>`（`-shared` 必须留，因为上游的 libruli.so 链接步复用同一个 `CFLAGS`）。

顺带实测通过、因此**不需要**改动的面：`-Wl,-soname,libruli.so.4`、`-Wl,--version-script,libruli.ver`
（`HIDDEN{...}; libruli4{*;}` 这套 version script OHOS 的 lld 吃得下）、`-loop`、`-ldl`
（三条都在 `~/tmp/uc2/z33-ruli/probe/` 用最小 .c 单独验过：`-ldl` RC=0、version-script RC=0），
以及 Makefile 里硬编码的小写 `ar`（`/data/service/hnp/bin/ar` 在 profile buildenv 的 PATH 里）。

## 源码修改

**无。** `archives/r/ruli/0.36/patches/` 为空，全部适配都发生在 make 命令行变量上（R1 参数最少化）。

`package()` 不走 `make install` 的理由（写清楚免得被当成偷懒）：
上游 install 目标无条件做三件与本包选项无关的事 —— `mkdir -p` 三个目录、`cp *.h`、
以及 `cd $(INSTALL_LIB_DIR) && ln -s libruli.so.4 libruli.so`。
`shared=False`（默认）时根本不该建 `libruli.so` 符号链接，而 HMDFS 上软链接只能
`rm -f && ln -s`（S1）；`man3` 目录也只有一个 `ruli.3`。直接 stage 更可控，
shared=True 分支里补符号链接时用 `os.path.islink` 先删再建，失败则退回实拷贝。

## 依赖版本

| 依赖 | 版本 | 形态 | 来源 |
|---|---|---|---|
| liboop | 1.0.1 | `include/oop.h` + `lib/liboop.a`（静态） | 制品仓 ohpcd，revision `31ba5328bca52e3b6b4cd9976971e5c8`；本仓归档 `archives/l/liboop/1.0.1`；**W0 精确制品可取性证据**（配方生成后补跑）`~/tmp/uc2/z33-ruli/w0-liboop-publication.log`，设备绝对路径 `/storage/Users/currentUser/tmp/uc2/z33-ruli/w0-liboop-publication.log`，取证脚本同目录 `w0-liboop.sh`（可重跑） |
| libc/pthread | — | 系统 | 未使用 pthread（`grep pthread src/*.c *.h` 零命中，事件循环由 liboop 的 select 提供） |

**liboop/1.0.1 的 W0 证据要点**（上述日志内的判据行，不认 rc 只认行）：
全新 `CONAN_HOME=$HOME/tmp/ch/home-z33-w0`（只从 `home-ruli` 拷 `remotes.json`，
下载前先查本 home → `ERROR: Recipe 'liboop/1.0.1' not found`，排除缓存命中）后：

- recipe 侧：`Downloading recipe 'liboop/1.0.1#31ba5328bca52e3b6b4cd9976971e5c8'` —— 与本文件
  上方与本表申报的 revision 逐字符一致；
- 同轮对照包：`zlib/1.3.1`、`ncurses/6.5` 同一轮各出一行 `Downloading recipe`（缺对照则
  "已发布/未发布"结论不成立，这是仓内既定口径）；
- 二进制侧：`conan install --requires=liboop/1.0.1 --build=never
  -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` → `... 21b17f8b2bc0e9511e276e3d57a23893067cefe5
  #8cbb601ed04667e6842474faae77c6e1 - Download (ohpcd)` + `Downloading binary packages` +
  `Package installed` + `Install finished successfully` ⇒ **OHOS/armv8/clang15 的精确制品在
  远端确可取得，且禁用了任何通配 `conan list` 判据**；
- 两条负面结果如实记录，不掩盖：① 任务书建议的 `--requires=liboop/1.0.1@ohpcd/stable`
  报 `Unable to find ... in remotes` —— 已核实是**参考名形态不符**而非发布缺口
  （`archives/l/liboop/1.0.1/conanfile.py` 只声明 `name = "liboop"` / `version = "1.0.1"`，
  无 user/channel，配方实际 `self.requires("liboop/1.0.1")` 走的正是上面那条成功的探测）；
  ② 反证对照组 `bogus-nonexistent-pkg/9.9.9@` 报的是
  `error:system acceleration policy not enabled`，与本文件 §"判依赖是否已发布" 的既有结论一致：
  该报错文案不能单独当"未发布"判据 ⇒ 本轮只对**目标包**用正向 `Downloading recipe` 行下结论。

早先记在案的两条（`probe-liboop.out` / `probe-ncu.out`）形态是
`Skip recipe ... already in cache` —— 属**假成功**（缓存命中，不证明远端可取），
故上方新日志才是 W0 的正式证据；本文件此前把它当 W0 满足依据，已更正。

`src/` 里 20 个 .c 全进 `LIBOBJ`；未使用 `resolv.h` / `__res_*`（DNS 报文是 ruli 自己实现的）。

## 验证结果

判决行原文（`~/tmp/uc2/z33-ruli/03-conan-verify-r3.log`，`VERIFY_RC=0`）：

```
  ✅   G1: PASS
  ✅   G2: PASS
  ✅   G3: PASS
  ✅   G4: PASS
✅ 配方验证通过: ruli 0.36
VERIFY_RC=0
```

`reports/conan-verify-report.md`：**Verdict: PASS**（G0/G1/G2/G3/G4 PASS；
L2/L4/L5 `跳过（无 cache 路径）` —— 纯库包无 bin/ 时的框架预期，不是失败也不是可执行证据）。

消费者测试（`archives/r/ruli/0.36/reports/conan-create.log`，
副本 `~/tmp/uc2/z33-ruli/03-conan-create-r3.log`）：

```
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "command": "./test_ruli",
 "discovered": 12, "passedCount": 12, "skippedCount": 0, "failedCount": 0,
 "network_dependent_checks": 1, "skip_reasons": []}
ruli consumer test_package passed (12/12 checks)
```

`main()` 在 conanrun 环境与直调两种执行方式下各跑一遍，两遍都是 `SUMMARY ok=12 skipped=0 failed=0`。

真发出去的那一条 DNS 查询走的是 ruli 自己的路径（resolv.conf 解析 → UDP/53 →
`ruli_dname_encode` 造问 → `ruli_parse_*` 解答），拿回 `rcode=RULI_RCODE_NAMEERROR(3)`。

### W3 本地 CI（`ci/conan/build_and_test.sh`，finish 步骤 [5/10]）判决行原文

`archives/r/ruli/0.36/reports/w3-local-ci.log`（564 行，与 `conan-create.log` md5 不同：
`92ff164c…` vs `378724aa…`，mtime 01:50:40 晚于 conan-create 的 01:49:24）：

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
[step] Running conan create (output logged to .../.ci_logs/conan_build_ruli_0.36.log)...
SUMMARY ok=11 skipped=1 failed=0 discovered=12        （两次执行各一行）
[ok] ruli/0.36 — conan create passed
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[step] L1e: Destructive negative test (R34)...
[ok] L1e: Negative test confirmed — test genuinely depends on ruli
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
  Total:   1
[step] All packages built and tested successfully ✅
[step] Pre-download: conandata.yml 已还原为官方 URL
```

`L2_RESULT=skip: no bin/ dir` 是纯库包的框架预期（无命令行产物可跑 `--version`），
既不是失败，也**不能**反过来当"可执行证据"。
`L1e` 的破坏性反向验证通过，是 R34"测试确实依赖被测包"的机器证据。
`.ci-result.json` 由 finish 自己写入（`exit_code: 0`、`integrity_hash`、
`log_sha256: c6917596e1e104fda552019f917831571364a2ed4eb2cca6fd6bd76d171186de`），未手工碰过。

## 测试数字五维账本

| 维度 | 数值 | 口径与证据 |
|---|---|---|
| 上游测试静态总数 | **12**（2026-09-25 审计整改：本行原写 **0**，属漏记，已更正） | 唯一来源 = 上游**已注册**用例 `perl/RULI/t/RULI.t` 的 `use Test::More tests => 12;`（全文 74 行，第 6 行给出 plan=12，第 7 行 `BEGIN { use_ok(...) }`；11 处 `ok()` + 1 处 `use_ok()` 正好 12 条，与 plan 逐字一致）。它由同目录 `perl/RULI/Makefile.PL`（ExtUtils::MakeMaker）注册进 `make test`，文件头自述 "Before `make install' is performed this script should be runnable with `make test'" ⇒ 是正式注册用例，不是散落脚本。**原句「无 tests/test 目录」是错的**：全 tarball 确有 `perl/RULI/t/` 这一个 `t/` 目录（正是本文件 `MANIFEST.yml` 的 `scanned_for` 第 6 项自列要扫的目录名），无的只是顶层 `tests/`、`test/`、`spec/`。C 构建面一侧仍为 0 命中：185 条目 tarball 全扫，8 个 Makefile 无 `check:`/`test:`/`check-local:`/`TESTS`/`check_PROGRAMS`；无 gtest/ctest/pytest/DejaGnu/CUnit 注册。逐条明细与不构建/不执行理由见 `test_package/MANIFEST.yml` 的 `top_level_files` + `scan_result` |
| 上游测试可执行数 | **0**（不由本包构建面进入） | 上面那 12 条静态用例一条都不被本包构建或执行，三条独立技术原因：① 本配方 `build()` 只 `make -C src` 产出 `libruli.a`/`libruli.so.4`，**不构建任何语言绑定**，被测对象 `Net::RULI` 这个 XS 模块在本包内不存在；② 它需要 perl 解释器且需先 `perl Makefile.PL && make` 现造 MakeMaker 的 `test` 目标，顶层 `Makefile`（实测 565 B，`$Id: Makefile,v 1.9 2004-06-24 05:02:24 evertonm Exp $`）只有 `default`/`clean`/`install`/`dpkg`/`dpkg-clean`/`release-clean` 六个目标，`default:` 只 `$(MAKE) -C src` 与 `-C sample`（连 `tools` 都不进），全 tarball `grep -rn SUBDIRS` 与 `DIST_SUBDIRS` **零命中**，`perl` 在顶层与 src/tools/sample 四个 Makefile 中**零出现**（原稿此处写的是 `SUBDIRS = src tools sample` 与 `DIST_SUBDIRS 多列 perl`，属未经实物核验的推断，2026-09-25 第 3 轮窄复审在解包树 `~/tmp/uc2/z33-ruli-audit2/tarball/` 上否证后按实测改写；结论“不进构建面”不变）；③ 它的 `ok()` 断言的是对 `bocaaberta.com.br` 等 5 个活域名真发 SRV/SMTP/HTTP 查询能否拿到非空应答，非确定且无回归基线。⇒ 与已逐条判 `is_test:false` 的 `guile/ruli-test.scm`、`lua/test.lua`、`php/ruli/tests/001.phpt` **同类同级**。就 C 构建面而言 `make check` 仍是**未定义规则**（裸 Makefile，连 automake 的隐式空 check 都没有），执行即 "No rule to make target 'check'" ⇒ `upstream_test_in_build: false`，`build()` 不调任何测试目标 |
| 实测通过数 | **12（conan-verify 轮） / 11（W3 轮）** | 两局都要看：① `conan-verify` 轮（`03-conan-create-r3.log`）两次执行均 `SUMMARY ok=12 skipped=0 failed=0`，`passedCount=12`；② **W3 本地 CI 轮**（`reports/w3-local-ci.log` L516/L531）两次执行均 `SUMMARY ok=11 skipped=1 failed=0`，`passedCount=11`。差异**只**来自唯一联网项 `sync_query_nxdomain`：W3 那一轮三次尝试（每次走 `ruli_search_res_new(source, retry=2, timeout=10)`）都没拿到答复，最后一次 `srv_code=13(FALL_QUERY) rcode=-1` → 按设计记 CHECK-SKIP。11 个确定性用例两局全绿，无源码/链接差异 |
| 跳过数 | **0（conan-verify） / 1（W3）** | `skippedCount=0` / `skippedCount=1`；W3 那 1 条的 `skip_reasons` 原文（含 attempts=3 与 srv_code/rcode 证据）已进日志。分母仍是 12，未缩 |
| 失败数 | **0** | 两局 `failedCount=0`，退出码 0；`[ok] ruli/0.36 — conan create passed`、`L1_RESULT=pass`、`Total: 1`、`All packages built and tested successfully ✅` |
| 分母 | **12 = 0（上游可执行）+ 12（消费者集成）** | 未缩分母：网络项以"重试 3 次 + 拿不到答复才 SKIP 并打印 srv_code/rcode 证据"实现，不静默丢用例。**分母纪律（更正后口径）**：上游清单口径那 12 条已如实入账（上面第一行），它进本包分母的贡献是 **0**，唯一依据是"一条都不被本包构建或执行"（三条技术理由见上面第二行）—— 既**没有**并进通过数/实测数，也**没有**为了维持 100% 而从清单里删掉；消费者 12 项的账一字未动。另注：`test_package/conanfile.py` 发的 `HMBS_UPSTREAM_TEST_RESULT status=no_tests` 标记作用域就是 C 构建面（该文件第 11-14 行原文把范围限定在 "no check / test target in Makefile, src/Makefile, tools/Makefile or sample/Makefile"），与本表"可执行数 0"同口径，不与清单口径的 12 相冲突 |

12 项消费者用例（全部真调 libruli 导出符号，见 `test_package/test_ruli.c`）：
1 `dname_encode_wire_format`、2 `dname_decode_roundtrip`（含拒绝压缩指针）、
3 `dname_encode_guards`（缓冲不足 / 257 超长单标签两个负例）、4 `dname_match`、
5 `dname_expand_pointer`（`0xC00C` 标签偏移展开 + 越界指针必拒）、
6 `qtype_qclass_tables`、7 `addr_parse_snprint`（v4/v6 逐八位组 + 回环 + 垃圾落 PF_UNSPEC）、
8 `rfc3484_sort`（global 作用域 v4+v6 按 rule 9 产出 v6 在前）、
9 `mem_and_list`（`ruli_mem_*` 实连 liboop `oop_malloc` + `ruli_malloc` 钩子确实被调 + 容器 9 个操作）、
10 `errstr_tables`、11 `sync_query_nxdomain`（**真 DNS**）、12 `getaddrinfo_dispatch`。

## 上游日志绝对路径（复核用）

- `~/tmp/uc2/z33-ruli/00-preflight.log`（preflight_check.sh，W0。**注意其覆盖面**：该轮只 9 行、
  正文写 "未找到依赖声明"，因为它跑在 `conanfile.py` 生成之前 ⇒ 对 `liboop/1.0.1` 零覆盖，
  不能当该依赖的 W0 证据；依赖发布态的正式证据见本节末尾的 `w0-liboop-publication.log`）
- `~/tmp/uc2/z33-ruli/01-recipe-search.log`
- `~/tmp/uc2/z33-ruli/02-initbuild.log`（含 check_env 崩溃完整 traceback）
- `~/tmp/uc2/z33-ruli/03-conan-verify-r1.log` + `round1-fail-g2.log`（测试宏 C99 空 `__VA_ARGS__`）
- `~/tmp/uc2/z33-ruli/03-conan-verify-r2.log` + `round2-fail-g2.log` + `03-conan-create-r2.log`（两条测试期望错 + DNS 抖动实拍）
- `~/tmp/uc2/z33-ruli/03-conan-verify-r3.log` + `03-conan-create-r3.log`（**PASS 判决**）
- worktree 内：`archives/r/ruli/0.36/reports/conan-verify-report.md`、`archives/r/ruli/0.36/reports/conan-create.log`
- 源件探针：`~/tmp/uc2/z33-ruli/probe/dl.err`（`-ldl` RC=0）、`probe/vs.err`（version-script RC=0）、
  `probe-liboop.out` / `probe-ncu.out`（**仅为参考件**：其形态是 `Skip recipe ... already in cache`
  ⇒ 缓存命中的假成功，不构成远端可取证据，见上方依赖表旁的 W0 要点）
- **W0 依赖发布态正式证据（2026-09-25 审计整改补）**：
  `~/tmp/uc2/z33-ruli/w0-liboop-publication.log`
  （设备绝对路径 `/storage/Users/currentUser/tmp/uc2/z33-ruli/w0-liboop-publication.log`，
  235 行；取证脚本 `~/tmp/uc2/z33-ruli/w0-liboop.sh`，全新 `CONAN_HOME` 起头可重跑；
  分步原始输出在同目录 `w0tmp/`）

## 已试过的失败方案

1. **`init-build` 一键起步** → 撞 `scripts/ohc/check_env.py:33` 的 `NameError`（框架 bug，本机未装 `automake` 触发）。
   没去改 `scripts/`，改为只消费它已产出的骨架，后续手动喂 make 变量。
2. **打算给 `src/Makefile` 打补丁去掉 `-Werror`、把 `ar` 改成 `$(AR)`** → 实测 GNU make 命令行变量
   即可顶掉 `CC`/`CFLAGS` 赋值，`ar` 又恰好在 buildenv PATH 里 ⇒ **补丁归零**，比打补丁更可审计。
3. **`conan install --requires=liboop/1.0.1` 不加 profile** → 直接踩到默认 profile 是
   `os=Linux / libcxx=libstdc++11 / cppstd=gnu14`，报 "Missing prebuilt package"。
   必须显式 `-pr:h=-pr:b=ci/conan/profiles/ohos-aarch64` 才命中 OHOS 二进制。
4. **`conan download "zlib/1.3.1@-:-" --only-recipe`** → `ERROR: Do not specify 'package_id' with 'only-recipe'`；
   正确写法是 `conan download <pkg>/<ver>@ --only-recipe -r ohpcd`。
5. **消费者测试里用空 service 做正向 A 查询**（`ruli_sync_query("", host, 80, 0)`）→ 恒 NULL，是 API 误用不是网络故障。
   教训已写进上面第 6 行。
6. **把 IPv6 打印钉死成 `2001:db8::1a`** → 上游 `ruli_inet6_snprint` 不折叠零段；
   钉字符串是拿"我以为的 POSIX 习惯"当判据，改成"打印→回解→逐位相同"才是真性质。

## 适用边界

- **裸 Makefile 的 C 库**（无 configure/CMake/meson）：`make VAR=...` 命令行覆写是替代源码补丁的第一选择。
  前提是目标变量在 makefile 里是 `=`/`:=` 赋值而不是 `override`；本包 `CC`、`CFLAGS`、`LDFLAGS`
  以及四个 `INSTALL_*_DIR` 都是普通赋值，全部可覆写。
  **注意 `CPPFLAGS` 是未被 makefile 赋值的**，它会从环境直接穿进去 —— 想控它得走环境而不是命令行。
- **公开头文件转包依赖**（本包 `ruli.h → ruli_oop.h → <oop.h>`）：这种包必须
  `transitive_headers=True`，否则 test_package 之外的一切消费者都编不过；只看 `.a`/`.so`
  的符号依赖来判断"要不要声明依赖"会漏掉这一面。
- **判依赖是否已发布**：`conan download <pkg>/<ver>@ --only-recipe -r ohpcd` + **同轮对照包**；
  禁通配 `conan list`。缺失包报的是 `system acceleration policy not enabled`（设备网络策略错），
  单独看它不能当"未发布"判据。⇒ 只有**目标包自己打出 `Downloading recipe` 行**才算已发布；
  `Skip recipe ... already in cache` 的 RC=0 是**假成功**（本轮第一版探针就踩了这个：它落在
  warm 的 `home-ruli` 上，看着 RC=0 却什么都没取）。正确做法：新建一次性 `CONAN_HOME`
  只拷 `remotes.json`，先 `conan list <ref> --cache` 自证 `Recipe not found`，再 download。
  二进制可取性另用 `conan install --requires=<ref> --build=never -pr:h/-pr:b=<CI profile>`
  在同一个空 home 上探（本轮拿到 `- Download (ohpcd)` + `Package installed`，
  见 `w0-liboop-publication.log`）。另注意参考名形态：`<pkg>/<ver>@user/channel` 与仓内
  实际发布的裸 `name/version` 不匹配时会报 `Unable to find ... in remotes`，
  那是**名字形态错**不是发布缺口，别据此误判依赖未适配（本轮 `liboop/1.0.1@ohpcd/stable` 实拍）。
- **需要联网的消费者用例**：把"传输层失败"和"权威否定答复"分成两个码集合判断，
  重试到预算用完才 SKIP 并打印 `srv_code/rcode` 当证据。
  这台设备的 DNS 实测可达（`/etc/resolv.conf` 有 `114.114.114.114` + `8.8.8.8`，
  UDP/53 到 8.8.8.8 可连），但**单发查询会偶发 `FALL_QUERY(13)`**，
  所以任何"发一次定生死"的写法都是 flaky 的。
- **CI 取源风险（本包口径）**：源站是 **Savannah**（`download.savannah.nongnu.org`）。
  本轮取源直连 200 成功（一次瞬时 500，重试即通），但 Savannah 既不在 GitHub 镜像改写分支、
  也不在 `build_and_test.sh` L1117-1120 的 SourceForge 处理里 ⇒ **CI 拿的是原始 URL，无镜像兜底**。
  另注意 E299：镜像改写不校验状态码，命中会拿到约 162B 的 404 HTML 导致 sha256 必败 —— 本包
  URL 未被改写，不受影响，但如果后续 CI 红在取源上，先按这个方向核。
- **B 判定 = none**。理由：本轮撞到的三类问题分别是 (a) 工具链环境（无 `gcc`、`-Werror` 在
  clang 15 下变致命）—— 属已入库的 E092/E540 家族，G2 两次失败都被 E540 命中（是**命中**不是未命中，
  故 R31 不强制出草稿）；(b) 我自己测试写错的期望；(c) 上游 ruli 自身行为（IPv6 不折叠零段、
  否定答复回空表、空 service 被拒）。**没有一条是 HarmonyOS/HongMeng 与 POSIX 实现之间的行为偏差**：
  探针清单 #13(ppoll) / #17(getaddrinfo) 同域的两个点本轮都没撞出偏差 —— ruli 的 getaddrinfo
  包装对 numeric host 明确短路给 libc，真 DNS 路径（AF_INET + UDP/53 + NAMEERROR）在设备上工作正常，
  未使用 `ppoll`（liboop 用 `select`），也未使用 raw socket / `resolv.h`。
  ⇒ 不建 `knowledge/drafts/`、不建 Issue。

---

**编译结束**: 2026-09-25 01:49
**最终状态**: built

## 路径与知识库声明（3+2 最小声明，与 PR 正文同源）

- 适配路径：路径 A（基础适配；patches/ 为空，零上游源码改动，裸 Makefile 的 CC 与 CFLAGS 用命令行变量整体覆写解决）
- 使用知识库：openharmony-compile-agent skill 与 knowledge/graph 知识图谱；本轮 G2 两次失败均**命中**既有条目 E540（shadow-ci / runner-path-prepend）与 E092 族（clang 15 下 -Werror 叠加 -pedantic -ansi 变致命），并复用 E490（conan untargz 保留 exec 位）与 autoconf/HMDFS umask 家族的复核结论
- 知识库扩展：无新增条目。理由：本轮三类问题分别是工具链环境（已被 E540/E092 覆盖）、本包消费者测试自身缺陷、上游 ruli 行为差异（ruli_inet6_snprint 不折叠零段、否定答复返回非 NULL 空表、空 txt_service 被 submit 拒）；行为探针 #13（ppoll）与 #17（getaddrinfo）均无鸿蒙特性相对 POSIX 的偏差 ⇒ B 判定 = none（命中既有条目时 R31 不强制建草稿）
- 关联 Issue：无需新建（B 判定 = none，未产生跨库新机制；【知识库扩展】类 Issue 仅随 create 建）
- 交付面与测试口径：纯库交付（libruli.so.4 与头文件，无 bin/ ⇒ W3 的 L2_RESULT=skip 属框架对纯库的预期，既非失败也不可当可执行证据）；上游**清单口径**静态测试总数如实记 **12**（唯一来源 `perl/RULI/t/RULI.t` 的 `Test::More tests => 12`，由 `perl/RULI/Makefile.PL` 注册；2026-09-25 审计整改把本行原写的 0 更正为 12，理由与三条"不构建/不执行"技术依据见「测试数字五维账本」前两行），上游**可执行数**如实记 0；本包分母 12 全部来自真调导出符号的消费者用例（未把上游 12 并进通过数，也未从清单删掉），联网项按重试 3 次加 srv_code 与 rcode 证据才记 SKIP，未缩分母

## 上游 12 条 perl 用例真实执行（2026-09-26，CIW-F3，rule4 整改）
设备装有 perl v5.42.0（aarch64-linux，/data/service/hnp/bin/perl，cc=clang）。
取上游 perl/RULI/ 原样源码（零修改），`perl Makefile.PL` 以命令行 INC/LIBS 覆写指向
conan 产物（libruli.a + liboop.a，home-ciwf3-ruli）后 make：XS 绑定编译链接成功。
`perl -Mblib t/RULI.t` 真实执行（真发 DNS，114.114.114.114 出口）：

- **结果：10/12 通过，2 失败**。
- 失败定位：ok3/ok4 = `ruli_sync_query('_http._tcp','bocaaberta.com.br')` 返回 undef
  ——该域名 NXDOMAIN（上游 2004 年测试语料已从 DNS 注销，`nslookup -type=SRV
  _http._tcp.bocaaberta.com.br` 复核为 NXDOMAIN；任何平台执行结果相同，非 OHOS 适配缺陷）。
- 语义交叉验证：uol.com.br（域名存活但无 _http._tcp SRV）返回**非 NULL 空表**，ok5/6 通过
  ——证明否定答复=空表、域名不存在=undef 的上游语义均正确落实现。
- 其余 8 条联网用例全部命中真实 SRV 记录（aol.com/kensingtonlabs.com/registro.br 等，
  含 A+AAAA 地址返回）。
- 完整输出：设备 `~/tmp/uc2/ciwf3-ruli-RULIt.log`（`ok 1..12` 逐条 + `failed 2 tests of 12`）。
- 未修改上游任何测试文件与断言（RULI.t 逐字节原样）。
