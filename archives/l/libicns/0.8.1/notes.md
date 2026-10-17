# libicns 0.8.1 adaptation notes

## Scope

- Official source: SourceForge `icns` project libicns 0.8.1 release tarball
  (2012, the final upstream release).
- Source SHA-256: `335f10782fc79855cf02beac4926c4bf9f800a742445afbbf7729dab384555c2`
  (verified against the SourceForge canonical download and the Debian
  `libicns_0.8.1.orig.tar.gz` mirror).
- License: the library (`src/`) is LGPL-2.1-or-later; the bundled CLI tools
  (`icnsutils/`) are GPL-2.0 and are shipped as separate executables.
- The recipe is a library with three GPL command-line tools.

## Dependency gate

The only hard dependency is libpng: upstream `configure.ac` probes it with
`AC_CHECK_LIB(png, ...)`. `libpng/1.6.58.2` is already published on the OHOS
PC Conan remote and is declared as the visible public requirement
(`transitive_headers=True` because `icns.h`-consumers decode PNG elements via
the library's internal use of libpng types in the ABI surface? no — it is
declared because `libicns.pc` carries `Requires: libpng`, making it a public
pkg-config dependency).

Jasper and OpenJPEG are optional JPEG-2000 backends: when absent, configure
only emits `AC_MSG_WARN` and the library builds without JP2 decode support.
Both configure switches are disabled explicitly so the build is deterministic
and does not depend on host probing.

## Build design

The release archive ships generated Autotools files (`configure`,
`config.guess`, `config.sub`, `Makefile.in`, `ltmain.sh`, `aclocal.m4`), so
the recipe never runs autoreconf. Its single source patch teaches the bundled
2012-era GNU config scripts the OHOS triplet:

- `config.guess`: adds `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`,
  inserted before the `aarch64:Linux:*:*` case (the old-style script has no
  LIBC detection block and would otherwise die with "unable to guess system
  type" on a HarmonyOS host).
- `config.sub`: accepts `linux-ohos*` both in the `maybe_os` kernel-libc split
  (so `aarch64-unknown-linux-ohos` parses as `aarch64-unknown` + `-linux-ohos`)
  and in the basic `-os` list (so the canonicalized `-linux-gnu-ohos` form is
  also valid).

The patch was validated on a real HarmonyOS aarch64 host: `sh config.guess`
prints `aarch64-unknown-linux-ohos` and `sh config.sub` accepts that triple.

The build mirrors the libice 1.1.2 OHOS pattern: on OHOS each configure,
make, check, and install command runs under the generated Conan build
environment with `SHELL`/`CONFIG_SHELL` overridden to `/system/bin/sh`
(avoids the HNP Bash `getcwd` failure inside HMDFS Conan build folders) and
`MKDIR_P=/system/bin/mkdir -p`. Before configure, the recipe requires exactly
two upstream `umask 077` sites in `configure` and rewrites them to `umask 022`
so `config.status` does not create HMDFS temporaries the effective user cannot
write (fails closed if the upstream layout changes). Every make invocation is
serial. `TMPDIR` is bound to a build-local `.tmp` directory.

`png2icns` uses the libpng grayscale API guarded by
`#if PNG_LIBPNG_VER >= 10209`; with libpng 1.6.58 the modern
`png_set_expand_gray_1_2_4_to_8` path compiles unchanged — no compatibility
patch is needed.

The installed `libicns.pc` is rewritten to package-relative paths and the
obsolete non-relocatable `libicns.la` is deleted. The upstream libtool
`-version-info 3:0:2` is preserved — verified in the installed package:
file `libicns.so.1.2.0`, SONAME `libicns.so.1` (`readelf -d`, matches the
`libicns.so.1` → `libicns.so.1.2.0` symlink pair).

## Tools

`icns2png`, `icontainer2icns`, and `png2icns` are installed under `bin/` and
declared in the software-level `commands.json` (L0k). `icns2png --version`
exits 1 by upstream design (`CONVERSION_SHOWDOC`), which CI L2 treats as a
non-blocking observation, matching the upstream CLI contract.

## Tests

Upstream has no test suite: no `TESTS`, `check_PROGRAMS`, or `check` sources
exist in any `Makefile.am`; `samples/` holds only three data files
(`test1.icns`, `test2.rsrc`, `test3.bin`) and no assertion code. `make check`
is still executed and the truthful upstream count is `0/0`.

The Conan consumer test (`test.c`) is a full API round-trip against the
installed header and shared library: create family → synthesize a 32×32 ARGB
image (`icns_init_image`) → encode (`icns_new_element_from_image`) →
insert/read-back (`icns_set_element_in_family`/`icns_get_element_from_family`)
→ decode and pixel-compare (`icns_get_image_from_element`) → utils API
(`icns_get_image_info_for_type`, `icns_get_type_from_image_info`,
`icns_type_str`) → export/import blob (`icns_export_family_data`/
`icns_import_family_data`) → write/read round-trip through a real temp file
(`icns_write_family_to_file`/`icns_read_family_from_file`).

The OHOS-specific test (`test_ohos_libicns.c`, counted as its own independent
test entry) covers the adaptation points directly: it `dlopen`s the installed
`libicns.so` (proving the patched config scripts produced a loadable shared
object for the ohos triple), and runs a 16×16 icon file round-trip under the
Conan-provided `TMPDIR` with `stat` permission checks on the written file
(the HMDFS/umask adaptation, knowledge E011/E002).

Tests are counted by independent entry point: upstream 0/0 (no test suite,
§ Tests above), consumer `test_libicns` 1/1, OHOS-specific
`test_ohos_libicns` 1/1. Their internal assertion checkpoints (48 total:
32 in `test.c` — 26 CHECK + 6 `fail()` sites; 16 in `test_ohos_libicns.c` —
13 CHECK + 3 `fail()` sites) are recorded in `MANIFEST.yml` as quality
metrics only and are not counted as test cases.

## Current state

- Local `conan create` (G0–G4): PASS — log at `reports/conan-create.log`
  (with `-pr ~/.conan2/profiles/ohos-aarch64-local`, the device-local
  reproduction profile; the CI profile hardcodes the runner toolchain path).
- Consumer/OHOS test executables built and run: PASS —
  `reports/conan-create.log` (`RUN: ./test_libicns` → `all checks passed`,
  `RUN: ./test_ohos_libicns` → `all checks passed`); the build-phase
  compile log is kept at `reports/test-package.log` (its test() section
  is truncated — the executed-run evidence lives in conan-create.log).
- Upstream `make check`: executed in build(); upstream has no test suite
  (`Nothing to be done for 'check'`), truthful count 0/0.
- Manual destructive reverse verification (L1e): sabotaged package
  (moved `lib/` + `include/` out) → `conan test` fails immediately with
  "Library 'icns' not found in package"; restored afterwards.
- Scoped CI (`CI_PACKAGES=archives/l/libicns/0.8.1 zsh
  ci/conan/build_and_test.sh`): **PASS** — L0e/L0f/L0h/L0k, L1a/L1b/L1c,
  L1e (auto destructive reverse), L4, L5 all green; L2 smoke observes
  icns2png --version exit 1 (upstream CLI design, non-blocking, pre-declared
  in notes). Log at `reports/scoped-ci.log`.
- Absolute-path scan of recipe tree: clean (no `/storage`, `/data/service`,
  `/home` literals outside logs).
- `python3 -m py_compile` on both conanfiles: PASS.
- `git diff --check` / `git diff --cached --check`: clean (rc=0). The
  patch file's unified-diff context lines keep the upstream config.guess
  tab indentation (same as the already-merged libice 1.1.2 / nvi 1.81.6
  config patches); the repo-standard `patches/.gitattributes`
  (`*.patch whitespace=-blank-at-eol,-blank-at-eof,-space-before-tab`,
  same as autoconf/glib and 8 other merged packages) scopes the check
  exemption to exactly those context lines.
- Knowledge: this adaptation surfaced a real reusable gap — the official
  `scripts/patch-autotools-ohos.pl` anchors only match post-2016 config
  scripts and silently produced a broken config.guess on the 2012-era
  libicns scripts (self-check 1/5). Filed as
  `knowledge/drafts/DRAFT-E564-oldstyle-config-guess-ohos-reanchor.{kv,md}`
  after dedup against E007 / DRAFT-c-ares-lite / DRAFT-postgresql-18.3.
  `knowledge_check.sh`: PASS.

---

**编译结束**: 2026-09-08 (conan create + scoped CI + both consumer tests PASS)
**最终状态**: built — pending PR CI and release publication (no commit made per instructions)
