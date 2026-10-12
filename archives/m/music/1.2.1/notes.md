# music 1.2.1 适配笔记

## 编译环境
- 构建系统: autotools（上游 release tarball 自带 `configure`，配方直接 `sh ./configure`）
- 编译日期: 2026-10-11（`conan create` 终态 rc=0 @ 05:40:12 CST，配方 revision
  `music/1.2.1#7c441a784bce5d4fe97868dec6c7ad92`（conan 修订号，非 git 对象），待验证 HEAD
  `2411ef11a44004cce14c9a0a89da2f99648b95df`，父 `fc7d3c427a304aedf6af0e931910551b184f746d`；两者均已 `git cat-file -e` 实测存在）
- 编译器: clang/clang++（经上游 `mpicc`/`mpiCC` 包装器）
- 状态: built（W3 构建验证通过；未 release/upload，故不标 published）

## 编译步骤

1. `apply_conandata_patches` 应用 3 个测试补丁（见"源码修改"）。
2. `_patch_autotools_for_ohos` / `_patch_config_guess` / `_patch_sub` 系列 / `_verify_triplet`：
   替换 config.guess、去掉 configure 的 `umask 077` 包裹，并用真机回显坐实三元组
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（rc=0）。
3. `_mpi_paths` + `_write_mpi_shim`：解析已发布 `mpich/4.0.3` 的 bin/lib/include，
   生成裸名 `mpiCC`/`mpicc` 包装器置于 PATH 首位（上游 configure 的 `mpiCC)` 分支只转发
   `MPI_CFLAGS/MPI_CXXFLAGS/MPI_LDFLAGS` 三个变量，不 splice CFLAGS，故显式展开
   `-I… -O2 -fPIC` 与 `-DHAVE_MPICH2`）。
4. `_configure_make_install`：生成并执行 `music-ohos-build.sh`
   （`export MAKEFLAGS=-j2`、`AR/RANLIB/NM/STRIP/LD` 指向 LLVM 同名工具，设备无 binutils），
   依次 `sh ./configure --prefix=… --enable-static --disable-shared --without-python`
   → `make -j2` → `make install DESTDIR=<stage>`。
