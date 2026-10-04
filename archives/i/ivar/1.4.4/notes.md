# ivar 1.4.4 — 适配工作笔记（Windows 阶段 1，2026-09-26）

任务：contrib-7550 · 分支 `feat/ivar-1.4.4`（以平台实际显示为准，提交前核对）。

## W0 依赖分析

直接依赖（制品仓均已归档，MateBook 第一步用 `conan download` 复核二进制
包，R35，禁用 `conan list`）：

| 依赖 | 版本 | 依据 |
|------|------|------|
| htslib | 1.24-r0 | configure.ac `AC_CHECK_LIB([hts])`；src 直 include `htslib/sam.h`、`htslib/bgzf.h`、`htslib/hts.h`（call_variants.cpp / ref_seq.h / call_consensus_pileup.cpp 等） |
| zlib | 1.3.1 | src 直 include `zlib.h`（call_consensus.cpp、call_variants.h、ref_seq.h）；**必须与 htslib/1.24-r0 自身依赖钉同版本**（htslib requires zlib/1.3.1, xz/5.6.2, libdeflate/1.25），避免 conan 图冲突 |

传递依赖（xz/5.6.2、libdeflate/1.25）由 htslib 包声明，**真机首验修正
（2026-09-28）：必须由本配方显式 require 并补链**——htslib/1.24-r0 是
静态库包（包内仅 libhts.a），其 package_info 不含 libdeflate/lzma，
静态 libhts.a(cram/bgzf) 引用的 libdeflate_*/lzma_* 符号需消费方补链
（真机链接期 15 个 undefined symbol 实测，全部属 libdeflate/lzma 两
类）。修复：requires 增加 xz/5.6.2 + libdeflate/1.25（与 htslib 配方
逐字一致，allelecount/4.3.0 先例同款），generate() 注入其 -L，
make 命令行 `LIBS="-lhts -lz -lpthread -ldeflate -llzma"` 覆盖
Makefile.am 硬编码（命令行变量压过 makefile 赋值；automake 链接规则
中 LDFLAGS 在对象之前，-l 不能走 LDFLAGS）。
构建工具：autoconf/2.72、automake/1.18（tool_requires；无 LT_INIT，不需要
libtool）。xz、libdeflate 为 htslib 的必需依赖，非本任务可选项。

## W0b 历史知识核验

- 相邻已归档 autotools + bootstrap 先例：`zzuf/0.15`（tool_requires
  automake/autoconf、PERL=/data/service/hnp/bin/perl、PERL5LIB 指向
  tool 包 share、umask 077→022 替换、--build 三元组、make -j1）。
- htslib/1.24-r0 已归档（其 PR 含 OHOS 适配），transitive_headers 传递。
- E114（HMHDFS umask 077 临时目录 Permission denied）、E074（jobserver
  fifo EPERM → -j1）、R32/R33/R39/R9 均按仓库现行规则处理。

## 源码要点（tag tarball v1.4.4 实测）

- sha256 `e5c3905ffefb910a22aee44dc9374bf597b1cad84821c5f3b9e780d73513c083`
  （codeload 官方 tag 归档；release 无资产附件）。
- tarball **不含 configure**；`autogen.sh` = `autoreconf --force --install`。
- `configure.ac:18` 无条件 `LIBS="-lhts -lp -lpthread"`（**-lp 不存在**）：
  - 后果 1：AC_CHECK_LIB(hts/pthread/z) 在 configure 阶段全部报 no——
    无害，**不要误读为配置失败**；
  - 后果 2：实际链接用 src/tests Makefile.am 的
    `LIBS = -lhts -lz -lpthread`（覆盖 configure 代入值，无 -lp）；
  - 处理：**不传 --with-hts**（该分支只附加 -I/-L，多余），htslib/zlib
    路径经 conanbuild 环境 CPPFLAGS/LDFLAGS 注入。
- `Makefile.am` 硬编码 `CXXFLAGS = -g -std=c++11 -Wall -Wextra -Werror
  -Wno-unused-but-set-variable`（src 与 tests 同）。GNU make 中环境变量
  覆盖 makefile 赋值 → generate() 导出完整 CXXFLAGS（-O2 -std=c++11
  -Wall -Wextra），保留上游警告级别、仅去 -Werror，防 OHOS clang 平台
  差异告警炸整包。测试断言不受影响。
- tests 的 21 个 TESTS 经 `../data/` 相对路径取数据（顶层 data/ 111KB）
  → in-source 构建（`folders.build="."`）。
