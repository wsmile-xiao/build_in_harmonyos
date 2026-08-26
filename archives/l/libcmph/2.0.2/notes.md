# libcmph 2.0.2 adaptation notes

## Evidence status

- Upstream: CMPH (C Minimal Perfect Hashing Library) 2.0.2, the final
  release on SourceForge (2018-12-29), mirrored on GitHub
  `bonitao/cmph` tag `v2.0.2`. Homebrew `libcmph` and Debian `cmph`
  both reference this exact tarball.
- Official URL: `https://downloads.sourceforge.net/project/cmph/v2.0.2/cmph-2.0.2.tar.gz`
- SHA256: `365f1e8056400d460f1ee7bfafdbf37d5ee6c78e8f4723bf4b3c081c89733f1e`
  — verified by download + `sha256sum`, and cross-checked against the
  Homebrew formula and Debian package metadata (both identical).
- License: `LGPL-2.1-only OR MPL-1.1` (dual-licensed; COPYING + LGPL-2 +
  MPL-1.1 shipped in the tarball, all three installed to `licenses/`).

## Build system determination

The SourceForge tarball is a **GNU autotools release** (not a git
archive). It contains a pre-generated `configure` (604 KB, dated
2018-12-29), `Makefile.in`, `aclocal.m4`, `config.guess`/`config.sub`,
`ltmain.sh`, and the full `m4/` macro set. This is the upstream-blessed
distribution artifact — the same path Homebrew and Debian use.

**No `autoreconf` is needed**, and therefore **no host
automake/autoconf/libtool dependency**. This was verified by inspecting
the tarball contents (`configure` present and executable) and confirmed
empirically: `./configure && make` builds and links cleanly without
invoking autoreconf. This deliberately avoids the class of recipes that
only work when autotools happens to be installed on the build host.

## Adaptations (no source patches)

Two environment-only adaptations, both applied at build time to
*generated* files (never to upstream source). No `patches/` directory is
declared.

| # | Problem | Root cause | Fix (build-time, generated-file only) |
|---|---------|-----------|---------------------------------------|
| 1 | config.status aborts: `could not setup config files machinery` (`Permission denied` writing `subs1.awk`) | E114: HMDFS turns config.status's `umask 077 && mktemp -d` 0700 temp dir into an unwritable setgid `drwx--S---` dir | `_drop_umask_077()` strips `umask 077` → `umask 022` in the generated `configure` before configure runs (same approach as aaphoto / abiword-plugin-clarisworks). Idempotent. |
| 2 | `make -j>1` hangs or errors (jobserver FIFO EPERM) | E074: HMDFS SELinux forbids FIFO creation | All `make` invocations pass `-j1` (build, check, install). |

config.guess (2018-03-08 snapshot) cannot identify HarmonyOS
(`uname -s = "HarmonyOS"`); the triplet is passed explicitly as
`--build/--host=aarch64-unknown-linux-gnu` (config.sub accepts
`*-linux-gnu`) so configure never runs the probe — same approach as the
libtool/automake recipes in this registry.

## Upstream tests

`tests/Makefile.am` declares the upstream official test suite:

```
TESTS = $(check_PROGRAMS)
check_PROGRAMS = graph_tests select_tests compressed_seq_tests
                 compressed_rank_tests cmph_benchmark_test
noinst_PROGRAMS = packed_mphf_tests mphf_tests   # NOT in TESTS, excluded
```

All five `check_PROGRAMS` are self-contained, link only `libcmph.la`,
and have **no libcheck dependency** (the optional `--enable-check` unit
tests need libcheck and are disabled via `--disable-check`). `make -j1
check` runs all five; each returns 0 on pass / 1 on fail.

The four `examples/*` programs are `noinst_PROGRAMS` and are **not**
part of `make check`; they are counted separately in MANIFEST.yml so the
official-test number is not inflated.

## Consumer test

`test_package/perfect_hash_contract.c` links libcmph, builds a minimal
perfect hash over a fixed 20-key set (CMPH_CHD_PH), and verifies:

- P1 perfect/injective (distinct indices),
- P2 minimal (indices in [0, nkeys), every slot hit),
- P3 stable (re-query matches first pass),
- P4 packed equivalence (`cmph_pack` + `cmph_search_packed` agree),
- P5 dump/load round-trip (`cmph_dump` → `cmph_load` reproduces mapping).

127 assertions total (7 scalar + 6 per-key loops × 20 keys).

## CLI

`src/Makefile.am` installs `bin_PROGRAMS = cmph`. The CLI is packaged
and `commands.json` (software-level) is declared per R38. Verified:
`cmph -V` prints `0.8`; `cmph -h` prints the long usage. The CLI is a
consumer of libcmph (links `libcmph.la`), so the library is the primary
artifact; `package_type = "library"`.

## Dependencies

None. libcmph is dependency-free (only libc + libm). No `requires()`;
no `tool_requires()` — autotools is not needed because the tarball ships
a pre-generated configure.
