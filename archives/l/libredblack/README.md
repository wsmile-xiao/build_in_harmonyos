# libredblack

libredblack is Damian Ivereigh's C implementation of the **red-black balanced
tree**, with a compact API — `rbinit`, `rbsearch`, `rbfind`, `rbdelete`,
`rblookup` (range queries), `rbwalk`, `rbdestroy` — and a generator script that
can emit a customised, name-mangled copy of the library.

- Upstream: http://libredblack.sourceforge.net/
- Release: 1.3
- License: LGPL-2.1 (per the COPYING file the tarball ships; downstream
  packaging metadata disagrees with itself, the source is authoritative)
- Build system: autotools
- Package form: `lib/libredblack.a` + `include/redblack.h` (or `libredblack.so*`
  with `-o shared=True`). No executables are installed.

## HarmonyOS PC adaptation

Four portability patches; the tree implementation itself is untouched.

| Patch | Purpose |
|---|---|
| `0001-config.guess.patch` | the shipped script is the **2001-09-04** release: it has no HarmonyOS case, and its only ARM entry is `arm*:Linux:*:*` — a pattern that does *not* match `aarch64` |
| `0002-config.sub.patch` | accept `linux-ohos`. **Two** places are needed: the `maybe_os` kernel-os special case next to `linux-gnu*`, and the basic-OS whitelist |
| `0003-configure.patch` | create the private temp dirs with `umask 022` instead of `077` (unusable on the OHOS HMDFS) |
| `0004-Makefile-toolchain-cflags.patch` | upstream hard-codes `CFLAGS=-Wall`, silently discarding every flag the toolchain exports — the compile line had no `-O2` and no `-fPIC` |

The package is configured with `--without-rbgen`: `rbgen` is a Python-2 era
generator script that fails on Python 3, and upstream's Makefile has an explicit
fallback for its absence.

## Upstream tests

None. `Makefile.am` has neither `TESTS` nor `check_PROGRAMS`, and the
`example*` programs are `noinst_PROGRAMS` demonstrations — no assertions and no
expected output. The package ships a consumer test instead: 200 keys inserted in
*descending* order (the worst case for an unbalanced tree), then 13 checks over
find / min / max / in-order traversal / range lookups / walk / delete.

See `1.3/notes.md` for the full record and `1.3/test_package/MANIFEST.yml` for
the audit.