- 无 catch 等测试框架（plain assert），无第三方 test 依赖。
- CLI：`ivar version`（src/ivar.cpp:670，打印 `iVar version 1.4.4`）；
  consensus 子命令可直接吃 mpileup 文本 → 消费者测试真实调用。

## 测试计划

- 上游：`make check`（21 个单元测试程序，构建阶段执行，失败时输出
  tests/test-suite.log）。目标 100%，实际数字以 MateBook 实测为准。
- 消费者：test_package/test_ivar.sh 7 项断言（version/-v/无参数/未知
  命令/consensus -h/trim 缺参/功能调用 consensus 生成共识序列），
  全部离线。

## 留给 MateBook 的验证项

1. `conan download` htslib/1.24-r0、zlib/1.3.1（及其传递依赖）确认二进制
   包可用（R35）；缺失则按规则报依赖任务，不得跳过。
2. conan create + conan test 完整跑通（bootstrap → configure → make -j1
   → make check → install → 消费者测试）。
3. 关注点（如失败按下列顺序排查）：
   - tests 链接 `-lpthread`：OHOS musl 若无 libpthread 存根库，21 个测试
     全部链接失败 → 首个真实错误是 `cannot find -lpthread`；解法为补丁
     （tests/Makefile.am 去掉 -lpthread 或换 -lc），走 conandata patches。
   - src 链接 `LIBS = -lhts -lz -lpthread` 同上。
   - -Werror 已通过环境覆盖移除；若仍见编译警告炸包，检查 conanbuild
     env 是否真被 make 继承（`make -n` 观察 CXXFLAGS）。
   - AC_CHECK_LIB 三项报 no 属预期（见上），不算 configure 失败。
   - 消费者断言 7 的共识输出：预期 `.consensus.fa` 含 `>Consensus_` 与
     连续 10 个 A（大小写不敏感匹配）；若 ivar 对 mpileup 缺映射质量列
     解析有要求，调整 fixtures 而非放宽断言。
4. `ohc-run.py finish ivar 1.4.4 built` → W4 审计（不跑 submit）。

## 真机修正记录（Windows 端汇总）

### 第 1 轮（SHA 8f4b50f8 验证中止后修正）：静态 libhts.a 传递符号

主产品链接期 15 个 undefined symbol（libdeflate_*/lzma_*）。根因：
htslib/1.24-r0 是静态库包（包内仅 libhts.a），其 package_info 不声明
自身传递符号依赖 → 消费方必须补链。修复：requires 显式加
xz/5.6.2 + libdeflate/1.25（版本钉与 htslib 配方逐字一致，W0 已核
allelecount/4.3.0 先例），include/lib 路径进 conanbuild 环境，链接符
号库以 make 命令行 `LIBS="-lhts -lz -lpthread -ldeflate -llzma"` 覆盖
（automake 链接规则 LDFLAGS 在对象之前，-l 不能走 LDFLAGS）。
-CPPFLAGS/LDFLAGS 供 configure 探测与链接命中制品仓包。

### 第 2 轮（SHA 8f4b50f8 第 2 次验证中止后修正）：运行期 libdeflate.so.0

编译/链接全绿（main 21/21 编译），make check 的 tests 二进制运行
exit 127（NEEDED libdeflate.so.0 找不到）。根因：libdeflate/1.25 包
仅共享库形态（无 .a），而 conanbuild 环境的 LD_LIBRARY_PATH 只含
SDK llvm/lib、不含依赖 lib 目录（真机实测）。修复（不硬编码缓存
路径）：
- 配方 build()：make check 命令前缀注入 `LD_LIBRARY_PATH`，libdir
  逐项取自 htslib/zlib/libdeflate/xz 的 cpp_info.libdirs；
- test_package：同款 runpaths 注入（遍历 host 依赖 cpp_info，
  防御性，ivar 自身 libdir 除外），消费者脚本运行前生效。
注入后单测复跑 rc=0（真机诊断性实测）。知识库条目：仅共享库形态
依赖的运行期路径须显式前置（conan 环境不自动携带依赖 libdirs）。

### 第 3 轮（SHA 6f94f438）补充修正：上游测试硬编码 /tmp

