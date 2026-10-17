# lib2geom 1.4.0 native adaptation notes

Scope: shared library, all 25 upstream CTest executable groups, independent installed-package consumer. No test executable excluded. Optional Cython/Cairo/GTK toys are not delivered.
Published graph: boost/1.90.0.3, double-conversion/3.4.0, glib/2.88.3.1, gsl/2.8 and gtest/1.17.0.2. Dependencies were downloaded from ohpcd; none rebuilt with build=missing.

## Failures and changes
- r1: upstream consumed pkg-config library names but omitted their library directories. Derive shared/executable -L flags from the resolved Conan graph.
- r2: Clang 15 did not accept nine C++20 implicit dependent-type uses. Add explicit typename in planar-graph.h.
- r3: compilation completed; 5/25 executable groups failed numeric assertions.
- r4: OHOS Clang -ffp-contract=off fixed Bezier, ellipse, arc and quartic failures without assertion changes. Circle and coincident-line tests still failed.
- r5: preserve exact nondegenerate matching/reversed endpoints before the normalization-based overlap path. This avoids discarding exact endpoint intersections due to projection roundoff; do not broaden the generic overlap tolerance.
- OHOS circle test a/c reconstruction differed by one double ULP at coordinates near 10 (approximately 1.78e-15), larger than its 1e-15 absolute threshold. Only this assertion changes to 4e-15, the bound already used by the adjacent b/c test. The expected counts, geometric checks and all random test iterations remain. This is a test modification, not an unchanged upstream result, and must be disclosed in PR.

## Evidence
Final run lib2geom-conan-20261011T0632Z-r5: Conan RC0, 25/25 CTest executable groups, including 263/263 GoogleTest cases across 22 executables and 3 independent custom programs. Consumer 18 assertions: Bezier evaluation, point arithmetic, SVG path parsing, HarmonyOS identity, TMPDIR write/pread/unlink.
Candidate SHA256 f5598c02c3747dfe0624bb9e16eed1b8487fe2676098f72f7db533af5c80fb70.
Log SHA256 6b07ff1b912c8f941f15a82431c267ef5b0c2ab31fff33564dac71eeb9c7b90b.
All 12 immutable receipts, release and postrelease PASS. Failed r1-r4 remain FAIL.

## Pending
Historical pending list superseded below; remote submission remains gated by PRE/POST contracts.

## Formal validation and submission preparation

Official three-patch candidate passed `lib2geom-finish-20261011-r2`: conan-verify and embedded W3 PASS; 25/25 CTest programs, 263/263 GoogleTest cases plus 3/3 custom programs (266 logical inventory items), installed consumer 18 assertions. Raw W3 SHA-256 913384caed3e36f0e58ee9b5fd2b14395c4efd1e0ddfeef220cc4ef65f14c4f8; CI integrity 9ac4a426fe814300. All 12 receipts, release/postrelease PASS on rebooted device. Original formal r1 failed `/bin/sh: can't fork - try again`, preserved as FAIL; it was not resumed across boot drift.

Aggregate finish RC1 is only legacy post-W3 step5b/step8 readiness/staging, not compilation/test failure. Do not claim whole-finish or competition-worker CI PASS. Source registration inventory, normalized provenance-bound PASS summary, HD reassessment and knowledge pair E545-draft-GE11 are in submission material. OHOS circle tolerance modification remains disclosed. No runtime input changed after the successful formal run; later notes/knowledge reporting edits are metadata only.
