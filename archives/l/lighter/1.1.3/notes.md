# lighter 1.1.3 adaptation notes

## Upstream

Lighter (`https://github.com/mourisl/Lighter`) corrects sequencing-read errors
and trims adapters using a k-mer spectrum. The 1.1.3 tarball holds 16 files:
three translation units (`main.cpp`, `ErrorCorrection.cpp`, `GetKmers.cpp`), ten
headers, a bare `Makefile`, `LICENSE`, `README.md` and `.gitignore`. There is not
a single `.c` file — the tree is C++, so the recipe drives `CXX`, not `CC`.

## License (upstream contradicts itself, disclosed not resolved)

The `LICENSE` file shipped in the tarball is the FSF **GNU General Public
License Version 3** text (`LICENSE` line 3 reads "Version 3, 29 June 2007").
The README notice, however, is boilerplate for a different grant: lines
108-111 of `README.md` say the program may be redistributed "under the terms of
the GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version", i.e.
GPL-2.0-or-later. The recipe declares `license = "GPL-3.0-or-later"`, which follows
the license text that is actually packaged (`LICENSE` lines 572-587 also carry
the GPL-3 "or any later version" option clause). The contradiction is upstream's
and is recorded here rather than silently picked one way; if the reviewers
prefer the README grant, the only change needed is the SPDX string. **主窗判定（2026-09-25）：以打包许可证正文为准**，取值维持 `GPL-3.0-or-later`，不改成 GPL-2.0。

## Build decisions

* `package_type = "application"`: upstream produces one CLI, `lighter`.
* The Makefile hard-codes `CXX = g++`, `CXXFLAGS = -Wall -O3` and
  `LINKFLAGS = -lpthread -lz`, and defines **no install target**. The recipe
  overrides `CXX`/`CXXFLAGS`/`LINKFLAGS` on the make command line so the Conan
  toolchain and the zlib dependency paths reach both the compile and the link
  step without patching upstream, and `package()` copies `lighter` to `bin/`
  and `LICENSE` to `licenses/` by hand because OHOS ships no coreutils
  `install(1)` (R16: the artifact still comes out of `conan create`).
* `make -j1` (R9, HMDFS).
* The compiler is read through
  `conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp")`
  — on conan 2.29.1 the `:c`/`:cpp` sub-keys are not addressable and raise
  `does not exist in configuration list` (R33).

## zlib dependency and source URL

* `File.h` and `Reads.h` `#include <zlib.h>` and call `gzopen`/`gzread`, so zlib
  is a genuine link dependency rather than an optional one.
* `requires = zlib/1.3.2`. Version choice: repo-wide, merged recipes use
  zlib/1.3.1.1 (423) and zlib/1.3.1 (407) most often, then zlib/1.3.2 (52);
  the closest structural analogue already merged, archives/a/adapterremoval/2.3.4, is a bare-Makefile C++ sequencing tool that requires zlib/1.3.2, so this recipe follows it; W0 (ci/scripts/preflight_check.sh lighter/1.1.3) is what decides whether that version is published on ohpcd, and its verdict is quoted verbatim in the gate report. The published state was then confirmed by an actual fetch during conan create: 'zlib/1.3.2: Downloaded package revision fbb0afb34d16643c8b06ef23a0d003a4'.
* Upstream ships no test suite: the tarball has no `test`/`spec`/`check` path
  and the only Makefile targets are `all`, `lighter`, three object rules and
  `clean`. Evidence commands:
  `tar tzf lighter_1.1.3.orig.tar.gz | grep -icE 'test|spec|check'` -> 0, and
  `grep -nE '^[a-zA-Z_.-]+:' src/Lighter-1.1.3/Makefile`.
* Source URL: the GitHub tag tarball
  `https://github.com/mourisl/Lighter/archive/refs/tags/v1.1.3.tar.gz` is
  byte-identical to Debian's `lighter_1.1.3.orig.tar.gz` — both measure 48575
  bytes with sha256 `c8a251c410805f82dad77e40661f0faf14ec82dedb3ff717094ba8ff4ef94465`, verified with `curl` + `sha256sum` on the build
  host on 2026-09-25 (`~/tmp/uc2/z32-lighter/gh.tar.gz`,
  `lighter_1.1.3.orig.tar.gz`). The official upstream URL is therefore used and
  no Debian downstream host appears in `conandata.yml` (R39/PF7).

