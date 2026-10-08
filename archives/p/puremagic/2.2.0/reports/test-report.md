# puremagic 2.2.0 test report

## Fixed source

Upstream `puremagic-2.2.0.tar.gz`, SHA-256
`eb4bddf07c177c4b434554b92165b67449f5a51e152b976202d6254498810eef`.

## H1 #003 results, 2026-09-27

- OHOS 6.0 / aarch64, Python 3.12.9: the two unmodified upstream pytest files
  passed **95/95** using the hash-pinned test-only pytest ZIP over `PYTHONPATH`.
- Official W3 in `finish`: passed; `.ci-result.json` reported `exit_code=0`.
- Conan create and package consumer: passed; **4 scenarios, 4 API calls, and
  4 assertions**. This result is for the pre-hook recipe tree.
- Full official `finish`: **failed, rc 1**, with `step3`, `step5b`, and
  `step8` reported failed. The G0 log says the original tarball was not found
  at the expected location; it did not reach configure/make. Separately, the
  fixed sdist inventory contains no `configure`/`configure.ac` or
  Makefile/Makefile.in. This is a source-shape observation, not the logged G0
  failure. The G1 report failed the static checks for standard Conan patch
  hooks. H1 #003's other finalization and submit-readiness warnings are retained
  in its raw evidence.

## H1 #004 targeted retest, 2026-09-28

- Revised candidate: exactly one `conan create` returned **rc 0** on OHOS
  6.0/aarch64. Target Python `compileall` passed. Conan logged the `export_sources()`,
  `export_conandata_patches()` and `apply_conandata_patches()` calls; the patch
  list remained empty.
- Real package consumer: **4 scenarios, 4 API calls, 4 assertions passed**.
  H1 returned package reference
  `puremagic/2.2.0#589899285f20ac01d1e8b745fe341981:da39a3ee5e6b4b0d3255bfef95601890afd80709#c915ed033e4e2c47150dd52bc063037c`.
- Independent file inventory counted 19 runtime files (17 Python modules,
  one JSON signature database, and MIT license); each matched the fixed sdist
  by SHA-256. The recovered package archive also contains two Conan metadata
  files.
- H1 #004 did not rerun G1, upstream pytest, W3, `finish`, submission
  preflight or official CI. H1 #003's 95/95 and W3 pass belong to its earlier
  recipe tree. Its full `finish rc 1` is unchanged.

## Scope and limitations

The revised recipe adds only standard Conan patch hooks with an empty patch
list; no upstream source behavior changed. H1 #003's 95/95 and W3 results
apply to its earlier recipe tree and were not rerun for H1 #004. H1 #004 did
not run G1, full `finish`, submission preflight, or official CI. H1 #003's full
`finish` remains **rc 1**, with the recorded failed steps `step3`, `step5b`,
and `step8`. Its G0 log says the original tarball was not found at the expected
location; the fixed sdist's lack of `configure` and Makefile is a separate
source-inventory observation. Official developer role and Python-source /
`cpp`-task eligibility remain unverified.