5. `_run_upstream_suite`：**在 `build()` 内**（conanfile.py:67-76 第 76 行调用）用装机
   `bin/music_tests` 跑上游 sanity 套件，单条用例预算 45s、整套 1800s，结果由 `_report_suite`
   汇总上报（`ignore_errors=True`，不作为构建闸门）。执行前 `cd self.build_folder` 并
   `export PWD="$(pwd)"` / `unset CONFIG_SHELL` / `export SHELL=/bin/sh`（E386 家族两道防线，
   见"遇到的问题"第 5 条）；**不得** `cd` 进 `$TEST_OUTDIR`：runner 自身会 `rm -rf` 再 `mkdir`
   （`music_tests` L271-275），HMDFS 上删后重建是新 inode ⇒ 旧 cwd 成孤儿，子 shell `os.getcwd()`
   直接 FileNotFoundError。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make check` 注册 0 项 | `testsuite/Makefile.am` 无 `TESTS =` 且 `SUBDIRS` 受 `COND_USE_MPI` 门控 | 改用 configure 生成的 runner `bin/music_tests`（实列 14 项）在 `build()` 内执行；口径见 `test-ledger.tsv` |
| 2 | 装机版 runner 把 configure 期绝对前缀烧死在脚本里，DESTDIR 暂存时指向不存在的 package_folder | 上游 `music_tests.in` 硬编码 `@prefix@` | 补丁 0001 让前缀可用 `MUSIC_TEST_*` 覆盖，配方导出暂存树路径 |
| 3 | 上游 `run_test` 硬编码 4s 超时，共享设备上必然假超时 | HMDFS + 多方并发 | 补丁 0002 使超时可由 `MUSIC_TEST_TIMEOUT` 配置，配方设 45s |
| 4 | `loop.test` 报 `Error during launching of binary /eventdelay`（10-10 batch2 读数） | 用例引用未定义变量 `${TEST_BINARY}`，路径塌成 `/eventdelay` | 补丁 0003 改用 `${TEST_EXTRABINDIR}`/`${TEST_BINDIR}`。**本轮构建内实测已生效**：`loop.test` err=0、输出 165 行；该轮的失败签名改判为逐字行交错（见账本） |
| 5 | 01:41 那次 create 内套件 14 项全部 `unexpected exit code`（`create.log:1218` registered=14 OK=0 FAILED=0 suite_abort=14；JUnit `tests=14 failures=14`，`time` 字段全是 `xgetcwd:`） | E386 家族：conan 的 `SHELL/CONFIG_SHELL` 指向 hnp bash，在 HMDFS 构建目录内 getcwd 必挂；叠加 runner 对 `$TEST_OUTDIR` 的 `rm -rf`+`mkdir` 在 HMDFS 上造成孤儿 inode | 第 5 步的四条（`cd build_folder` + `PWD` 预置 + `unset CONFIG_SHELL` + `SHELL=/bin/sh`）；**本轮已消解**：`suite_abort=0`，`xgetcwd:` 与 `unexpected exit code` 签名 0 次出现，14 项全部取得判决 |
| 6 | 被 45s 预算止损的用例（chain/cloop/fork-collective）旧记录写成 `verdict=OK rc=137` | 判据把"无失败计数"当通过，且 toybox `timeout` 自建嵌套 pgid 使配方 `killpg` 垫片够不到 | 判据统一：`rc=137` ⇒ 无判决。**本轮构建内无一条 SIGKILL**；`fork.test` 的 collective 轮由 runner 自身超时给出 `15 (Failed: timeout)` ⇒ 记 `timeout_no_verdict`（无判定），chain/cloop 则取得真判决（FAILED） |

## 源码修改

只动测试面，不动库源码；三个补丁均在 `patches/`，由 `conandata.yml` 声明、`apply_conandata_patches` 应用（无 `strip:`，`-p1` 形态）。

| 补丁 | 改的上游文件 | 原因 | 内容 | 结果 |
|------|--------------|------|------|------|
| `0001-tests-relocatable-runner.patch`（1616 B，53 行） | `testsuite/music_tests.in` | 装机 runner 前缀不可覆盖，DESTDIR 暂存树指向不存在路径 | 前缀改为可被 `MUSIC_TEST_BINDIR/EXTRABINDIR/DATADIR` 环境变量覆盖（保留包内默认值） | runner 能对暂存树执行，包内行为不变 |
| `0002-tests-configurable-timeout.patch`（444 B，11 行） | `testsuite/sanitytests/run_test` | 4s 硬编码超时在本设备是假超时 | 超时取 `MUSIC_TEST_TIMEOUT`，缺省仍为 4 | 单条 45s 预算生效（`fork.test` collective 轮 48.67s 处即被止损） |
| `0003-tests-loop-binary-bindings.patch`（655 B，23 行） | `testsuite/sanitytests/loop.test` | L22/25/28/31 用未定义 `${TEST_BINARY}` ⇒ `Error during launching of binary /eventdelay` | 改用 `${TEST_EXTRABINDIR}`/`${TEST_BINDIR}` | 本轮构建内实测生效（err=0、165 行输出）；原"环境未就绪"分类闭环 |

未修改任何上游库源码/头文件；**未删除任何用例，未缩小分母**。

## 依赖版本

- `mpich/4.0.3`（已发布的 OHOS 二进制包，PM=gforker + simple PMI，提供 `libmpi`/`mpiexec`/`mpicc`/`mpiCC`）——配方唯一 `requires`。
- 构建期：设备 LLVM 工具链（clang/clang++ 15.0.4、llvm-ar/llvm-ranlib/llvm-nm/llvm-strip/ld.lld）、autotools（configure 自带，未跑 autoreconf）、GNU coreutils 缺失项由 toybox 承担（见注意事项）。
- 上游 `--without-python`（本平台无 python 绑定需求，且避免探测到宿主 python）。

## 验证结果

```bash
# 1) 端到端构建（设备 frp-bar.com:23847，CONAN_HOME=~/tmp/ch/home-QDR-1009-E06-music）
#    驱动 ~/tmp/uc2/QDR-1009-E06/create2.sh = gate.sh 8000 → build-slot --wait 3600 --mem 8000
#    → memcap-run.py --mb 4000 -- conan create <archive> --build=missing（MAKEFLAGS=-j2）
$ conan create . --build=missing
music/1.2.1: Exported: music/1.2.1#7c441a784bce5d4fe97868dec6c7ad92
create2 rc=0 2026-10-11 05:40:12   MEMCAP[run] peak=406MB budget=4000MB rc=0 用时457.7s   # ~/tmp/uc2/QDR-1009-E06/create2.log

