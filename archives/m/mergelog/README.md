# mergelog

`mergelog` is a small, fast C program that merges httpd log files written in
Common Log Format (CLF) from web servers behind round-robin DNS into a single
chronologically sorted stream on stdout. `zmergelog` is the sibling binary
that additionally handles gzipped log files via zlib.

Upstream author: Bertrand Demiddelaer.

## Versions

| Version | Status | Upstream release |
| --- | --- | --- |
| 4.5 | built | 4.5.1 (SourceForge 4.5 series) |

Homepage: https://mergelog.sourceforge.net/

## Source

The official SourceForge download (`mergelog-4.5.1.tar.gz`, release 4.5.1 — the
final upstream release per the project ChangeLog and `configure.in`) is mirrored
by the Debian pool as a PGP-signed pristine-tar orig tarball. The recipe fetches
the Debian pool copy because SourceForge's Cloudflare front currently refuses
non-interactive requests; the SHA-256 matches the signed `.dsc` manifest, so the
bytes are provably upstream-identical.

- URL: https://deb.debian.org/debian/pool/main/m/mergelog/mergelog_4.5.1.orig.tar.gz
- SHA-256: `3fd6c8cddbcb1d6500010168aa812a157147851bcdcf9599a25dca0317749da1`
- License: GPL-2.0-only (COPYING is the GPLv2 text; `src/mergelog.c` header
  states "version 2 of the License".)

## Build

Autotools (autoconf 2.13 era). The tarball ships a pre-generated `configure`
and `Makefile.in`; the recipe runs `./configure --build=... --host=...` then
`make -j1`, then `make install`. It links against `zlib/1.3.1`.

Two Debian-packaged upstream bug-fix patches are applied:

- `0001-fix-scan-offset.patch` — SCAN_OFFSET 9→8 (Debian #538859), so merged
  dates are parsed at the correct column.
- `0002-fix-linker-order.patch` — move `$(LIBS)` after the object file so
  `ld.lld` resolves zlib symbols.

## Commands

- `mergelog logfile1 logfile2 ...` — merge plain CLF files, sorted by date.
- `zmergelog logfile1 logfile2 ...` — same, plus support for gzip-compressed
  inputs.

## Tests

Upstream ships **no formal test suite**: the release tarball has no `tests/`
or `test/` directory, no `TESTS` automake variable, and the `make check`
target is the empty autotools default (`check-am: all-am`). See
`4.5/test_package/MANIFEST.yml` for the full evidence.

The consumer `test_package/` fills that gap: it runs the packaged `mergelog`
and `zmergelog` binaries on real CLF fixtures (and gzip variants) and asserts
on date-sorted merge order plus the no-args CLI contract.