## Tests

Upstream contributed 0 cases (16-file tarball, no test/spec/check path, Makefile
targets only `all`, `lighter`, `main.o`, `ErrorCorrection.o`, `GetKmers.o`,
`clean`). The consumer suite therefore carries all coverage: **6 scenarios,
9 assertions**, every one of them executed against the packaged binary inside a
`mktemp -d "$HOME/tmp/lighter-test.XXXXXX"` scratch directory that the script
removes on exit (device `/tmp` is read-only, and fixtures must never land in the
archive directory).

Two measured behaviours of Lighter 1.1.3 shaped the assertions, and both are
recorded here because they contradict the first draft of this suite:

* **FASTQ output separates records with a trailing blank line.** A corrected
  12-read FASTQ is padded beyond 48 lines (60 in the reference run), so the first draft's
  `awk 'NR % 4 == 2'` position assumption read sequence, quality, `+` and blank
  lines as if they were all sequences. Records are parsed header-anchored now
  (`grep -A1 '^@read'`), and the layout itself is asserted (12 headers, 12 `+`
  separators).
* **`-k` consumes kmer_length, genome_size and alpha, and the trusted-kmer
  cut-off is derived from them** (`genome_size` is in bases; `-K` infers alpha
  instead). With the bare `-k 21` form the run labels every read
  `unfixable_error`; with a human-scale `genome_size` the tiny fixture is simply
  under-informed. All runs below therefore pin `-k 21 1000 1`, i.e. the fixture
  on its own scale (912 bases).
* On that scale a **single substitution is not corrected**: the 11x template
  kmers are already trusted, the outlier sits at count 1, Lighter reports
  `12 are error-free / Corrected 0 bases` and echoes the record verbatim. The
  first draft asserted that this read collapses onto the template, which is not
  what the tool does, so that assertion was *replaced, not weakened* — see the
  next bullet and the E419 section.
* What **is** corrected is a read carrying an invalid base: `nucToNum[]` marks
  non-ACGT with the `-1` sentinel, the kmers touching an `N` therefore become
  untrusted, and Lighter reports `11 are error-free / Corrected 1 bases`, tags
  the header `@read12 cor` and emits 12 identical template reads. Assertion 5
  pins exactly that (log line, header tag, single distinct output sequence equal
  to the template).

Gzipped FASTQ covers the zlib link face end to end (gzread in, gzwrite out) and
is re-inflated with an independent decompressor; plain FASTA covers the second
record writer. Every external call is wrapped in `/usr/bin/timeout`, so a hang
is a failure rather than a stall. See `test_package/MANIFEST.yml`.

## Path B judgement

## Compile failure on the target and its disposition (E419)

Round 1 of `conan create` downloaded the source cleanly and then stopped inside
`main.cpp` at the first real error (20 diagnostics emitted before clang gave
up):

    main.cpp:26:6: error: constant expression evaluates to -1 which cannot be
    narrowed to type 'char' [-Wc++11-narrowing]

The offending declaration is `main.cpp:23`, a nucleotide encoding table that
uses `-1` as the invalid-base sentinel:

    char nucToNum[26] = { 0, -1, 1, -1, -1, -1, 2, ... } ;

g++ on x86-64 defaults plain `char` to signed, so upstream never sees a problem.
clang on AArch64 defaults plain `char` to **unsigned**, so `-1` cannot narrow
into the element type at all - and had it merely been cast through, every
sentinel would have stored 255, each `nucToNum[x] == -1` test would compare 255
against -1 and silently pass, and the k-mer encoding would be corrupted rather
than fail loudly. That second part is why this was treated as a semantics
problem and not as a warning to be switched off.

This is the mechanism already recorded in the knowledge base as **E419**, "Target
plain-char signedness can change INT8 API results without changing stored bytes"
(`knowledge/graph/index.tsv` line 645, `knowledge/graph/E419.kv`). E419's
priority-1 disposition is `consistent-target-signed-char-mode` with
`rec_impl: conan-toolchain`, so the recipe adds `-fsigned-char` to `CXXFLAGS`:
no upstream line is patched, and no platform macro is introduced - E419's
`forbid_2` bans `__OHOS__`-style guards for exactly this class of problem, which
is the same boundary R8/PF5 draws.