# 2) 上游套件（在 build() 内执行，只汇总不拦构建）——本轮唯一分母载体
#    <build>/_testout/output.log 1088 行 sha256 89d7da54824e5bd8923bd1b42342dad1a1e2590b996b86edc1b11fbab35fce22
#    <build>/_testout/music_test_results.xml sha256 bd7736b0ad92c1aaea3c97b63bfdfa5dfd11cd5e32d492418aaaf086d2a5852b
#    <build> = ~/tmp/ch/home-QDR-1009-E06-music/p/b/music9f7b728303cd7/b/build-release
UPSTREAM SUITE (testsuite/sanitytests): registered=14 OK=8 FAILED=9 TIMEOUT=1 suite_abort=0 per_case_timeout=45s
JUnit: tests=14 failures=10 errors=0 time=86.18      # 10 = 9×exit2 + 1×exit15(timeout)，与四档口径一致
# 四档（item 级）：registered=14 / executed=14 / pass=4 / fail=9 / timeout=1 / skip=0
#   pass 项 = test_ag、launchtest、events.test、multicomm.test
# 四档（round 级）：静态 N_rounds_static=23；实际执行 18 轮 = OK 8 + FAILED 9 + TIMEOUT 1
#   未抵达 5 轮 = chain/const/launchtest.test/loop/messages 的 collective 轮
#   原因（同一）：首轮 run_test 判 FAILED 即 return 2 ⇒ .test 随即 exit，第二轮未执行
#   —— 上游 runner 早退机制，不是平台跳过：不并入"通过"、不从分母删除、不记 skip
# 逐 (item,round) 判决与分类：test-ledger.tsv（25 行）

