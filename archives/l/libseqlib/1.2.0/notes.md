# libseqlib 1.2.0 适配笔记

## 编译环境

- 构建系统: autotools (top-level configure + SUBDIRS=bwa/htslib/fermi-lite/src)
- 编译日期: 2026-09-14
- 编译器: clang/clang++ (OHOS aarch64, profile ci/conan/profiles/ohos-aarch64)
- 状态: built (pending HMBS preflight)

## 编译步骤

1. `conandata.yml` 主包为官方 tag 包 `https://github.com/walaj/SeqLib/archive/refs/tags/1.2.0.tar.gz` (sha256 见 conandata)，另 vendor 三个 pinned submodule codeload 包 (bwa@c02766e, fermi-lite@5bc90f8, htslib@49fdfbd)。
2. `source()` 解主包后分别解到 `bwa/`、`fermi-lite/`、`htslib/`，还原 `--recursive` 布局。
3. `generate()` 用 `AutotoolsDeps`/`PkgConfigDeps` 注入 `zlib/xz`，`AutotoolsToolchain` 追加 `--host=aarch64-unknown-linux-ohos`。zlib 必须用 `zlib/1.3.1.1`（见问题 7，后缀强制 ohpcd 解析）；bzip2 已禁用（见问题 6）。
4. `build()` 打 OHOS 补丁 (configure 的 umask/TMPDIR/bz2 检查降级为警告、uname+install shim、subdir LIBS 烘焙 `-L` 并去 bwa `-lrt`/htslib `-lbz2`、生成树 `ln -sf` 加固)，然后 in-source `configure`，再以 `CC/CXX/AR/RANLIB/CPPFLAGS/LDFLAGS/INCLUDES` 命令行变量直调 `make -j1`（samtools/1.21 同法，覆盖 `CC=gcc` 硬赋值的子 Makefile），最后打印 `HMBS_UPSTREAM_TEST_RESULT` (travis-compile, 1/1)。
5. `package()` 收集 `lib/libseqlib.a libbwa.a libfml.a libhts.a`，安装 `SeqLib/*.h[hpp]` 及 bundled `htslib/bwa/fermi-lite` 头文件。
6. `test_package` 用 CMake+CMakeDeps 编译 `test_seqlib.cpp` (5 个真实 API 检查)，`ctest` 运行后打印 `HMBS_TEST_PACKAGE_RESULT` (5/5) 并复发 upstream marker。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 包不含 submodule 内容，`make` 缺 `bwa/` 等 | GitHub codeload 不打包 submodule | conandata 增加 bwa/fermi-lite/htslib 三个官方 codeload 源并在 source() 定点解压 |
| 2 | 1.2.0 无 `make check`，上游测试如何认定 | SUBDIRS 均无 TESTS；Travis 仅跑 configure+make；seq_test 为独立 Boost 二进制 | 以 Travis 编译门为 upstream 断言 (1/1)，seq_test 53 例审计后说明未运行原因 |
| 3 | OHOS configure 跑 conftest 失败 | 跨环境误判为可执行 | `--host=aarch64-unknown-linux-ohos` |
| 4 | configure 写临时文件权限失败 | `umask 077` + `/tmp` 在 HMDFS 只读 | umask 改 022，TMPDIR 指到 HOME/tmp；uname/install shim |
| 5 | 链接需 zlib/lzma/bz2 | configure 检查 gzopen/lzma_code/bz2 | requirements 声明 zlib/1.3.1.1 xz/5.6.2，经 AutotoolsDeps 注入；bz2 按问题 6 禁用；zlib 版本见问题 7 |
| 6 | 真机预检 bzip2/1.0.8 CMake 失败 (2026-09-13)：conancenter 配方 CMakeToolchain 生成 CMAKE_SYSTEM_NAME=HarmonyOS（上游 CMake 无 Platform/HarmonyOS.cmake），`cmake.configure` 在 CMAKE_C_COMPILER=/data/service/hnp/bin/clang 处报错，整个依赖图 abort | bzip2 需求来自顶层 configure 的拼写式 `AC_SEARCH_LIBS([BZ2_bzBuffToBuffDecompress])`，但 `src/`+`SeqLib/` 全包零 BZ2 引用（实测 tarball 解包 grep），仅 bundled htslib 可选依赖 bz2（`#ifdef HAVE_LIBBZ2`，支持 --disable-bz2）；且 bzip2 与 zlib 同为 CMake 配方风险，而 zlib/xz 已被 htslib/1.24-r0 等 OHOS 包验证可用 | 删除 `self.requires("bzip2/1.0.8")`；顶层 configure 的 `as_fn_error "lib bz2 not found"` 降级为 WARNING 继续；bundled htslib `htslib_default_libs` 去 `-lbz2`（HAVE_LIBBZ2 未定义时编译安全）。BZ2 压缩 CRAM 不可读，与本仓 htslib/1.24-r0 --disable-bz2 一致，PR 补充说明如实声明 |
| 7 | 真机预检 zlib/1.3.1 CMake 失败 (2026-09-13 第 2 轮)：与 bzip2 同一指纹，conancenter zlib 配方 `cmake.configure()` (line 81) 在 HarmonyOS/clang 处 abort；且 bundled bwa/fermi-lite/htslib Makefile 硬赋值 `CC=gcc`/`AR=ar`（显式赋值胜过环境变量），bwa/fermi-lite 链接行不认 CPPFLAGS/LDFLAGS，bwa 在 uname=Linux 时追加 `-lrt`（OHOS 无 librt） | `zlib/1.3.1` 在 conancenter 与 ohpcd 均存在时解析走了 conancenter CMake 配方；本仓 `zlib/1.3.1.1` 为 OHOS 专用后缀版本（Makefile 构建，static+-fPIC，下游 libpng/cairo 已改指），conancenter 无此版本故强制 ohpcd 解析。子构建问题经实测上游 Makefile 确认（bwa/fermi-lite `CC=gcc`，bwa `ifeq uname Linux → LIBS+=-lrt`，htslib `htslib_default_libs` 含 `-lbz2`），本仓 samtools/1.21（同捆 htslib）已验证直调 make 之法 | `requires` 改指 `zlib/1.3.1.1`（xz/5.6.2 保持：首轮日志证实其配方来自 ohpcd autotools）；layout 改 in-source（source==build==src，samtools 同法，SUBDIRS 静态 Makefile 仅存在于源码树）；`build()` 以 `CC/CXX/AR(llvm-ar)/RANLIB/CPPFLAGS/LDFLAGS/INCLUDES` 命令行变量直调 `make -j1`（经 MAKEFLAGS 覆盖全部递归子 make，编译器取 conf `tools.build:compiler_executables`，R33）；`_patch_subdir_makefiles_for_ohos` 把 dep `-L` 烘焙进 bwa/fermi-lite LIBS、删除 bwa `-lrt` 段、htslib 默认 LIBS 去 `-lbz2`（正则已对真实上游 Makefile 驗证） |

