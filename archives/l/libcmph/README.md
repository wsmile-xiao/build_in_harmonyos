# libcmph

libcmph (CMPH — C Minimal Perfect Hashing Library) provides several
minimal perfect hashing algorithms (CHM, BMZ, BMZ8, BDZ, BDZ_PH, BRZ,
FCH, CHD, CHD_PH) behind a consistent C API, plus a `cmph` command-line
tool for generating perfect hash functions from key files.

## OHOS adaptation

- Builds the official 2.0.2 GNU autotools **release tarball** (pre-generated
  `configure`) — no `autoreconf`, no host automake/autoconf/libtool
  dependency.
- Keeps upstream source and the `libcmph.so` ABI unchanged (no source
  patches).
- Build-time-only adaptation for HMDFS: drops `umask 077` from the
  generated configure/config.status (E114) and uses `-j1` (E074).
- Runs the upstream `make check` suite (5 self-contained test programs:
  graph/select/compressed_seq/compressed_rank/cmph_benchmark).
- Installs the library, public headers (`cmph.h`, `cmph_types.h`,
  `cmph_time.h`, `chd_ph.h`), the `cmph.pc` pkg-config file, and the
  `cmph` CLI.
- Consumer test builds a minimal perfect hash over a fixed key set and
  verifies perfect/minimal/stable/deterministic/packed/round-trip
  properties.

## Dependencies

None — libcmph depends only on libc and libm.

## References

- https://cmph.sourceforge.net/
- https://sourceforge.net/projects/cmph/files/v2.0.2/
