# parasail 2.6.2 Conan 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am + m4/；tag 归档无生成的 configure）
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- Conan: OHOS 适配版 2.29.x，profile ci/conan/profiles/ohos-aarch64
- 状态: built（2026-09-21）

## Conan 适配说明

### 自举（autoreconf）
- GitHub tag 归档（v2.6.2.tar.gz）只含 configure.ac/Makefile.am/m4/，无 configure。
- build() 内 `autoreconf -fi`（env=conanbuild）；automake/1.18 + libtool/2.5.4 经
  tool_requires 提供（设备 harmonybrew 的 automake 不进 CI worker PATH；
  /data/service/hnp/bin 只有 autoconf 家族）。
- AC_INIT 用 m4_esyscmd([./version.sh]) 提版本（egrep/awk/tr，设备与 CI 的
  /data/service/hnp/bin、/system/bin 均提供）；configure 生成头即含
  "for Pairwise Sequence Alignment Library 2.6.2"。
- LT_INIT 需要 libtool.m4：libtool/2.5.4 的 buildenv 提供 ACLOCAL_PATH；
  configure.ac 自带 AC_CONFIG_MACRO_DIR([m4])（ax_* 宏随归档）。

### E011
- 生成的 configure/Makefile.in 内嵌 `umask 077`，HMDFS 上权限异常；
  build() 内 autoreconf 后统一替换为 umask 022（yara 4.5.5 同法）。

### SIMD 后端（configure 实况，见采信轮日志）
- aarch64：NEON 经 `<arm_neon.h>` 编译探针自动启用，实测
  `checking for ARM NEON support... default`（无需 -mfpu，NEON_CFLAGS=default）。
- SSE2/SSE4.1/AVX2/AVX512/AltiVec/xgetbv：目标编译探针不通过，自动关闭。
- `-fopenmp-simd` 探测通过：EXTRA_NEON_CFLAGS="-fopenmp-simd -DSIMDE_ENABLE_OPENMP"。
- OpenMP：`checking for OpenMP flag of C compiler... -fopenmp`，HAVE_OPENMP=1。

### 选项
- shared=False 默认（--enable-static --disable-shared）；shared=True 反之。
- --without-zlib：zlib 为可选依赖（仅 aligner gz 输入），零运行期依赖口径下关闭；
  HAVE_ZLIB=0，仅 SSE2 下才需 zlib 的 tests/ssw_test 本就不可达。

### 交叉编译语义（实测）
- conan 2.29 AutotoolsToolchain 对 OHOS **不自动传 --host/--build**；
  config.guess（2024-07-27 版）对 `uname -s = HarmonyOS` 报
  "unable to guess system type" → `configure: error: cannot guess build type`
  （其编译探针还先以 `dummy.c: Permission denied` 死在 HMDFS 上）。
- 解法：generate() 里 `self.conf.define("tools.gnu:host_triplet",
  "aarch64-linux-ohos")` + build_triplet **同值**（config.sub 接受并规范化为
  aarch64-unknown-linux-ohos）⇒ configure 正常且 cross_compiling=no ⇒
  上游 `if CROSS_COMPILING else TESTS +=` 的测试面保留。

### 上游测试（首轮 create 实测，2026-09-21）
- `make check -j4`：编译 21 个 check_PROGRAMS（traceback、test_align、
  test_basic、test_gcups、test_io、test_isa、test_matrix、test_openmp、
  test_pssm、test_query、test_scatter、test_sw_dispatch、test_verify、
  test_verify_tables、test_verify_rowcols、test_verify_traces、
  test_verify_cigars、test_12、test_64、test_p29、test_p59）；
  tests/test_ssw、tests/ssw_vs_pssw、tests/ssw_test 为 SSE2 门控未编译。
- Testsuite summary：**TOTAL 3 / PASS 3 / FAIL 0 / SKIP 0 / XFAIL 0 /
  XPASS 0 / ERROR 0**（tests/test_basic、tests/test_isa、
  tests/test_verify.test）。
- test_verify.test = `tests/test_verify -f $srcdir/data/test_small_2.fasta`
  （shell 包装，跑真实比对校验）。
- N 口径：N=3（上游 autotools TESTS 注册数=运行集）；check_PROGRAMS 21 为
  「构建即检查」面（仅编译）；meson 侧 0 个注册测试；test_basic 内部 8 个
  子用例按 harness 程序级计 1。四口径不混用，归因见 PR 正文。

### test_package（鸿蒙特有测试，实测通过）
- 消费者 test.c 共 12 项断言（口径=独立判失败的 if 检查，非空守卫 4 + 功能断言 8）：
  版本函数↔版本宏一致 ×3（major/minor/patch）、版本号==2.6.2 ×1、
  parasail_nw 分发器结果非空 ×1、blosum62 "asdf"/"asdf" 得分==20 ×1、
  端位 (end_query,end_ref)==(3,3) ×1、parasail_matrix_create 非空 ×1、
  128-bit striped 16 位核结果非空 ×1、identity 矩阵自比对得分==8 ×1、
  NEON 后端结果非空 ×1、parasail_nw_striped_neon_128_16 得分==8 ×1。
- 实测输出：`test_package: all checks passed (parasail 2.6.2)`。
- `test()` 用 self.run(exe, env="conanrun") 直跑；产物落 build_folder。

### 产物（package() 实测）
- libparasail.a + libparasail.la（shared=False 默认）
- parasail_aligner、parasail_stats（bin）
- 75 个头文件（parasail.h + parasail/*.h 含 matrices/）
- parasail-1.pc（pkg-config）

## 已知限制
- zlib 关闭 ⇒ parasail_aligner 不支持 gz 压缩输入（核心库功能不受影响）。
- OpenMP 由 configure 探测；clang 15 无 libomp 时 HAVE_OPENMP=0，
  test_openmp 以 `#if defined(_OPENMP)` 守卫编译不受影响。

---
**编译结束**: 2026-09-21（首轮 conan create rc=0；make check 3/3 PASS；test_package 12/12 断言通过；后续 4 个独立干净轮同结论，L5 比对见 reports/conan-verify-supplement.md）
**最终状态**: built
