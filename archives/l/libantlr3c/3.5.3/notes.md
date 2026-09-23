# libantlr3c 3.5.3 — OHOS PC (AArch64) Conan 2 archive

## What this is

`libantlr3c` is the C target runtime of the ANTLR v3 parser generator
(www.antlr3.org, github.com/antlr/antlr3, tag 3.5.3).  This archive packages
only the runtime library built from `runtime/C` of the antlr3-3.5.3 tag
archive — the parser generator itself is a Java tool and is not needed at
build or run time by consumers.

## Host/target split (E549 investigation)

The ANTLR v3 code generator (antlr-3.5.3-complete.jar, Java) is a
**host-side development tool**.  Lexers/parsers it emits are plain C files
that `#include <antlr3.h>` and link against `libantlr3c`.  Therefore:

- **target package** (this archive): `libantlr3c/3.5.3` — runtime library +
  30 public headers, no Java dependency, no generator dependency.
- **host tool** (NOT this archive): the Java generator.  Consumers that want
  generated parser sources generate them at development time on the host and
  check in the generated C code; a Conan package for the generator would
  belong in a separate `requires_openjdk` host recipe and is out of scope
  for the target runtime package.

The test package exercises the runtime **without any generator**: it
hand-writes the exact call pattern a generated lexer uses (mTokens override
+ antlr3LexerNewStream + antlr3CommonTokenStreamSourceNew), which keeps the
consumer test auditable, reproducible offline, and free of host-tool
contamination.  This is the audit path for the E549 "generator-runtime
split" boundary: generated C code depends only on the target runtime
package, so the consumer test is exactly "compile + link + run
generated-style code against the installed library".  The knowledge
draft `knowledge/drafts/E549-draft-BEBE.{kv,md}` records this boundary
(the initial idea was filed under E546 but that ID is already taken by
the libmagic build-time generator-selection draft upstream; E549 is the
globally free next ID, created with the official `graph add --draft`
tool with OHC_AGENT_ID=BEBE preserved).

## Upstream source & license

- Source: `https://github.com/antlr/antlr3/archive/refs/tags/3.5.3.tar.gz`
- SHA256: `a0892bcf164573d539b930e57a87ea45333141863a0dd3a49e5d8c919c8a58ab`
- License: BSD-3-Clause (runtime/C/COPYING; also embedded in configure.ac
  AC_COPYRIGHT — Jim Idle, Temporal Wave LLC)
- Build system: Autotools in `runtime/C` (configure.ac + Makefile.am, no
  pre-generated `configure` in the tag archive → `autoreconf -fi` bootstrap)
- Dependencies: libc only (memset/memmove/strdup); optional sys/socket +
  netinet/tcp probes for the ANTLR debugger socket (--enable-antlrdebug,
  default on, probes are conditional)

## Layout

```
3.5.3/
├── conanfile.py             # Conan 2 recipe (autotools, E007/E514/E074/E114)
├── conandata.yml            # source URL + SHA256
├── manifest.yaml            # version manifest (artifacts: reports/quality-report.md)
├── notes.md                 # this file
├── patches/                 # VPATH support for out-of-tree build
│   └── 0001-Makefile.am-VPATH-support.patch
├── reports/
│   └── quality-report.md    # verify-build G1-G4 result
└── test_package/            # offline, generator-free consumer contract test
    ├── conanfile.py         #   CMake + CTest, runs only when can_run()
    ├── CMakeLists.txt       #   find_package + target link
    ├── consumer_tests.c     #   hand-written generated-style lexer driver
    └── MANIFEST.yml         # upstream/test audit + counting
```

## Upstream tests audit (task requirement 3)

`runtime/C/Makefile.am` in the antlr3-3.5.3 tag archive registers **no
TESTS, check_PROGRAMS, check-LTLIBRARIES, check-local or custom test
target**; `make check` runs the automake default zero-test audit target.
The broader antlr3 repo test suites (runtime/ANTLRTreeParser etc.) are
Java-harness generator suites and do not build against runtime/C.  So
upstream officially provides **0 C-runnable tests** for this runtime;
Total/Pass/Fail/Skip = 0/0/0/0.  Consumer-level validation therefore lives
in `test_package/` (see MANIFEST.yml for the counting).

## OHOS-specific notes (why the recipe is shaped this way)

- **E007/E514** — config.guess cannot identify HarmonyOS.  The recipe pins
  `--build/--host=aarch64-unknown-linux-ohos` so the generated configure
  never runs its config.guess probe (config.sub accepts `*-linux-ohos`).
- **E074** — `make -j1`: parallel make on HMDFS fails with jobserver fifo
  EPERM.
- **E114** — the autoreconf-generated `runtime/C/configure` contains
  `umask 077 && mktemp -d`; on HMDFS (setgid dirs) that creates a drwx--S---
  temp dir that is unwritable even by its owner.  The recipe rewrites those
  two lines to a plain `mktemp -d` / `mkdir` before running configure.
- **--enable-64bit** — required on AArch64.  Without it, `ANTLR3_MARKER` is
  `ANTLR3_INT32` and pointer→marker assignments truncate on LP64; the 3.5.3
  runtime assumes 64-bit markers on 64-bit platforms.  configure.ac adds no
  ABI flag for clang (it falls into the generic `*)` branch), so this option
  only selects the 64-bit typedef/macro branch in antlr3defs.h.

## Where A/B path adjudication landed

- Upstream `runtime/C` = `Makefile.am` (not CMake): **Path A** (autotools +
  autoreconf bootstrap) — same family as libXext/a52dec.  A CMake
  re-implementation would be a foreign build system and lose the
  autotools-only OHOS knowledge entries (E007/E514/E074/E114).
- Conan layout: basic_layout; the build itself is a **VPATH (out-of-tree)
  build** — conan runs `runtime/C/configure` with cwd = build folder, and
  `patches/0001-Makefile.am-VPATH-support.patch` rewrites the in-tree-only
  `INCLUDES = -Iinclude` into VPATH-safe
  `AM_CPPFLAGS = -I$(top_srcdir)/include -I$(top_builddir)`.