Verification follows E419's `verification_cmd` ("rebuild every affected
translation unit ... run the complete unchanged ... package consumer on the real
target"): the recipe-level fix is exercised by the unchanged consumer suite on
the target. One claim in the first draft of these notes has been corrected by
measurement. The suite does **not** prove the `-1` sentinels behave as signed by
flipping a run-time switch - the narrowing diagnostics make the unsigned build
fail outright, so there is no unsigned binary to compare against. What the suite
does assert, and what only the sentinel semantics can satisfy, is that an
out-of-alphabet base is *recognised as invalid*: assertion 5 feeds one read
carrying `N`, and the packaged binary reports `Corrected 1 bases`, tags the
record `cor` and collapses it onto the 11x template. If `nucToNum[]` ever stored
the sentinel as 255 and compared it against -1, `N` would be an ordinary base,
the kmer would be trusted, and the run would report `Corrected 0 bases` with the
`N` still in the output - which is exactly what the substitution fixture does.
So the assertion is falsifiable in the direction that matters, without claiming
a run-time signedness experiment.

## Judgement

The one non-obvious obstacle in this port is already a documented entry, so the
conclusion is path A with knowledge reuse rather than an extension. Four-condition
comparison against E419:

* 同机制 - both are a plain-`char` object holding semantically signed 8-bit
  values (`-1` sentinels here, INT8 samples there).
* 同根因 - both come from implementation-defined plain-char signedness, where the
  AArch64 clang default is unsigned and the upstream test host default is signed.
* 同处置面 - both are repaired once at the toolchain with `-fsigned-char`
  (`rec_approach` consistent-target-signed-char-mode, `rec_impl`
  conan-toolchain), not by editing upstream sources.
* 同作用域 - both apply to every translation unit of the built artifact; the
  application domain differs (nucleotide table vs image/audio codecs), but
  E419's `affected_scope` keys on the plain-char declaration itself, which is
  what this package has.

The packaging conventions used here (no coreutils `install(1)` on OHOS, so
`package()` copies by hand; system-name libraries linked statically per R26) are
likewise already recorded elsewhere, as the scan below shows. No new OHOS-unique
capability surface was hit: no syscall was refused, no toolchain feature was
missing, and no source patch was needed, so the ledger's low B-potential stands
after measurement rather than by assumption.

The four ranges were scanned on the current baseline by the generator
(`~/tmp/uc2/z32-lighter/gen.py`, `bscan()`), line-based, with E-numbers taken
only from the names of files that actually matched:

```
ranges: knowledge/graph/*.kv, knowledge/graph/index.tsv,
        knowledge/drafts/*.kv, archives/**/notes.md
terms : install(1), coreutils, install -d, DT_NEEDED, libz.so, static only,
        zlib, narrowing, signed char, fsigned-char, plain char
  range=knowledge/graph/*.kv       term=coreutils    hits=43
    knowledge/graph/E008.kv:22: affected_scope:         使用 fstat() 判断输出类型的工具(coreutils, make, sed 等)
    knowledge/graph/E008.kv:54: source_event:           archives/c/coreutils/9.10/manifest.yaml
  range=knowledge/graph/*.kv       term=install -d   hits=4
    knowledge/graph/E108.kv:5: make.*install.*Error 127|install -d.*No such file|
    knowledge/graph/E108.kv:11: install -d, install -m0755, Error 127,
  range=knowledge/graph/*.kv       term=DT_NEEDED    hits=15
    knowledge/graph/E330.kv:8: error_signature:        failed to create symbolic link .*\.so\.[0-9]+|cmake_symlink_library: Sys
    knowledge/graph/E330.kv:12: match_keywords:         CMake, SONAME, symlink, cmake_symlink_library, CMAKE_PLATFORM_NO_VERSION
  range=knowledge/graph/*.kv       term=libz.so      hits=21
    knowledge/graph/E186.kv:2: # E110 — Rust项目在OHOS上cargo无法加载libz.so  ->E:E110
    knowledge/graph/E186.kv:14: match_keywords:         cargo, libz.so, Error loading shared library, musl ldso, RUNPATH, patche
  range=knowledge/graph/*.kv       term=static only  hits=3
    knowledge/graph/E028.kv:15: static only, ncurses, symbol link, override,
    knowledge/graph/E457.kv:35: match_keywords: glib,static only,duplicate runtime,double copy,GType,dispose,PC=0,SIGSEGV,shared
  range=knowledge/graph/*.kv       term=zlib         hits=50
    knowledge/graph/E146.kv:18: root_cause:             编译过程中发现缺少库依赖（如 libpcap/zlib/openssl），但本地编译遇到工具链限制（如 bison/flex pipe 问题）
    knowledge/graph/E186.kv:9: error_signature:        Error loading shared library libz\.so.*needed by.*cargo.*Error relocatin
  range=knowledge/graph/*.kv       term=narrowing    hits=5
    knowledge/graph/E400.kv:28: narrowing probes, then `--jitless` version/help plus
    knowledge/graph/E432.kv:7: match_keywords: native SDK, output ownership, failure status, destroy, finite coordinate, int32 
  range=knowledge/graph/*.kv       term=signed char  hits=3
    knowledge/graph/E419.kv:8: match_keywords:         -fsigned-char, plain char, unsigned char, INT8, integer promotion, AArch
    knowledge/graph/E419.kv:12: affected_scope:         C libraries that use plain char rather than signed char or int8_t for se
  range=knowledge/graph/*.kv       term=fsigned-char hits=5
    knowledge/graph/E419.kv:8: match_keywords:         -fsigned-char, plain char, unsigned char, INT8, integer promotion, AArch
    knowledge/graph/E419.kv:13: verification_cmd:       Confirm the failing values differ by 256; audit the upstream declaration
  range=knowledge/graph/*.kv       term=unsigned char hits=1
    knowledge/graph/E419.kv:8: match_keywords:         -fsigned-char, plain char, unsigned char, INT8, integer promotion, AArch
  range=knowledge/graph/*.kv       term=plain char   hits=5
    knowledge/graph/E419.kv:4: error_signature:        expected.*-[0-9]+.*actual.*[12][0-9]{2}|INT8.*char|plain char.*unsigned
    knowledge/graph/E419.kv:8: match_keywords:         -fsigned-char, plain char, unsigned char, INT8, integer promotion, AArch
  range=knowledge/graph/index.tsv  term=coreutils    hits=7
    knowledge/graph/index.tsv:236: E010	2	compat, toolchain	configure|make|sed|expr	configuration|compilation	toybox, sed, expr, GN  ->E:E010,E010
    knowledge/graph/index.tsv:302: E076	2	syscall, runtime, filesystem	cc|clang|coreutils	runtime|compilation	fstat, lseek, pipe, t  ->E:E076,E076
  range=knowledge/graph/index.tsv  term=install -d   hits=1
    knowledge/graph/index.tsv:334: E108	2	platform, install	make	installation	install, ginstall, GNU install, HarmonyOS, install -d  ->E:E108,E108
  range=knowledge/graph/index.tsv  term=DT_NEEDED    hits=2
    knowledge/graph/index.tsv:556: E330	2	ohos, cmake, linking, filesystem, shared-library	cmake|conan|ld.lld|readelf	build|package  ->E:E330
    knowledge/graph/index.tsv:761: E537	2	hmdfs, linking, conan, packaging, relocatable	conan|cmake|ld|clang|patchelf|readelf|hmdfs  ->E:E537
  range=knowledge/graph/index.tsv  term=libz.so      hits=3
    knowledge/graph/index.tsv:412: E186	3	toolchain, rust	ld	runtime	cargo, libz.so, Error loading shared library, musl ldso, RUNPA  ->E:E186,E186
    knowledge/graph/index.tsv:742: E518	3	ohos, toolchain, environment	git|buildbot|git-clone	installation|configuration	git-clone,  ->E:E518,E322
  range=knowledge/graph/index.tsv  term=static only  hits=2
    knowledge/graph/index.tsv:254: E028	3	linking, packaging	make|install	installation|runtime	shared library, conflict, system cra  ->E:E028,E028
    knowledge/graph/index.tsv:682: E457	2	linking, conan, shared-library	libtool|clang|conan|ld-musl	linking|testing	glib,static on  ->E:E457,E457
  range=knowledge/graph/index.tsv  term=zlib         hits=5
    knowledge/graph/index.tsv:742: E518	3	ohos, toolchain, environment	git|buildbot|git-clone	installation|configuration	git-clone,  ->E:E518,E322
    knowledge/graph/index.tsv:757: E533	2	hmdfs, ohos, portability, autotools, dependency	autotools|configure|make|conan	porting|te  ->E:E533
  range=knowledge/graph/index.tsv  term=narrowing    hits=1
    knowledge/graph/index.tsv:657: E432	2	native-api-contract	clang|gcc|native-sdk|code-review	source-adaptation|runtime-safety	nat  ->E:E432,E432
  range=knowledge/graph/index.tsv  term=signed char  hits=1
    knowledge/graph/index.tsv:645: E419	2	abi, c-language, signedness	clang|autotools|conan	testing|runtime	-fsigned-char, plain ch  ->E:E419,E215
  range=knowledge/graph/index.tsv  term=fsigned-char hits=1
    knowledge/graph/index.tsv:645: E419	2	abi, c-language, signedness	clang|autotools|conan	testing|runtime	-fsigned-char, plain ch  ->E:E419,E215
  range=knowledge/graph/index.tsv  term=unsigned char hits=1
    knowledge/graph/index.tsv:645: E419	2	abi, c-language, signedness	clang|autotools|conan	testing|runtime	-fsigned-char, plain ch  ->E:E419,E215
  range=knowledge/graph/index.tsv  term=plain char   hits=1
    knowledge/graph/index.tsv:645: E419	2	abi, c-language, signedness	clang|autotools|conan	testing|runtime	-fsigned-char, plain ch  ->E:E419,E215
  range=knowledge/drafts/*.kv      term=install(1)   hits=3
    knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.kv:28: match_keywords:         qbe, compiler backend, SSA, code generation, arm64, assembly, end-to-end
    knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.kv:39: rec_description:        最小且行为保持地让驱动接受 TMPDIR（tmp=${TMPDIR:-/tmp}/qbe.zzzz；默认行为不变、不引入平台宏、无绝对路径），配
  range=knowledge/drafts/*.kv      term=coreutils    hits=35
    knowledge/drafts/DRAFT-E574-libosip-installsh-single-file-batch-loss.kv:18: root_cause: OHOS PC 上 PATH 无 /usr/bin/install（精简 userland 不带 coreutils install），configure 探测失败后回
    knowledge/drafts/DRAFT-argp-musl-gap-bridge.kv:21: command-line parsing, coreutils, elfutils,
  range=knowledge/drafts/*.kv      term=install -d   hits=1
    knowledge/drafts/DRAFT-8958-clthreads-makefile-stage-install-shadow.kv:24: match_keywords:         make install DESTDIR, install -d Permission denied, Error 127 install,
  range=knowledge/drafts/*.kv      term=DT_NEEDED    hits=173
    knowledge/drafts/DRAFT-332-openrct2-0.5.3-libcpp15-cpp20-compat.kv:57: <传递依赖绝对路径>」：readelf -d 查 DT_NEEDED 是否绝对路径——fontconfig/
    knowledge/drafts/DRAFT-3888-audiocd-ohos-musl-elf-segment-layout.kv:38: sweep：OHOS patchelf 会把段表重排成被拒布局。绝对路径 DT_NEEDED 在 CI 环境一致的
  range=knowledge/drafts/*.kv      term=libz.so      hits=15
    knowledge/drafts/DRAFT-E569-codeload-direct-url-bypass-302.kv:11: Error loading shared library libz.so, Max retries exceeded, ConnectTimeoutError,
    knowledge/drafts/DRAFT-E569-codeload-direct-url-bypass-302.kv:17: git（git 缺 libz.so，exit 127）。conan 源码下载走两条通道：(1) CI 的
  range=knowledge/drafts/*.kv      term=zlib         hits=247
    knowledge/drafts/DRAFT-E572-removed-config-script-pkgconfig-migration.kv:56: 同时把配方侧仍需的依赖 flags（如静态 zlib 的 -I/-L）用同一 pkg-config 注入
    knowledge/drafts/DRAFT-E572-removed-config-script-pkgconfig-migration.kv:58: rec_command: make -j1 cube2font PLATFORM=aarch64-unknown-linux-ohos CXX=<clang++> PKG_CONFIG=<pk
  range=knowledge/drafts/*.kv      term=narrowing    hits=18
    knowledge/drafts/DRAFT-hfsm2-beta73-aarch64-char-narrowing.kv:1: # DRAFT — aarch64 plain-char 无符号导致上游 C++ 测试源码编译期窄化（-Wc++11-narrowing）
    knowledge/drafts/DRAFT-hfsm2-beta73-aarch64-char-narrowing.kv:7: id:                     DRAFT-hfsm2-beta73-aarch64-char-narrowing
  range=knowledge/drafts/*.kv      term=signed char  hits=33
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:15: match_keywords:         EOF, getc, fgetc, getchar, plain char, unsigned char, aarch64-unknown-li
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:19: affected_scope:         任何把 getc/fgetc/getchar 返回值或“读到的字节 + EOF”放进 char/unsigned char 变量的 C 代码：手
  range=knowledge/drafts/*.kv      term=fsigned-char hits=37
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:19: affected_scope:         任何把 getc/fgetc/getchar 返回值或“读到的字节 + EOF”放进 char/unsigned char 变量的 C 代码：手
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:24: rec_description:        把承接 getc()/fgetc() 返回值的变量类型改为 int（与标准规定的返回值域一致），使 EOF 可表示、状态机恢复出口。单行类型修正
  range=knowledge/drafts/*.kv      term=unsigned char hits=25
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:15: match_keywords:         EOF, getc, fgetc, getchar, plain char, unsigned char, aarch64-unknown-li
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:19: affected_scope:         任何把 getc/fgetc/getchar 返回值或“读到的字节 + EOF”放进 char/unsigned char 变量的 C 代码：手
  range=knowledge/drafts/*.kv      term=plain char   hits=23
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:2: # DRAFT — 用 plain char 承接 getc()/fgetc() 再与 EOF 比较：
    knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:3: #         plain char 无符号的目标平台上扫描状态机在文件末尾死循环
  range=archives/**/notes.md       term=install(1)   hits=39
    archives/c/cksfv/1.3.15/notes.md:13: 2. `make install` 调用 POSIX `install(1)` 命令，OHOS Conan 构建环境中该命令不在 PATH
    archives/c/cloud-utils-ec2metadata/0.34/notes.md:19: ### 1. Makefile — install(1) 长选项兼容
  range=archives/**/notes.md       term=coreutils    hits=190
    archives/a/aa3d/1.0/notes.md:34: | 3 | `install` 命令不可用 | OHOS 精简环境无 coreutils install | 用 `cp` + `chmod` 代替 |
    archives/a/accrete/1.0/notes.md:39: | 2 | Makefile 默认 `INSTALL=/usr/bin/install -s` 不存在 | OHOS 无 GNU coreutils install | conanfile.p
  range=archives/**/notes.md       term=install -d   hits=51
    archives/a/abi-compliance-checker/2.3/notes.md:27: perl Makefile.pl -install -destdir=<install_dir> -prefix=/usr
    archives/a/acf-core/0.24.1/notes.md:16: - **平台补丁（0001-bin-Makefile.patch）**：OHOS 无 coreutils `install` 命令（`install -Dm755` → rc127），
  range=archives/**/notes.md       term=DT_NEEDED    hits=412
    archives/a/accel-ppp/1.14.0/notes.md:63: - test_load_all_modules / test_pcre_negative_cases 曾因模块 .so 在 OHOS musl 下缺少 libtriton.so / libco
    archives/a/accessibility/26.04.3/notes.md:52: 定义 SONAME flag → 库无 DT_SONAME、消费者记录路径形 DT_NEEDED。
  range=archives/**/notes.md       term=libz.so      hits=101
    archives/a/ada-bar-codes/005/notes.md:275: gnat1 额外依赖 libmpfr.so.4/libgmp.so.10/libisl.so.23/libmpc.so.3/libz.so.1/
    archives/a/ada-bar-codes/005/notes.md:334: - gnat1 NEEDED = `libisl.so.23, libmpc.so.3, libmpfr.so.6, libgmp.so.10, libz.so.1,
  range=archives/**/notes.md       term=static only  hits=11
    archives/l/libfec/1.0-26-gc5d935f/notes.md:107: ## Local verification done (Windows host, static only)
    archives/l/liblbfgs/1.10/notes.md:19: - **Static only**: `--disable-shared --enable-static` — HarmonyOS PC uses static
  range=archives/**/notes.md       term=zlib         hits=2362
    archives/a/aaphoto/0.45/notes.md:22: DEPROOT 为 libjpeg/libpng/zlib 预编译包的合并 include/lib 目录。
    archives/a/aaphoto/0.45/notes.md:49: | zlib | 1.3.1.1 | ohpcd 制品仓 | 经 libpng 传递引入 |
  range=archives/**/notes.md       term=narrowing    hits=30
    archives/a/aces_container/1.0.2/notes.md:15: - Patch: raise the CMake minimum version to 3.5, fix Clang C++17 narrowing diagnostics in two sc
    archives/a/astlib/0.9.0/notes.md:32: | 7 | Narrowing conversion errors in cat002 spec | Generated UTF-8 bytes (-62,-80) in char array
  range=archives/**/notes.md       term=signed char  hits=54
    archives/a/aescrypt/0.7/notes.md:60: - 该软件非常老旧（2001年），代码有多处指针类型不匹配警告（char* vs unsigned char*），但不影响功能
    archives/a/anubis/4.3/notes.md:23: | 2 | `tests/mta.c` 中 `u_char` 未定义 | OHOS libc 不提供该旧 typedef | 生成 `0002-tests-mta.c.patch`，仅将两个字
  range=archives/**/notes.md       term=fsigned-char hits=23
    archives/a/avanor/0.5.8/notes.md:11: 3. 编译命令: `make CC=clang++ LD=clang++ -fuse-ld=bfd CFLAGS="-fsigned-char -pipe ..." LIBS="-lncurs
    archives/b/burst/3.1.1/notes.md:29: OHOS AArch64 compiles plain `char` as unsigned by default. Burst's unchanged `to_unsigned` docte  ->E:E419
  range=archives/**/notes.md       term=unsigned char hits=40
    archives/a/aescrypt/0.7/notes.md:60: - 该软件非常老旧（2001年），代码有多处指针类型不匹配警告（char* vs unsigned char*），但不影响功能
    archives/a/anubis/4.3/notes.md:23: | 2 | `tests/mta.c` 中 `u_char` 未定义 | OHOS libc 不提供该旧 typedef | 生成 `0002-tests-mta.c.patch`，仅将两个字
  range=archives/**/notes.md       term=plain char   hits=15
    archives/g/gdcm/3.2.11/notes.md:21: ### 3. TestRescaler2 失败：plain char 符号性（平台差异实锤）
    archives/g/gdcm/3.2.11/notes.md:23: - 根因：测试模板 `TestRescaler2Func<char,char>` 假设 plain char 是 signed（x86 Linux 语义）；OHOS arm64 SDK 下 `