# 3) 消费者测试（test_package/test_music.cc，mpiexec -n 2，真实调用 MUSIC::predictRank / MUSIC::Configuration 往返断言）
MUSIC_CONSUMER rank=0 failures=0 checks=13
MUSIC_CONSUMER rank=1 failures=0 checks=13        # ⇒ N_consumer=1 程序 ×13 断言 ×2 rank = 26，failures=0
```

通过率口径（勿与 runner 原子数混算；runner 条目数不等于原子用例数）：
- 消费者测试（test_package）：26/26 断言通过（1 程序 ×13 断言 ×2 rank），通过率 100%。
- 消费者测试执行面（与上面 26/26 读数同源，AGENTS §10.1）：本次 `conan create` 的
  `create2.log` Profile host（L16-25）与 Profile build（L37-46）settings 逐项全同
  （`arch=armv8` / `build_type=Release` / `compiler=clang` / `compiler.cppstd=17` /
  `compiler.libcxx=libc++` / `compiler.version=15` / `os=OHOS` / `os.version=6.0`）
  ⇒ `cross_building()` 为假 ⇒ `test_package/conanfile.py:41-47` 的交叉早退分支**未触发**
  （`create2.log` 内 `cross-building` 出现 0 次），实际走 L45-47 的 `mpiexec -n 2 test_music`
  执行面，逐 rank 打印 `MUSIC_CONSUMER rank=0 failures=0 checks=13`（L1206/L1221）与
  `MUSIC_CONSUMER rank=1 failures=0 checks=13`（L1222/L1237）⇒ 26/26 是**真实执行**读数。
- 如实限制的交叉分支（本窗未观测、属潜在路径）：若改用 host 与 build 不一致的交叉 profile
  （典型为 CI worker），`test()` 会在 `conanfile.py:42-44` 打印
  `cross-building: consumer verified by compile+link only` 后 `return`，消费者面
  **退化为 compile+link only（不执行任何断言）**。该情形下的合法申报口径只能是
  "已编译 + 已链接"，**不得**沿用 26/26 执行读数；本轮四个申报载体（本文件 /
  `manifest.yaml` / `test_package/MANIFEST.yml` / `test-ledger.tsv`）已按上述实际执行面同源，
  全部测试数字与分母未作任何改动。
- 上游套件 item 级：执行 14/14，通过 4/14 = 28.6%；失败 9；超时（无判定）1；跳过 0。
- 上游套件 round 级：静态 23 轮，执行 18 轮（OK 8 / FAILED 9 / TIMEOUT 1），未抵达 5 轮；
  按执行轮计 8/18 = 44.4%，按静态全量计 8/23 = 34.8%（两个分母都写出，避免"执行数/静态数"混算）。
- `N_static(automake TESTS)=0` 仅在该窄意义成立，声明面为 6 个 `testbin_PROGRAMS` + `test_ag`
  （内含 1 个 `TEST_CASE` / 86 条 Catch 断言）+ 12 个 `.test` + `run_test`；
  `N_rounds_static=23` 是静态展开轮次（11 个 `.test` 各 2 轮 + `multiport.test` 1 轮）。

五维账本（§10.1；五个分母分别记，任何一个都不得替代另一个）：

| 维度 | 取值 | 依据 |
|---|---|---|
| `N_static` | automake `TESTS =` 注册 **0**（窄意义）；静态声明面 **20** 个测试单元（6 `testbin_PROGRAMS` + `test_ag` + 12 `.test` + `run_test`）；静态展开轮次 `N_rounds_static` **23** | `testsuite/Makefile.am` 无 `TESTS =` 且 `SUBDIRS` 受 `COND_USE_MPI` 门控；`sanitytests/Makefile.am`、`unittests/catch/Makefile.am` 逐项 grep |
| `N_registered` | **14** | `bin/music_tests --showme-tests` 实列（本轮唯一执行分母） |
| `N_executed` | **14**（item 级，`skip=0`）；轮级 **18**（静态展开 23） | `UPSTREAM SUITE …: registered=14 OK=8 FAILED=9 TIMEOUT=1 suite_abort=0`；JUnit `tests=14 failures=10 errors=0`（10 = 9×exit2 + 1×exit15） |
| 未执行/未抵达 | item 级 **0**；轮级 **5 未达**（chain / const / launchtest.test / loop / messages 的 collective 轮） | 首轮 `run_test` 判 FAILED 即 `return 2` ⇒ `.test` 早退，属上游 runner 机制：记"未达"，不记 skip、不并入通过、不从分母删除 |
| `N_consumer` | **1** 个真实 API 消费者程序（`test_music.cc`）；`N_assertion` = 13 ×2 rank = **26**，failures=0 | `create2.log` `MUSIC_CONSUMER rank=0/1 failures=0 checks=13` |

通过率一律带分母：**执行项 4/14（=28.6%）；执行轮 8/18（=44.4%）；静态全量轮 8/23（=34.8%）；消费者 26/26（=100%）**。
上游侧未达 100%，不得把"部分成功"写成适配成功；`SIGKILL`/超时（`timeout_no_verdict` 1 项）一律不记 PASS。

## 交付物

| 文件 | 大小/行数 | sha256 | 说明 |
|------|-----------|--------|------|
| `conanfile.py` | 23032 B / 461 行 | `3e2d23c1d8a77c0f84221dc376fa83a8bcb9db2314db63b3555d3620eaf9b60b` | 设备与 Windows 两份已统一（分叉消除） |
| `conandata.yml` | 607 B / 12 行 | `3c1c29ceb8c562de5088a9d48f36d1c67a0a55be28b004013a36138b3108c2e8` | 官方 release URL + sha256 + 3 条 patch_file |
| `patches/0001..0003` | 1616 / 444 / 655 B | — | 仅测试面，逐项见"源码修改" |
| `test_package/conanfile.py` | 1868 B / 47 行 | `f8ded5e26eebf430145b3997095a041517234ac279280c72b3a77b9636624add` | `self.tested_reference_str` + mpiexec -n 2 |
| `test_package/test_music.cc` | 2717 B / 84 行 | `86eef6ea268ab8689285c1eb81c71f34270afc1841425f3554b744ee0ddf4b25` | 真实 API 消费者测试（自写 `check(bool,…)` 计数决定退出码） |
| `test-ledger.tsv` | 本 PR 新增 | 见提交后 `git show --stat` | 上游测试同源账本（唯一机器可读分母，25 行 = 23 轮 + 2 非轮条目） |

包内产物：`bin/` 实测 **11** 个可执行文件（package_folder `p/bin`，2026-10-11 05:38-05:39 落档，
逐个 `ls -l` 读数，单位字节：`contsink` 8194624、`eventcounter` 8346176、`eventgenerator` 8329792、
`eventlogger` 8313408、`eventselect` 8383040、`eventsink` 8407616、`eventsource` 8358464、
`messagesource` 8227392、`music` 2091584、`music_tests` 9915、`musicrun` 362），
与 `conanfile.py:459 self.cpp_info.bindirs = ["bin"]` 一一对应（`commands.json` 即按此 11 项如实描述，
无编造命令名、无漏项）；`lib/libmusic.a`、`lib/music-1.2.1/`（extra bindir）、
`share/music-1.2.1/`（配置与用例数据）。
`test_package/test_music`（969280 B 编译产物）与 conan 生成的 `conan{build,run}*.sh`、`metadata/`
**不入库**（提交时逐个精确路径 add，禁 `add -A`）。

## 注意事项

1. **§10 风险如实申报**：套件确实在 `build()` 内执行且本轮已取得 14 项真判决（不再是"0 执行"），
   但配方用 `ignore_errors=True`、`_report_suite` 只汇总 ⇒ **上游失败不会拦住构建**。这是本配方的
   真实限制，不粉饰为闸门。
2. **9 条 FAILED 的定性（逐字证据在账本 `note` 列）**：
   - `platform_limited_proven` 3：`const.test`、`divergence.test` 的 collective 轮、`loop.test` 的
     point-to-point 轮 ⇒ PM=gforker 各 rank 继承同一 stdout fd、写非行原子（有逐字合并行证据）；
     制品仓无 hydra 版 MPICH 可用（实测 4.0.3/5.0.1/5.0.1.1 均 `--with-pm=gforker`，5.0.1.2 写 hydra 但 Missing prebuilt）。
     这 3 条是唯一可按"平台受限 + 技术原因"逐项 `test_skipped` 候选的项，本轮仍如实记 FAILED 未升格为跳过。
   - `product_proven` 2：`cloop.test`/`contclock.test` 的 collective 轮，签名
     `Error in MUSIC library: internal error: BIFO in erroneous state before fill`，出自上游 `src/BIFO.cc:55`。
   - `product_or_platform_pending` 4（逐条给技术原因；**归因均未证实 ⇒ 一律写"未达定案"，判决保持 FAILED，不折进"平台受限"、更不折进"通过"**）：
     `chain.test`（事件 4 迟到 0.89 vs 期望 0.67，输出行完整、无交错、无 MPI 报错 ⇒ 差异在投递时序，未达"平台受限"所需的对照证据）；
     `launchtest.test`（`.test` 内 `np=3` 故意非法自连，而上游参照 `ok`/`errok` 均为空 ⇒ 参照文件与错误路径不自洽，属上游用例自相矛盾，未达定案）；
     `messages.test`（given 5 行 vs expected 10 行，各行完整、err=0 ⇒ 投递条数差异，非交错非崩溃，未达定案）；
     `multiport.test`（`internal_Allgatherv` 报 `errno=104 Connection reset by peer` ⇒ 对端 rank 先终止属后果不是根因，根因未达定案）。
     定案所需的最小复现/基线对照（同一 PM 下 1 rank 与 2 rank 各跑一次并比 `out`/`err`）本窗未取得，未达前不得升格为跳过或平台受限。
   - `timeout_no_verdict` 1：`fork.test` 的 collective 轮（45s 预算，48.67s，rc=15）⇒ 无判定，不记通过。
3. **两处旧归因被本轮推翻**（旧结论不豁免新证据）：contclock/multiport 的"np 求和 2×"（对照
   `src/setup.cc:281-289`）本轮未复现；`loop.test` 的"环境未就绪"因补丁 0003 生效而闭环。
   10-10 18:1x 的 batch2 独立运行读数与 01:41 那次 create 均降级为次级载体，不再作分母。
4. 设备无 GNU binutils 与 GNU `timeout`/`ps`；`timeout` 由配方 `_write_timeout_shim` 提供，
   其 `killpg` 对 toybox `timeout` 自建的嵌套 pgid 够不到 ⇒ 该机制只解释"历史 rc=137 止损"，
   本轮构建内的超时来自 runner 自身预算并留下 `15 (Failed: timeout)` 可读判决。
5. 静态库交付（`shared=False` 默认），`cpp_info.requires = ["mpich::mpich"]`。
6. **revision 绑定**：本文档与账本的数字绑定 rev `7c441a784bce5d4fe97868dec6c7ad92` / HEAD
   `2411ef11a440…`。文档类提交本身会再生成新 revision，但三个代码件
   （`conanfile.py` `3e2d23c1d8a7…`、`conandata.yml` `3c1c29ceb8c5…`、`test_package/conanfile.py`
   `f8ded5e26eeb…`、`test_music.cc` `86eef6ea268a…`）逐字节不变 ⇒ 构建与测试行为输入不变；
   同 SHA 重绑由下一小时的独立 W4 复审与 CI 阶段办理，本窗不自找审计角色。

---

**编译结束**: 2026-10-11 05:40:12 CST（`create2 rc=0`；本轮为读数落档与精确提交，未再起构建）
**最终状态**: built（上游套件在 `build()` 内已取得 14 项真判决；4 项未定性 + 1 项超时无判定如实保留，未提审、未建 PR）


## R38 / 包级 commands.json 补齐（2026-10-11 17:2x，本窗首次本地 PF8）

- 依据链本窗独立复核原文（非照抄审计结论）：`conanfile.py:459 self.cpp_info.bindirs = ["bin"]`
  ⇒ `ci/conan/detect_bindirs.py`（97 行 AST）对 music 配方实跑输出 `1`
  ⇒ CI L0k（`ci/conan/build_and_test.sh`：`:685-693` 取 PKG_SOFTWARE_DIR、`:694-698` 对 archives
  变更适用、`:701/:705/:706` 三取一、`:710` OR 判定）判
  `[fail] L0k: CLI tool detected but commands.json missing (R38)`；`package_type="library"`（`:29`）
  在 bindirs 非空时不豁免。
- 新增 **包级** `archives/m/music/commands.json`（不是版本级；存量 adduser 的版本级件 L0k 不认，
  历史例外不构成豁免）：`name=music` / `type=tool` / `versions."1.2.1".ref=music/1.2.1` /
  `binary=false`。`binary` 取 `false` 与 `manifest.yaml status: built` 且未 release/upload 的实况一致；
  `description` 取配方自身 `description`/`topics` 加上面 11 个真实交付物；`homepage` 与
  `conanfile.py`、`test_package/MANIFEST.yml` 同源。
- 本地 PF8 改前/改后读数（`scripts/ohc/preflight.py:517 is_cli` / `:518 cj` /
  `:519-521 "CLI 包缺 commands.json——R38 必拦"`；驱动 `~/tmp/uc2/QDR-1009-E06/pf8-1717.py`）：
  改前 `PF8_FINDINGS=1`（命中 `PF8 配方闸: CLI 包（application/bindirs 非空）缺 commands.json——R38 必拦`）、
  `CJ_EXISTS=False`、`L0K detect_bindirs='1'`、`L0K_VERDICT=FAIL_L0k_R38`；
  改后 `PF8_FINDINGS=0`、`CJ_EXISTS=True`、`CJ_NAME='music'`、`CJ_TYPE='tool'`、
  `CJ_VERSIONS=['1.2.1']`、`CJ_REF='music/1.2.1'`、`BINARY=False`、`L0K_VERDICT=PASS`。