## 上游测试审计

- `seq_test/seq_test.cpp` (41KB) 含 53 个 `BOOST_AUTO_TEST_CASE` (read_gzbed, bfc, correct_and_assemble, header_check, merge, interval_queries, json_parse_from_file, sw_alignment, read_filter_1, fermi_add_reads, seq_utils, bam_record, fermi_assemble, bam_header_*, genomic_*, small_trie, large_trie, bwa_wrapper, bam_reader, set_qualities, header_constructor, overlapping_coverage, gr_*, sequtils, bam_write, bam_record_more, bam_record_manipulation, change_bam_record, stdinput, cramin, cramin_new_ref, bamin, samin, bamout, samout, cramout, samout_to_stdout, bamout_to_stdout, bam_poly, plot_test, reset_works)。
- 1.2.0 tarball (97 files) 无 `test_data/`、无 `*.bam`；所需 `test_data/small.bam/cram/sam`、`test_ref.fa`、`test.bed.gz`、`test.vcf.gz`、`example4.json` 等不在包内，Travis 经 secure token 外部下载，OHOS 离线无法补齐。
- `seq_test/Makefile.am` 需 `libboost_unit_test_framework/system/timer/chrono` (Boost 1.73)，引入完整 Boost 会显著拉长构建且仍缺数据，故本轮不编译 seq_test。
- 结论：上游有效 CI 断言为 Travis 编译门 (1/1)，53 例 Boost 需在线数据，放弃运行，已在 PR 补充说明如实声明。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1.1 | BGZF/gzip，configure 必查（见问题 7：后缀强制 ohpcd 解析，Makefile 构建） |
| xz | 5.6.2 | liblzma，CRAM/LZMA |
| (bzip2 已禁用) | — | 见问题 6：SeqLib 自身零 BZ2 引用，bundled htslib 按 --disable-bz2 构建；本仓 htslib/1.24-r0 同例 |

## 验证结果

