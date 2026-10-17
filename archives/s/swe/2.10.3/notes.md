# swe 2.10.3 — HarmonyOS PC 适配笔记

## 概述

swe（Swiss Ephemeris，瑞士星历）是 Astrodienst 开发的高精度天文历算 C 库，
C99，plain Makefile 构建。上游仓库：https://github.com/aloistr/swisseph，
tag v2.10.3final（即 2.10.3 正式版，Swiss Ephemeris 3.0 之前的最后一个 2.10.x），
双许可 AGPL-3.0 / Swiss Ephemeris Professional License。

源码归档：`https://github.com/aloistr/swisseph/archive/refs/tags/v2.10.3final.tar.gz`
（359 MiB，根目录 swisseph-2.10.3final，共 466 条目，含 261 个 ephe/ 星历数据文件），
sha256 = 032a71d18cff92c9bf960020abda28d44c8f0c678072dcbab561e9aeb0399fbc
（2026-09-25 本机下载实测，与 FreeBSD ports 记录一致）。

## 适配策略

- 构建系统：上游 plain Makefile，无 configure。配方用 `self.run("make ...")`
  直接驱动（树内 zlib/1.3.1 同款做法）。
- R33：编译器取自 Conan conf `tools.build:compiler_executables:c`，以 make
  命令行覆盖（`CC=... CFLAGS="-O2 -fPIC -Wall"`）传入，覆盖 Makefile 内硬编码
  的 `CC=cc`；从不裸用 shell 环境变量。
- 只构建可移植目标：`libswe.a`、`libswe.so`、`swetest`、`swemini`。
  刻意跳过全静态 `swetests`（`-Wl,-Bstatic` 链接组在 OHOS loader 下不可移植）。
- 上游 Makefile 按 `uname` 区分 Darwin/Linux；OHOS 走 Linux 分支
  （`-shared` → libswe.so，`-lm -ldl`），无需补丁。
- `-j1` 构建（HMDFS jobserver 约束）。
- 零 Conan 依赖：libswe 只需系统 libm（R32 口径 `in ("Linux", "OHOS")` 追加）。
- 默认静态（shared=False，免 .so 签名麻烦）；shared=True 时保留 .so。
- 无 patches/ 文件：swetest.c 中未声明的 `spmoon` 在配方 `build()` 内
  直接改写为复用 `sastno`（回退上游后续提交 c353e6f 的做法），修复 clang
  下 `use of undeclared identifier 'spmoon'` 硬错误；上一轮的独立 .patch
  文件因 unified-diff hunk 行数与解析器不兼容被真机拒绝，本轮改用
  `replace_in_file` 免 hunk 方案；库源码本身无其他改动。
- 不打包可执行文件（swetest/swemini 仅构建期验证用），纯库包，无需 commands.json。
- 2026-09-25 真机轮：swetest 动态链接报 `Error relocating ... symbol not found`
  （swe_sol_eclipse_when_loc / swe_lun_occult_* / swe_heliacal_ut /
  swe_nod_aps / swe_d2l / swe_orbit_max_min_true_distance，分别定义于
  swecl.c / swehel.c / swephlib.c，均在上游 SWEOBJ 内，库本身并不缺文件）。
  根因是上游 `swetest: ... -L. -lswe` 在 .a/.so 并存时优先选 .so，使冒烟
  依赖 loader 路径与 .so 全符号导出；叠加 conan 构建目录复用时 make 增量
  易复用陈旧 .o/.so。修复：build() 先 `make clean`（失败忽略），先编
  `libswe.a/libswe.so + swetest.o/swemini.o`，经 `nm -g` 校验 7 个关键符号
  后，再以显式 `./libswe.a` 静态直链 swetest/swemini，不再走 `-lswe`。

## 上游测试审计

- 上游测试 = setest/ 目录 C 专用 harness：`suite_01..suite_10` 共 10 个测试套件
  （calc / fixstar / misc / ayanamsa / date_time / houses / apsides /
  eclipses / rise / solcross），顶层 `make test` 即 `cd setest && make && ./setest t`。
- 口径：upstream_test_total = 10，upstream_test_count_method = auto
  （单一自研框架，套件可通过 `setest/suite_*.c` 清单解析）。
- 完整 setest 需要 libcrypto（setest/Makefile `LIBS += -lcrypto`）+ m4
  （generated_tests.c 由 testsuite.m4 生成）+ perl（t/test.sh），且运行时依赖
  JPL 量级星历数据；构建沙箱内不可达，故 build() 改跑上游自带 swetest 二进制
  （Debian 同款 "swetest" test application）Moshier 解析模式（-emos，无需星历文件）
  3 个确定性用例，逐个校验退出码 0 且 stdout 含浮点历算值（防空输出假通过）。
- 计数来源单一：discovered = 源码树 suite_*.c 文件数（glob，找不到或数量不符直接失败）；
  executed/passed/failed = 3 个 smoke 的实测结果；无 findall 数数、无减法推导、
  无猜测修正分支；恒等式 passed+failed==executed 在代码内自检，违例直接抛错。
- gaps：10-3=7 个 setest 套件未在构建沙箱执行，category=environment，证据见 marker。
- 审计附注（后续轮若被要求跑完整 setest，需先解决两项硬阻塞）：
  1. setest/setest.c 大量使用 GNU C 嵌套函数（如 run() 内的 general_setup 等），
     OHOS clang 15 不支持该扩展，构建前需先做测试源码重构并如实申报测试修改。
  2. 夹具 t.fix 含 SEFLG_JPLEPH 迭代，需要 de431.eph（约 2.6 GiB，上游要求从
     JPL/Dropbox 另行下载，源码包未附带），缺失时这些迭代必然失败，只能记 gap。
- test_package：test_swe.c 10 个真实 API 断言（julday 精确值 2451545.0、version 前缀
  2.10.（上游 SE_VERSION 为 2.10.03）、Moshier 太阳黄经区间、行星名 Sun、恒星时区间、houses_ex 返回码与 Asc、
  Lahiri 章动返回码（与 swe_calc_ut 同为 ephemeris flag>=0，如 4=MOSEPH）与区间、Moshier 太阴黄经区间），二进制自发 HMBS_TEST_PACKAGE_RESULT。
- 上游 marker 双判定：passed 仅当 executed==discovered（10/10）；当前 3 个 smoke 全绿但部分覆盖时发 failed+reason+gaps 且构建成功，仅核心真失败才抛错（ifopt/2.1.4 模式）。

## 真机预检

以下由 HMBS 在真机执行 `conan create` 验证，根据失败日志在后续轮修复：

- 359 MiB 源码包下载 + 444 MiB 解压在真机耗时/磁盘是否可行。
- `uname` 在真机输出是否落入 Makefile Linux 分支（若落入未知分支需补丁）。
- swetest 3 个 smoke 在真机是否输出预期数值。
- test_swe 10 断言在真机是否通过（Moshier 计算与平台无关，预期稳定）。

## 已确认事实

- 源码归档 sha256 = 032a71d18cff92c9bf960020abda28d44c8f0c678072dcbab561e9aeb0399fbc。
- 库产物：libswe.a（必选），libswe.so（shared=True 时）；头文件为源码根全部 *.h
  （swephexp.h 主 API、swedate.h、swehouse.h、swejpl.h、sweodef.h、swedll.h 等）。
- 上游 10 个 setest 套件文件清单已在归档内核对（suite_01_calc.c … suite_10_solcross.c）。
