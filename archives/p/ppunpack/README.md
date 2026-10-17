# ppunpack

ppunpack is Marc Espie's small portable C decruncher for **Amiga PowerPacker**
data files (`PP20` signature): `ppunpack infile outfile` restores the original
bytes, so PowerPacked Amiga files can be processed on other machines.

- Upstream: https://aminet.net/package/misc/unix/ppsmall-1.0 (Aminet, "PowerPacker
  decruncher 1.0, short version")
- Source: https://ftp.fau.de/aminet/misc/unix/ppsmall-1.0.tar.Z (Unix compress,
  5251 bytes; the long `ppunpack-1.0.tar.Z` only adds the `sf.pp`/`sf.chk` samples,
  which test_package downloads to run upstream's `make check`)
- License: copyright (c) Marc Espie 1995, based on Nico Francois' decruncher.
  Upstream README: "THIS SOURCE-CODE CAN BE USED FOR NON COMMERCIAL PURPOSES ONLY,
  IN PPDECRUNCH OR TRACKER. PLEASE CONTACT Nico Francois (nico.francois@scala.com)
  FOR ANY OTHER USES."  Packaged verbatim as `licenses/README`; declared as
  `LicenseRef-ppunpack-noncommercial`.  Whether redistribution as a standalone
  package fits these terms is left to the maintainers' review.
- Package form: `bin/ppunpack` (application)

## HarmonyOS PC adaptation

No source patch.

| Item | Handling |
|---|---|
| `.tar.Z` (LZW) source | conan `get()` cannot unpack it and the device's toybox gzip has no LZW; `source()` downloads with sha256 and decodes with a built-in Python LZW reader |
| Makefile hard-codes `CC=acc`, `all:` runs `check` on sample files not in this distribution | `make ppunpack CC=<OHOS clang> COPTS=...` from the recipe |
| Runtime | linked `-static-pie`: libc-only tool, keeps PIE/RELRO, no loader dependency |

## Versions

| Version | Status | Notes |
|---|---|---|
| 1.0 | built | Aminet ppsmall-1.0 |
