# librttopo 1.1.0 adaptation notes

## Validation boundary

- Latest stable upstream release: `librttopo-1.1.0`.
- Package version `1.1.0` contains the corrected OpenHarmony recipe for that
  upstream release and replaces the initial defective package of the same
  version.
- Official source SHA-256:
  `5b4002b2b6be1fe59a487cff6edbc81db773dd1e437beb966fac6ac68e849f19`.
- Dependency: published `geos/3.13.1`.
- The release archive ships no upstream test suite: no test directory,
  `TESTS`, or `check_PROGRAMS` registration. Upstream count is therefore 0/0.

## Blocking downstream evidence

The previous `librttopo/1.1.0` package resolved in a fresh HarmonyOS arm64
Conan graph, but `libspatialite/5.1.0.1` then ran its complete upstream suite
at 107/108. The only failure was `check_toponoface2d`:

```text
RTTOPO error: SQL/MM Spatial exception - point not on edge
RTTOPO error: rtt_ModEdgeSplit failed
TopoGeo_AddLineStringNoFace() #6 error: rtt_ModEdgeSplit failed
```

The old recipe also used a Void Linux source mirror, required
`geos/3.13.0`, lacked explicit PIC, and did not carry the split correction.

## Correctness change

`rtline_split_by_point_to()` computes the closest point-to-segment distance.
The surrounding library defines `FP_TOLERANCE` as `1e-12` and consistently
uses `FP_IS_ZERO()` for floating-point predicates, but this function used the
exact predicate `mindist > 0`. The narrow patch applies that existing contract:

```c
if ( ! FP_IS_ZERO(mindist) ) return 0;
```

The consumer test covers an exact point, a point `5e-13` from the line, and a
point `2e-12` from the line. The middle case must split and the last must not,
so the test proves both sides of the tolerance boundary without weakening it.

## Public dependency contract

`librttopo_geom.h` includes `geos_c.h`, and the static `librttopo.a` retains
GEOS symbols. The GEOS requirement therefore explicitly propagates both
headers and libraries. Without `transitive_headers=True`, Conan 2 strips the
GEOS include directory when a downstream project consumes librttopo through
`rttopo::rttopo`, even though the GEOS libraries still reach the final link.
The consumer test intentionally finds only `rttopo` so this package metadata
contract cannot be bypassed by a direct GEOS declaration in the test project.

## Formal validation

The following results validate the corrected implementation content from the
superseded suffixed candidate. They do not replace a fresh build and release of
the canonical `librttopo/1.1.0` package after the defective artifact is removed.

- Upstream: 0/0 (the official release archive ships no registered suite).
- Candidate consumer assertions: 17/17 on HarmonyOS arm64.
- Previous defective `librttopo/1.1.0` artifact negative control: failed as
  expected before the corrected candidate was introduced.
- PIC whole-archive probe: passed for AArch64 with no TEXTREL and with the
  expected `libgeos_c.so` closure.
- Downstream regression: `check_toponoface2d` passed and the complete
  libspatialite upstream suite passed 108/108.
- Downstream libspatialite consumer assertions: 16/16.
- The superseded candidate's formal `finish` completed with exit code 0 and
  generated `.ci-result.json`; the historical result bundle SHA-256 is
  `fc3bb68e2e10c526e2e146ed89637f8011cadad1b26d8c4cddad3edd1d0ad6b9`.
---

**编译结束**: 2026-08-06 07:02
**最终状态**: failed (canonical 1.1.0 rebuild required)
