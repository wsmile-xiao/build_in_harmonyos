# kakasi 2.3.6 adaptation notes

KAKASI (Kanji Kana Simple Inverter) converts Japanese Kanji to Hiragana,
Katakana or Romaji. The package ships the `kakasi` command-line filter and
the `libkakasi` shared library, plus four helper tools (`mkkanwa`,
`atoc_conv`, `rdic_conv`, `wx2_conv`) and the `kakasi-config` script.

## W0 dependency audit

- Upstream: `http://kakasi.namazu.org/`, release `kakasi-2.3.6.tar.gz`.
- Source archive SHA256: `004276fd5619c003f514822d82d14ae83cd45fb9338e0cb56a44974b44961893`.
- License: `GPL-2.0-or-later`.
- Build system: Autotools + Libtool (`configure.in`, `Makefile.am`,
  `lib_LTLIBRARIES = libkakasi.la`).
- Hard runtime/build dependency: none (see UTF-8 note below).
- Optional dependency: `iconv`/`libiconv`, only required by upstream's
  default UTF-8 input/output support (`-iutf8`/`-outf8`). The repository has
  no `libiconv` Conan package. HarmonyOS musl `iconv` does not implement
  `EUC-JP <-> UTF-8`, so UTF-8 support is disabled this round.
- Test-only dependency: GNU `od`/`echo` (individual tests skip when absent).

### W0 conclusion

```text
依赖数量：0 个强制 Conan 依赖
已满足依赖：无（核心 EUC-JP/SJIS 转换内置于 kakasi，不依赖 iconv）
缺失依赖：libiconv（仅 UTF-8 输入/输出需要，需另起适配任务）
是否需要拆分依赖适配：是——若要启用 UTF-8，需先单独适配 libiconv
阻塞点：无（前置阶段通过 --disable-utf8 规避 iconv）
下一步：本机配方验证，真机 shadow CI
```

## W1 source and build analysis

- Project type: C (autotools + libtool), single library + command-line tools.
- Installed artifacts: `lib/libkakasi.so*`, `include/libkakasi.h`,
  `bin/kakasi` + 4 tools, `share/kakasi/{kanwadict,itaijidict}`,
  `share/man/*`.
- `kanwadict` is generated at build time by `src/mkkanwa` from the 2.2 MB
  `kakasidict` text dictionary. This runs fine on the native OHOS device
  build (the recipe builds and runs `mkkanwa` on the device itself).
- `iconv` is used only by `src/kanjiio.c` for `EUC-JP <-> UTF-8`; the
  EUC-JP/SJIS conversion path is fully self-contained.
- Upstream tests: `make check` runs 9 shell scripts (`tests/kakasi-1..9`).
  `kakasi-5` and `kakasi-7` are upstream-disabled (exit 77 / exit 0);
  `kakasi-6` and `kakasi-9` require UTF-8/`iconv`.

## W2 recipe decisions

- Source URL/SHA256 are inlined in `conanfile.py` (no `conandata.yml`) to
  avoid the CI pre-download `BUILD_DIR: parameter not set` defect described
  in the common-issues guide.
- `--disable-utf8` avoids the `AM_ICONV` probe and the `AC_RUN_IFELSE`
  `iconv_open("EUC-JP", "UTF-8")` check, both of which fail on musl/OHOS.
- OHOS uses portable GNU `--build`/`--host` triplets because the bundled 2014
  `config.guess`/`config.sub` do not recognise HarmonyOS triplets.
- The configure patch forces the `sed` fallback for `expr` and changes the
  temporary-directory `umask` from `077` to `022`, following the HarmonyOS
  common-issues guidance (toybox `expr`, HMDFS restrictive umask).
- The OHOS branch invokes `configure` through `/system/bin/sh`, matching the
  first-shadow-build permission issue seen in the `nettoe` adaptation.

## W3 test_package

- `test_package` validates the installed `bin/kakasi` binary, not the source
  tree: it checks the version banner and performs a real Kanji -> Hiragana
  conversion (`山` EUC-JP `bb b3` -> `やま` EUC-JP `a4 e4 a4 de`) that needs
  the packaged dictionary via `KANWADICTPATH`.
- The test word `山` is a plain (non-okurigana) dictionary entry
  (`やま 山`), so a single kanji matches deterministically. Upstream
  okurigana entries such as `あいs 愛` store a `tail` flag and only match
  when the following kana agrees with the tail, so a lone `愛` would not be
  converted by `-JH`.
- 3 assertions: version banner, conversion exit code, conversion output.

## Local verification (W4, this host)

- Source archive download and SHA256 check: passed.
- Configure patch applicability (`git apply --check`): passed.
- Python syntax validation for recipe and test package: passed (`py_compile`).
- YAML parsing for `manifest.yaml` / `test_package/MANIFEST.yml`: passed.
- `git diff --check`: passed.

## HarmonyOS shadow CI (W5)

- Isolated job: `kakasi-2.3.6-shadow-20260920`, OHOS armv8 native build.
- Command: `conan create archives/k/kakasi/2.3.6 -pr:h
  ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
  --build=missing`.
- `conan create` exit code: 0 (package created + test_package passed).
- L0/L1/L4/L5: pass. L2: pass (atoc_conv/rdic_conv/wx2_conv `--version`
  OK; `kakasi`/`kakasi-config`/`mkkanwa` have no `--version`, non-blocking).
- Upstream tests executed: kakasi-2/3 (romaji) passed, kakasi-8 (libkakasi
  link) passed, kakasi-7 upstream-disabled (exit 0), kakasi-4/5 skipped.
  kakasi-1 excluded (needs GNU `echo -e`); kakasi-6/9 excluded (UTF-8).
- test_package: 3/3 assertions passed (version banner + 山→やま conversion).

## Recipe iterations needed on the device

1. Declare `shared` option (Conan `library` package_type requirement).
2. `LD=ld.lld` + `-fuse-ld=lld` (libtool cannot find a bare `ld`).
3. `AR`/`RANLIB` absolute paths to `llvm-ar`/`llvm-ranlib` (libtool falls
   back to `false` for `ar` otherwise).
4. In-source build (`folders.build = "."`) because `lib/Makefile.am` uses
   relative `INCLUDES = -I.. -I../src` that break under out-of-source VPATH.
5. Run upstream tests via `sh ./kakasi-N` (HMDFS grants no exec permission).
6. Tolerate exit 77 (skip) in the upstream test loop.

## Known limitations / follow-ups

- UTF-8 input/output is disabled; enabling it needs a separate `libiconv`
  adaptation and a `kakasi` re-bind to that dependency.
- `kakasi`/`kakasi-config`/`mkkanwa` do not implement `--version`; they print
  usage to stderr and exit 1, so the CI L2 smoke check is non-blocking.
