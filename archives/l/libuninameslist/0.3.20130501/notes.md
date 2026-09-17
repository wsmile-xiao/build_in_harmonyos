# libuninameslist 0.3.20130501 — OHOS PC (AArch64) Conan 2 archive

## What this is

`libuninameslist` provides direct access to the Unicode NamesList.txt
annotation data from C: `uniNamesList_name(uni)` returns the official
Unicode character name, `uniNamesList_annot(uni)` returns the annotations
block (aliases, cross references), and `uniNamesList_NamesListVersion()`
returns the data version banner ("Nameslist-Version: 6.2" for this
release — the old tag scheme is `0.3.<NamesList stamp>`).  It is part of
the fontforge ecosystem (fontforge links it for glyph-name lookups) and
usable by any font/text tool that needs Unicode character metadata.

Pure C, zero third-party dependencies: the generated `nameslist.c` is a
static const table + binary-search lookup, libc only.

## Upstream source & license

- Source: `https://github.com/fontforge/libuninameslist/archive/refs/tags/0.3.20130501.tar.gz`
- SHA256: `bd16f55305122e9b181d27a1117586338735e220788f2f9ed2abbef690000611`
- License: the data table (nameslist.c) carries the Unicode Terms of Use
  notice; `LICENSE`/`COPYING` (GPL-2.0-or-later) covers the build tooling
  (buildnameslist.c).  The conan recipe records `Unicode-TOU` for the
  library artifact.
- Build system: Autotools (`configure.ac` + `Makefile.am`, no
  pre-generated `configure` in the tag archive → `autoreconf -fi`
  bootstrap), libtool `LT_INIT` for the .so/.a pair.

## Upstream tests audit

`Makefile.am` registers **no TESTS / check_PROGRAMS / check-local /
custom check target**: `make check` prints "Nothing to be done for
'check'" — the automake default zero-test audit target.  The optional
`buildnameslist` helper (EXTRA_PROGRAMS, buildnameslist.c) is a
data-table regeneration tool that needs `NamesList.txt` downloaded at
build time; it is not a test and not part of the check target.
Upstream C-runnable tests = **0** (Total/Pass/Fail/Skip = 0/0/0/0).
Consumer validation lives in `test_package/` (14 numbered CHECKs, see
test_package/MANIFEST.yml).

## OHOS adaptations (0 source patches — all runtime)

- **E007/E514** — the shipped 2013-vintage `config.guess`/`config.sub`
  predate OpenHarmony and reject `*-linux-ohos` (verified:
  `./config.sub aarch64-unknown-linux-ohos` → "Invalid configuration").
  The recipe pins `--build/--host=aarch64-unknown-linux-ohos` so
  configure never runs its config.guess probe; the conan automake
  tool_require's modern config.sub accepts the triplet.
- **E443** — the tag archive ships no `configure`; `build()` runs
  `autoreconf -f -i` under VirtualBuildEnv (profile [buildenv] PATH +
  `tool_requires automake/1.18 + libtool/2.5.4` bindirs), so the whole
  autotools closure resolves on the CI worker.
- **E114** — the autoreconf-generated `configure` contains
  `umask 077 && mktemp -d`; on HMDFS (setgid dirs) that creates a
  drwx--S--- temp dir unwritable even by its owner.  The recipe rewrites
  those two lines to plain `mktemp -d` / `mkdir` before configuring.
- **E074** — `make -j1`: parallel make on HMDFS fails with jobserver
  fifo EPERM.
- The optional `--enable-oldfrenchlib` (libuninameslist-fr, old French
  annotations) is NOT enabled — upstream keeps it off by default
  (DISTCHECK_CONFIGURE_FLAGS notwithstanding, the default configure
  output builds only the main library), and the main library is what
  fontforge consumes.

## Local verification (2026-09-15, this worker)

1. Bootstrap: `autoreconf -f -i` (after installing cmd-pkgs automake
   1.16.5 + libtool 2.4.7 locally; CI uses tool_requires
   automake/1.18 + libtool/2.5.4) — clean.
2. `./configure --prefix=...` with the ohos-triplet pinning — clean.
3. `make -j4` → `libuninameslist.la` (.so.0.0.3 + .a) — clean.
4. `make check` → "Nothing to be done for 'check'" (zero-test audit
   target, exit 0).
5. `make install DESTDIR=...` → lib/libuninameslist.{so*,a,la} +
   include/uninameslist.h.
6. Consumer smoke (staging): version=Nameslist-Version: 6.2;
   name(41)=RIGHT PARENTHESIS; name(955)=GREEK SMALL LETTER LAMDA
   (official Unicode 6.2 spelling); annot(955) carries the "lambda"
   cross-reference.  The same contract is codified in
   test_package/consumer_tests.c (14 CHECKs).

## Layout

```
0.3.20130501/
├── conanfile.py             # Conan 2 recipe (autotools, E007/E443/E114/E074)
├── conandata.yml            # source URL + SHA256 (0 patches)
├── manifest.yaml            # version manifest
├── notes.md                 # this file
├── reports/
│   └── quality-report.md    # conan-verify G1-G4 result
└── test_package/            # offline consumer contract test
    ├── conanfile.py         #   CMake + direct run under conanrun
    ├── CMakeLists.txt       #   find_package + target link
    ├── consumer_tests.c     #   14 CHECKs over the whole public API
    └── MANIFEST.yml         # upstream/test audit + counting
```
---

**编译结束**: 2026-09-15 02:03
**最终状态**: built
