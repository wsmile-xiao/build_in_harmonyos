# Adaptation Notes — mpgtx 1.3.1

## Software
- **Name**: mpgtx (an MPeG ToolboX)
- **Version**: 1.3.1 (final upstream release, 2005-01-02 "Happy New Year Release")
- **Description**: command-line MPEG audio/video/system toolbox — split, join, demultiplex, ID3v1 tag editing (tagmp3), stream inspection
- **License**: GPL-2.0-only (COPYING is the plain GPLv2 text with no "or later" wording; source headers say "GNU Public License"; Homebrew records GPL-2.0-only)
- **Upstream homepage**: https://mpgtx.sourceforge.net/
- **Official source**: https://downloads.sourceforge.net/project/mpgtx/mpgtx/1.3.1/mpgtx-1.3.1.tar.gz
  (SourceForge is the only official distribution channel — there is no upstream git repository, only the dormant SourceForge CVS. Chose the official `downloads.sourceforge.net/project/mpgtx/...` path over any third-party GitHub fork; the same URL+SHA256 is independently recorded by Homebrew homebrew-core.)
- **SHA256**: 8815e73e98b862f12ba1ef5eaaf49407cf211c1f668c5ee325bf04af27f8e377 (locally verified with sha256sum)
- **Version authenticity**: confirmed via ChangeLog entry "02 January 2005 (Version 1.3.1)" and `#define MPGTX_VERSION "1.3.1"` in common.hh; 1.3.1 is the last release — upstream inactive since.

## Build System
- **Type**: custom — a hand-written `configure` shell script (NOT autotools; no configure.ac/Makefile.am exist). The tarball's `makefile` is a dummy that only prints a greeting; `./configure` writes the real `Makefile`.
- Generated Makefile targets: `default`, `warn`, `mpgtx`, `clean`, `install`, `uninstall` — nothing else.

## Upstream test audit (formal tests)
The release tarball contains **no test suite at all**:
- File list (complete, 23 files): AUTHORS, COPYING, ChangeLog, README, TODO, chunkTab.cxx/.hh, commandline.cxx, common.hh, config.guess, configure, id3command.cxx/.hh, makefile, man/{Makefile,mpgtx.1,tagmp3.1}, man/de/{Makefile,mpgtx.1,tagmp3.1}, mpeg.cxx/.hh, mpegOut.cxx/.hh, mpgtx.spec — no `test/`, `tests/`, `regression/`, no CI configs, no examples.
- No `TESTS` / `check_PROGRAMS` anywhere; no perl/python/shell test scripts.
- Actually executed (pristine tarball, generated real Makefile):
  - `make check` → `make: *** No rule to make target 'check'. Stop.` (exit 2)
  - `make test` → `make: *** No rule to make target 'test'. Stop.` (exit 2)
- **Upstream formal tests: Total = 0 / Pass = 0 / Fail = 0 / Skip = 0.**
- Package-level verification is therefore done exclusively by `test_package/` (runs the installed CLI on a programmatic MP3 fixture).

## Patches
1. `patches/0001-ohos-configure-cc-gcc-probe-strip.patch` (portability, minimal):
   - **Original errors / platform reasons**:
     a) configure hardcodes `CC="g++"` and unconditionally runs `gcc --version` to special-case GCC 3.0/3.1 (`-O3`→`-O2`). The OHOS toolchain ships only clang/clang++ (no gcc/g++), so the probe fails and CC stays a nonexistent compiler.
     b) `install` target uses coreutils `install -d/-s/-m`; the OHOS minimal userland has cp/ln/rm/mkdir but no `install(1)`.
     c) `install -s` strips the binary, discarding the lld self-signature; and there is no DESTDIR support for staging.
   - **Fix**: honor `CXX` env var (fallback `g++`), guard the gcc probe behind `command -v gcc`, add `DESTDIR=` to the generated Makefile and prefix INSTALLDIR/MANDIR/MANDIRDE with `$(DESTDIR)`, replace `install` invocations with portable `mkdir -p`/`cp -f`/`chmod 755` and drop `-s`.
   - **No functional change** for stock GCC+coreutils builds: CXX unset → g++; gcc present → probe still runs; DESTDIR defaults to empty; mkdir/cp/chmod stage the same tree as install.

## Build Configuration
- **Compiler**: OHOS clang++ (from Conan conf `tools.build:compiler_executables`, injected via `CXX` env at generate() time — no absolute paths in the recipe)
- **Configure**: `./configure --prefix=/usr` → `make` → `make install DESTDIR=<package_folder>`
- **Dependencies**: none
- **Installed files**: usr/bin/{mpgtx, mpgjoin, mpgcat, mpgsplit, mpginfo, mpgdemux, tagmp3} (binary + symlinks), usr/share man pages

## test_package
Runs the **installed** package (never the build tree) on HarmonyOS PC (AArch64, real execution):
- fixture: 8 MPEG-1 Layer III frames (417 B each, 0xFF 0xFB 0x90 0x64 header) generated programmatically by printf — no committed binaries
- checks: version, help, mpginfo analysis (layer/bitrate/sample-rate/frame size), mpgsplit cut (output count + sizes), mpgjoin rejoin (existence + size), plus 3 negative tests (junk input, missing file, no-args) asserting on real diagnostic output

## Knowledge
- mpgtx subcommands dispatch on argv[0]; all 7 commands are one binary + 6 symlinks (commands.json must declare all of them).
- mpgtx is deliberately lenient: it exits 0 even for junk input, so negative tests must assert on its diagnostic output ("is not a valid mpeg file"), not on exit codes.

---

**编译结束**: 2026-08-31
**最终状态**: built