LD_LIBRARY_PATH 注入生效（Error loading shared library 0、
Error relocating 0，21 个单测全部真实运行），上游 21 例 20 PASS
1 FAIL——check_trim exit 255：`[E::hts_open_format] Failed to open
file "/tmp/trim.bam" : Read-only file system`（4 次写尝试全 EROFS）。
根因（钉死到源码行）：tests/test_trim.cpp:27-28 与
test_amplicon_search.cpp:42-43 硬编码 /tmp，不读 TMPDIR；设备 /tmp
为 root 只读挂载（touch 探针实测 EROFS）。环境与上游测试假设冲突，
非配方缺陷。

修复（patches/0001-tests-tmpdir.patch，测试专用 portability 补丁）：
两文件的暂存目录改为 ivar_test_tmpdir()——TMPDIR 优先（配方 make
check 显式导出构建树），缺省回退当前目录（in-source 构建，可写）；
库代码与断言零改动。Windows 级验证：patch -p1 dry-run/apply 幂等，
与手工修正树逐文件 diff 零残差。PR 将如实标注该补丁为上游测试源码
适配。

### 第 4 轮（SHA be864aa9 验证中止后修正）：make install 重链接回落默认 LIBS

里程碑：make check 首次 21/21 全 PASS（Testsuite summary TOTAL 21 /
PASS 21 / FAIL 0 / SKIP 0 / ERROR 0），TMPDIR 补丁 + LD_LIBRARY_PATH
注入在真机全部生效，前 3 轮修复无回退。本轮止于 package() 的
make install：ld.lld 15 个 undefined symbols（全部 libdeflate_/lzma_，
与第 1 轮同型），失败链接行有四个 -L 但没有 -ldeflate -llzma。

根因（命令行对比钉死）：make 命令行 `LIBS=` 覆盖只在单次调用在场，
不跨 make 调用持久化；Makefile.am 无条件 `LIBS = -lhts -lz -lpthread`
赋值优先级高于 configure 代入值 → configure 期烘焙 LIBS 不可靠；
裸 `make install` 重链 ivar 时回落默认 LIBS，缺 -ldeflate -llzma。
修复：package() 的 make install 加与 make check 完全相同的
`LIBS="-lhts -lz -lpthread -ldeflate -llzma"` 前缀（注释写明两处
必须保持一致）。-lp 无害怪癖继续不预修（见 manifest 知识条目）。
新 SHA 需 MateBook 全量复验：create → test → finish → 审计。

### 第 6 轮（SHA 1fbf570d 验证中止后修正）：test_package 两处缺陷

里程碑：构建链首次全绿——bootstrap→configure→make→make check 21/21
→ make install（LIBS 前缀与 check 逐字一致）全过，安装位 NEEDED=
libdeflate.so.0 + libc++_shared.so + libc.so（无 liblzma.so.5 属预期：
xz/5.6.2 制品包仅 liblzma.a，-llzma 已静态链入，二进制内嵌 lzma_×190），
ivar --version exit=0。第 1-5 轮问题零回退。本轮暴露 test_package 两处
缺陷（前 4 轮 make install 均未成功，test() 从未真正执行到）：

1. test_package/conanfile.py:38：`ref.name` 应为 `ref.ref.name`——
   Conan 2 中 dependencies.host.items() 的键是 Requirement 对象，
   .name 在 ref.ref 上。确定性必现；Windows 侧 cross_building() 在
   test() 开头提前返回，永远走不到该段，故开发侧测不出。
2. test_ivar.sh #7：误把 `-i` 当输入文件。ivar consensus 的 mpileup
   输入走 stdin（ivar.cpp isatty 检查强制管道），`-i` 是 FASTA 头
   seq_id——路径被当成头名，mpileup 从未被读入（"Reference length:
   0"）。且期望文件名 cns.consensus.fa 错误（上游
   call_consensus_pileup.cpp:166-167 写 <prefix>.fa + .qual.txt，
   .consensus.fa 是 samtools 命名）；默认 -m 10 会把 depth 3 的全部
   位置滤成 gap。修正：`-p cns -q 20 -m 1 < sample.mpileup`，断言
   cns.fa 存在且非空、头 ^>Consensus_（无 -i 时 seq_id 为空）、
   序列行恰为 AAAAAAAAAA（fixture 10 位置全 A、质量 III=Q40；裸
   大写碱基字符经 allele_functions.cpp default 分支按普通碱基计数，
   已核源码）、cns.qual.txt 存在。上游 21/21 全过（含 consensus
   功能项）佐证二进制功能无异常，纯属脚本调用/期望设计错误。

新 SHA 需 MateBook 全量复验：create → test → finish → 审计。
---

**编译结束**: 2026-10-01 21:17
**最终状态**: built