首轮仅完成未提交工作树，待 HMBS 真机预检：

```bash
# HMBS 后台执行 (勿在本机跑 conan)
# conan create archives/l/libseqlib/1.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 预期: HMBS_UPSTREAM_TEST_RESULT 1/1 passed, HMBS_TEST_PACKAGE_RESULT 5/5 passed
```

本地仅做静态检查：

```bash
python -m py_compile archives/l/libseqlib/1.2.0/conanfile.py archives/l/libseqlib/1.2.0/test_package/conanfile.py
# PASS
```

| 8 | 真机预检 configure 直接失败 (2026-09-13 第 3 轮)：`src/configure[159]: /data/service/hnp/bin/bash: inaccessible or not found`，`autotools.configure()` (line 154) Error 127 | profile `ohos-aarch64` 的 `[buildenv]` 注入 `CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash`；autoconf configure 经 `exec $CONFIG_SHELL` 重执行自身（上游 configure 约 159 行），该 OHOS bash 在预检构建目录不可用（classads draft + akku/guile 同指纹）。与配方逻辑无关 | `generate()` 经 `tc.environment()` 把 `CONFIG_SHELL/SHELL` 重定义为 `/bin/sh`（随 conanbuild.sh 下发，覆盖 profile）；`build()` 不再调 `Autotools.configure()`，改用 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure --disable-shared --enable-static --prefix=/ ... --host=aarch64-unknown-linux-ohos`（内联前缀对单命令必胜，`sh` 显式调用不依赖 +x，HMDFS chmod:0），`make` 同样加内联前缀与 `SHELL=/bin/sh` 变量（libtool 重 exec 走 CONFIG_SHELL，recipe shell 走 make SHELL） |
| 9 | 真机预检 configure 的 C++ 编译器检查失败 (2026-09-13 第 4 轮)：`checking whether the C++ compiler works... no`，`configure: error: C++ compiler cannot create executables` (Error 77)，伴随 `can't create temporary file /tmp/shx92owu.tmp: Read-only file system`，HMBS 平台诊断 `[readonly_tmp]` | 配方从未透传 HMBS 注入的可写 TMPDIR：`generate()` 只定义了 CONFIG_SHELL/SHELL，`build()` 无 TMPDIR 设置，autoconf conftest 与 clang 内部临时文件回退到只读 `/tmp` (erofs)，导致编译器自检失败；旧的 configure 补丁仅把 `${TMPDIR-/tmp}` 换成 `${TMPDIR:-${HOME}/tmp}`，但 TMPDIR 为空时仍不可写 | 新增 `_writable_tmpdir()` 复用 HMBS 注入 (TMPDIR/TMP/TEMP/HMBS_TMPDIR，缺失回退 $HOME/tmp)；`generate()` 经 `tc.environment()` 定义 TMPDIR/TMP/TEMP (随 conanbuild.sh 下发)；`build()` 首行同步 `os.environ`；configure/make 的 `self.run` 内联前缀追加 `TMPDIR="$TMPDIR" TMP="$TMP" TEMP="$TEMP"` (防 buildenv 聚合顺序覆盖)；test_package 同样在 build()/test() 设置可写 TMPDIR (backuppc-rsync/3.1.3.0 E002 同法，仅替换临时根目录，不跳过测试) |
| 10 | 同一指纹第 2 次修复 (2026-09-14)：上一轮仅透传 TMPDIR 后 `C++ compiler cannot create executables` (Error 77) 依旧；且本轮日志出现 GitHub 直连 `ConnectTimeout`（重试后成功，但后端判定需加镜像） | TMPDIR 不是唯一根因：configure 用的 CC/CXX 来自聚合 conanbuild.sh env，未被显式固定，且 autoconf 把真实编译错误藏进 config.log，真机摘要看不到；下载侧 GitHub 直连抖动需按 CI 规则加镜像 | 与上轮不同策略：① conandata 4 个源按 `ci/conan/build_and_test.sh get_mirrors()` 改为有序列表（gh-proxy.com 在前、官方在后，sha256 不变）；② `build()` 在 configure 前用同一 CC/CXX 做 C/C++ 最小编译链接冒烟测试（C++ 探针在 libc++ 时加 `-stdlib=libc++`），`--version` 与编译 stderr 直接进日志；③ configure 命令显式前缀 `CC/CXX`（防聚合 env 选错编译器）；④ configure 失败时自动打印 config.log 尾部 80 行再抛错；test_package 的 TMPDIR 保持 |