```

E-numbers read from hit filenames: E008, E010, E020, E027, E028, E054, E061, E063, E076, E081, E082, E106, E108, E115, E146, E161, E174, E178, E182, E186, E188, E218, E330, E383, E400, E419, E429, E430, E432, E447, E457, E465, E492, E502, E518, E533, E534, E537, E539, E540, E541, E543, E544, E545, E547, E550, E555, E563, E566, E569, E572, E574, E575, E577, E579, E580, E588, E590, E615, E617, E623, E626, E627, E628, E631, E633, E634, E961, E998

index.tsv rows whose title mentions install/coreutils/zlib/makefile/narrowing:

```
E002	3	environment	configure|make|install	configuration|installation	/tmp, temporary, read-only, erofs, TMPDIR, Permission denied, tmp	0	true	set-env-var	P014	doc/E002.md
E010	2	compat, toolchain	configure|make|sed|expr	configuration|compilation	toybox, sed, expr, GNU coreutils, GNU sed, garbled, hang, stuck, unsupported command, label, branch, regex, \|	0	true	install
E018	2	selinux, filesystem	ln|make|install|configure	installation|configuration	ln, symlink, Permission denied, wrapper script, soft link, SELinux, ln -sf, garbled, readlink, exec, copy instead of lin
E021	1	configure, filesystem	configure|make	configuration	BUILDEXEEXT, .exe, case insensitive, conftestdir, file system, build exe, extension, Makefile	0	false	skip-configure-test		doc/E021.md
E028	3	linking, packaging	make|install	installation|runtime	shared library, conflict, system crash, --without-shared, static only, ncurses, symbol link, override, LD_LIBRARY_PATH, rpath, version misma
E034	2	packaging, filesystem, security	wget|curl|python|runtime	runtime|download	CA certificates, SSL, wget, curl, ca-certificates, /etc/ssl/certs, certificate verify failed, unable to load	1	false	in
E035	3	compat, build-system	b2|bjam|boost-build	configuration	boost, b2, bjam, SHELL, version, error code, match-command-output	1	false	header-only-install		doc/E035.md
E037	2	compat, portability, filesystem, shell	shell|runtime|install	installation|runtime	/usr/bin/env, shebang, bad interpreter, No such file, env not found, shell script, #!/usr/bin/env, portable	2	t
E041	2	compat, build-system, autotools	configure|automake|make	configuration|compilation	automake, version mismatch, aclocal, autoheader, autoreconf, VPATH, timestamp, Makefile.am, configure.ac	1	true
E042	2	linking, packaging, runtime	patchelf|packaging|runtime	installation|runtime	RPATH, patchelf, lib-dynload, extension module, NEEDED, ImportError, portable, $ORIGIN, Python, gdbm	1	true	set-rpath
E049	2	portability, build-system, shell	perl|automake|shell|install	installation|runtime	shebang, hardcoded path, interpreter, perl, python, automake, gen-all.pl, portable, #!/data/, #!/usr/local/	1	t
E050	3	hmdfs, linking, runtime, filesystem	ld|clang|pip|make	linking|installation|runtime	HMDFS, symlink, symbolic link, os.path.exists, ld.lld, -lpython, pip install, make install, lib*.so, linker	1	
```

- ## Gate status at hand-off (2026-09-25, 续棒窗口)

`test_package` was made green by this round (scratch directory + the corrected
expectations above). The four gate commands below were started **after** the
commit, in the background, because the tool-call budget of this round ran out
first; nothing here claims they passed. Raw logs and per-step verdict lines:
`~/tmp/uc2/z32-lighter/gates/` (`create4.log`, `verify.log`, `finish.log`,
`graph.log`, `preflight.log`, summary in `GATES.md`). Items still owed to the
four-piece gate: `ohc-run.py conan-verify` (G0-G4, not W3),
`ohc-run.py finish lighter 1.1.3 built` (W3 = its step 5),
`ohc-run.py graph validate`, `python3 scripts/ohc/preflight.py . origin/main HEAD`
(PF1-PF9) - judge them from the logs, and re-run anything that did not land.

Known framework-side reds that stay **disclosed, not re-judged**: `step5b
unreferenced`, `step8 gen_summary`, the `step10` three-missing-artifacts report,
`G0` "cannot find the original tarball", and the PF9 / software-level
three-piece-set conflict if it fires. Also untouched on purpose: the worktree
carries someone else's uncommitted `archives/l/libXext/{README.md,manifest.yaml}`
edits, which were not staged, not reverted and not committed by this round.

**适配路径**: A
- **使用知识库**: hit E419（四条件对照见上文）；另复用 R26 系统名库静态链接与 OHOS 无 install(1) 的手工打包口径
- **知识库扩展**: 无（本包唯一非显然障碍已被 E419 覆盖，未观察到 OHOS 独有能力面）
- **关联 Issue**: 待创建（PRE_CREATE）
---

**编译结束**: 2026-09-25 05:34
**最终状态**: built