| 11 | 真机预检 bwa/kthread.c 编译失败 (2026-09-13 第5轮): kthread.c:76,84 error unknown type name int64_t, make[2] Error 1 导致整个 conan create abort; HMBS 平台诊断 [readonly_tmp] 为预检机框噪声与此无关 | walaj/bwa@c02766e 的 kthread.c 用 int64_t 却只 include <pthread.h>/<stdlib.h>/<limits.h>, 缺 <stdint.h>; glibc 间接引入而 x86 不报错, OHOS clang 头文件严格不含, 与 TMPDIR/只读 /tmp 无关 (上轮 TMPDIR 透传已生效, configure 已过, 失败点在 make 编译阶段); 对照 lh3/bwa 上游已含 stdint.h | 在 _patch_subdir_makefiles_for_ohos 新增 kthread.c 补丁: 若无 stdint.h 则在 #include <pthread.h> 后插入 #include <stdint.h> (OHOS 仅做最小补齐, 不跳过测试) |

| 12 | 真机预检 bwa/ksw.o 编译失败 (2026-09-13 第6轮): ksw.c:29 起 emmintrin.h 报错 This header is only meant to be used on x86 and x64 architecture, 连带 mmintrin/xmmintrin 20+ 错误致 too many errors, make[2] Error 1; 上轮 stdint 补丁已生效 (kthread.o 已过, 失败点推进到 ksw.o) | 钉住的 walaj/bwa@c02766e 早于上游 ARM 支持, ksw.c 无条件 include emmintrin.h 且用裸 SSE2 intrinsic; 同仓 bwa/0.7.19  recipe 证实 lh3/bwa v0.7.19 自带 neon_sse.h 并以 __ARM_NEON 分支解决 (CI #6613 通过) | 与上轮单头文件补齐不同策略: 新 _patch_bwa_neon_for_ohos 在构建时写入与 v0.7.19 逐字节一致的 neon_sse.h, 并把 v0.7.19 的 ARM 方案 backport 到 fork 版 ksw.c (三选 include、vextq 版 _mm_slli_si128、vmaxvq 版 __max_16/__max_8 及两处 lazy-F 收敛判断, DP 主循环数学不变, x86 路径逐字节保留); 本地以真实 walaj ksw.c 仿真验证 6 处替换命中、预处理条件配平、幂等 |

| 13 | 真机预检 bwa/bwtgap.o 编译失败 (2026-09-13 第7轮): bwtgap.h:8-10 error unknown type name u_int32_t, bwtgap.c:61 use of undeclared identifier u_int32_t, make[2] Error 1; 上轮 NEON 补丁已生效 (ksw.o 已过, 失败点推进到 bwtgap.o) | glibc sys/types.h 提供 BSD 别名 u_int32_t, OHOS 头文件无此类型; 同仓源码实测该别名仅出现在 bwa 的 4 个文件 (bwtgap.h/c、bwtindex.c、bwt_lite.c); 另预检 fermi-lite/f_ksw.c 与 bwa/ksw.c 系同一作者同族 striped-SW 代码 (6 处 SIMD 位点逐字节一致)，在 aarch64 必现同类 emmintrin 失败 | 与上轮不同策略: 新增 _ensure_u_int32_t 对 4 个文件在最后 include 后插入守卫式 typedef uint32_t u_int32_t (跨头文件重复包含安全); NEON 补丁重构为通用 _patch_ksw_neon，同时覆盖 fermi-lite/f_ksw.c (slli 锚点改用两文件共有的 LIKELY 块); 本地用钉住版本真实源码仿真验证全部命中、预处理配平、幂等 |
| 14 | 真机预检 bwa 链接失败 (2026-09-13 第8轮): `ld.lld: error: duplicate symbol: rle_auxtab` (bwtindex.o/rope.o 的 rle.h:33 定义 vs rle.o 的 rle.c:7 定义), `clang-15: error: linker command failed`, make[2] Error 1; 此时 configure 已过、ksw/bwtgap 编译已过, 失败点推进到 bwa 最终链接; HMBS 平台诊断 [readonly_tmp] 为框噪声 (configure 阶段已无 /tmp 报错, 与链接期符号冲突无关) | 钉住的 walaj/bwa@c02766e 的 bwa/rle.h:33 为 `const uint8_t rle_auxtab[8];` (无 extern, 实测钉住版本源码确认), 每个包含它的 TU (bwtindex.c/rope.c 等) 都产生一份 tentative 定义, 而 rle.c:7 是唯一的初始化定义; 老 GCC 默认 -fcommon 时多份合并而不报错, OHOS clang-15 默认 -fno-common 则报 duplicate symbol; 上游 lh3/bwa 已修复为 `extern const uint8_t rle_auxtab[8];` (实测 master 确认), 定义只留 rle.c | 与上轮头文件补齐不同策略: 新增无 OS 门控的 _patch_bwa_rle_extern, 构建时把 rle.h 该行改为 extern (上游同款修复, 幂等, 缺文件时静默跳过), rle.c 定义不动; 未加 -fcommon (掩盖式开关, 不用); 本地对钉住版本真实 rle.h 内容仿真验证替换命中且仅一处 |

## 注意事项

- 本配方保持静态库形态 (`shared=False` 默认)，避免 OHOS 系统库污染。
- `package_info.libs = ["seqlib","bwa","fml","hts"]`，消费者需同时链接四者及 zlib/lzma/bz2/pthread/m。
- Windows 检出会显示 `archives/l/libxext` 大小写碰撞为 dirty，属环境假象，与本 PR 无关；本 PR 仅含 `archives/l/libseqlib/`。

| 15 | 真机预检 bundled htslib 编译失败 (2026-09-13 第9轮): cram/cram_io.c:57 fatal error bzlib.h file not found, make[2] 在 htslib/ abort; 此时顶层 configure 已过 (libbz2 缺失仅为 WARNING), 失败点在 htslib 子 make 编译期; HMBS 平台诊断 [readonly_tmp] 为框噪声 (报错来自 preflight.sh 自身 /tmp 探测, 与配方无关, 配方 TMPDIR 透传自第4轮起已生效) | 顶层 SeqLib 的 AC_CONFIG_FILES 只覆盖 Makefile/src/*, 从不运行 bundled htslib 自带的 configure, 故 htslib/config.h 走其 Makefile 的 fallback 规则自动生成, 该规则无条件写入 HAVE_LIBBZ2=1 (实测钉住版本 htslib@49fdfbd Makefile 确认), 使 cram_io.c 的 #ifdef HAVE_LIBBZ2 分支打开并 #include <bzlib.h>; 而 OHOS 无 bzip2 依赖 (见问题6, conancenter CMake 配方在 OHOS 失败), 头文件根本不存在; 此前 HAVE_LIBBZ2 永不定义的假设错误 | 与上轮 rle.h 链接修复不同策略: _patch_subdir_makefiles_for_ohos 内把 htslib/Makefile 的 fallback 规则中 echo HAVE_LIBBZ2 行改为注释 (保留 HAVE_LIBLZMA, xz 为真实依赖), 并同步清理已存在的 htslib/config.h 中的 HAVE_LIBBZ2 行 (防 make 因文件已存在跳过规则); htslib_default_libs 去 -lbz2 保持; 未引入 bzip2 依赖 (CMake 配方 OHOS 不可用), BZ2 CRAM 不可读与 htslib/1.24-r0 --disable-bz2 一致 |
| 16 | 真机预检 src 编译失败 (2026-09-13 第10轮): SeqLib/GenomicRegionCollection.cpp:78 error no member named random_shuffle in namespace std, make[2] libseqlib_a-ReadFilter.o Error 1; HMBS 平台诊断 [readonly_tmp] 为框噪声 (preflight.sh 自身 /tmp 探测失败, 配方 TMPDIR 自第4轮已透传, 与此编译错误无关) | OHOS clang 默认 C++17+, std::random_shuffle 已在 C++17 移除; 上游 1.2.0 仅 Shuffle() 一处调用 (rand-based 两迭代器形式, 实测官方 tag 包确认), 与 TMPDIR 无关 | 新增无 OS 门控的 _patch_cxx17_random_shuffle, 构建时补 #include <random> 并把 random_shuffle(first,last) 换为 shuffle(first,last,mt19937(random_device{}())) (C++11 起有效, 均匀置换语义不变, x86/OHOS 通用, 幂等, 遍历 SeqLib+src) |
| 17 | 真机预检 src 编译失败 (2026-09-13 第11轮): ssw_cpp.cpp 经 SeqLib/ssw.h:17 报 This header is only meant to be used on x86 and x64 architecture, 连带 xmmintrin/mmintrin 20+ 错误致 too many errors, make[2] libseqlib_a-ssw_cpp.o Error 1; 上轮 random_shuffle 修复已生效 (失败点由 ReadFilter.o 推进到 ssw) | SeqLib 自带 SSW (Zhao 0.1.4, MIT) 为纯 x86 代码: SeqLib/ssw.h 与 src/ssw.c 均无条件 include emmintrin.h, ssw.c 用裸 SSE2 条纹 SW (byte/word 双路径 + Lazy-F); 与第6轮 bwa/ksw.o 同族但文件不同, 且 ssw 额外需要 srli/slli/extract/cmpeq8/cmpeq16/movemask 六个操作 (实测钉住版本 ssw.c 的 max16/max8 宏与 Lazy-F 循环确认, src/Makefile.am 确认仅 ssw.c/ssw_cpp.cpp 涉及 SSE), 故不能原样重复 ksw 的逐宏 backport | 与上轮不同策略: 共享 neon_sse.h 一次性扩展六个缺失操作 (cmpeq/movemask 用 NEON 原语, srli/slli/extract 用标量正确性优先写法), 新增 _patch_seqlib_ssw_neon_for_ohos 在 SeqLib/ 落盘扩展版垫片并把 ssw.h 改为 ARM 守卫引用, src/ssw.c 自身的 emmintrin include 在 ARM 下置空 (其 SeqLib/ssw.h 已引入垫片); x86 路径逐字节保留 |
| 18 | 真机预检 test_package 失败 (2026-09-13 第12轮): 主库已 built、上游 marker 1/1 通过, test_package cmake.configure 报 System is unknown to cmake (无 Platform/HarmonyOS) + CMAKE_CXX_COMPILER (/data/service/hnp/bin/clang++) 检查失败, Error in build() line 93 中止; 上轮 SSW 修复已生效 (失败点由 src 编译推进到 test_package) | CMakeToolchain 生成 CMAKE_SYSTEM_NAME=HarmonyOS, 上游 CMake 无此平台文件 故 try_compile 必败, generate() 里覆盖 CMAKE_CXX_COMPILER 也救不了 (与 bzip2/zlib conancenter 配方同指纹, 见问题6/7); 与前几轮主配方源码补丁不同域 | 与之前所有主配方补丁不同策略, 采纳已验证经验1 (cthreadpool 去 CMake 改直接编译): 删除 test_package/CMakeLists.txt, 改 direct-cxx——conf 字典式解析编译器 + 可写 TMPDIR 包裹, 按 dependencies cpp_info 组装 -I/-L/-l (libseqlib 优先、传递 zlib/xz 在后、system m/pthread 原样 -l, 与主配方链接一致), 直接编译 test_seqlib.cpp 并运行, 5 个断言 exit 0 门控后输出标记 |
| 19 | 真机预检 test_package 编译失败 (2026-09-13 第13轮): test_seqlib.cpp 经 SeqLib/GenomicRegion.h:13->BamHeader.h:4 报 fatal error htslib/htslib/hts.h file not found, conan Error 1; 主库 built、上轮 direct-cxx 改造已生效 (失败点由 cmake.configure 推进到 direct-cxx 编译) | package() 把 htslib/htslib/*.h 安装到 include/htslib/ (单层), 而上游 SeqLib 头写死 #include "htslib/htslib/hts.h" (双层, 源码根含 htslib/ 目录, -I 指向源码根时成立); 包内 include/htslib/htslib/hts.h 根本不存在, 与 TMPDIR/编译器无关 | 与之前源码补丁/direct-cxx 不同策略: package() 改为双层安装 include/htslib/htslib/*.h (还原源码根布局, -Iinclude 即可命中), 并保留单层 include/htslib/*.h 兼容 <htslib/hts.h> 消费者; package_info 不变 (已有 include); 本地 py_compile 通过 |
| 20 | 真机预检 test_package 编译失败 (2026-09-13 第14轮): test_seqlib.cpp 经 GenomicRegionCollection.h:311 报 fatal error SeqLib/GenomicRegionCollection.cpp file not found; 上轮 htslib 双层修复已生效 (失败点由 hts.h 推进到 .cpp) | 该头尾部 #include "SeqLib/GenomicRegionCollection.cpp" (模板实现放 .cpp), 而 package() 仅安装 *.h/*.hpp, 包内无该 .cpp, 与编译器/TMPDIR 无关; 此为同指纹第2次，需不同策略 | 与上轮头目录布局修复不同策略: package() 新增 SeqLib/*.cpp 一并安装到 include/SeqLib/ (仅消费者头可见的模板实现, 非全部 src); 本地 py_compile 通过 |
