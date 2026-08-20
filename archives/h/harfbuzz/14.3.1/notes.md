# HarfBuzz 14.3.1 adaptation notes

## Source and scope

- Official source: `harfbuzz-14.3.1.tar.xz`
- SHA-256: `9dae9538aae2ffdf70cec31f2c27bf68e2aaeeae3112688467697d5faf6194f7`
- Build system: Meson
- Delivery default: `shared=True`, required by Pango consumers

## Dependency decision

The 14.3.1 source exposes GLib, GObject, Cairo, zlib, ICU, Graphite2, Rust,
platform shapers, and demo integrations as optional Meson features. This
candidate disables those providers and keeps only `freetype/2.14.3` as a Conan
dependency. The current FreeType recipe has no Conan requirements and passes
`--with-harfbuzz=no`, so the graph is acyclic.

Fresh W0 evidence from the accepted W3 snapshot:

- Run: `20260819T010115Z`
- Root: `E:/HarmonyPC/validation/harfbuzz-14.3.1/w3-r7-20260819T010115Z`
- FreeType RREV: `7e95a2b2401fd12dcbdd2bf748f56b19`
- FreeType PID: `01d92cf349a0dd98ff915f4bd99a04430171517f`
- FreeType PREV: `333a87c0272a09afc1e8cbadd8de3ac6`
- Binary remote: `ohpcd`
- `info_invalid=0`, missing nodes `0`

## Test design

`tests=enabled` and `utilities=enabled` expose the upstream API, fuzzing,
threads, subset, shape, and vector Meson suites. `MESON_TESTTHREADS=1` keeps
execution bounded. On Linux/OHOS, `NM`, `OBJDUMP`, and an `LDD`-compatible
`llvm-readelf -d` command are resolved from the configured Clang toolchain so
the upstream distribution checks execute instead of self-skipping for a
missing helper.

For native W3, `HARFBUZZ_SOURCE_ARCHIVE` may point to the frozen official
tarball. The recipe converts only that verified regular file to `file://` and
continues to enforce the unchanged `conandata.yml` SHA-256 through `get()`.
When `HARFBUZZ_UPSTREAM_EVIDENCE_DIR` is set, the completed build copies the
raw Meson introspection inventory and JSONL/text test logs into that task-local
directory for independent counting and hashing.

The accepted r7 run introspected 75 unique Meson entries and matched all 75
ordered JSONL terminals. Every entry returned `OK`/RC0; failures and skips were
both zero. The raw introspection, JSONL, text log, and host summary remain
separate hash-bound files.

## Native failure history

- r4 `20260818T230527Z` passed isolated target-side W0, then failed during
  Meson configure before compilation. HarfBuzz directly executed
  `src/gen-hb-version.py`, whose `#!/usr/bin/env python3` shebang resolved
  through an inaccessible `/usr/bin` on the target and raised EACCES.
- The successor dynamically resolves executable `python3` and rewrites every
  matching upstream Python entrypoint shebang in Conan's isolated source copy.
  It requires `src/gen-hb-version.py` in the rebound inventory so source drift
  fails closed; the official source archive remains unchanged.
- r5 `20260818T232832Z` passed W0, configure, and compilation, then registered
  and executed 75 Meson entries. The raw result was 9 OK, 21 FAIL, 43 ERROR,
  and 2 SKIP. Meson produced only versioned `libharfbuzz*.so.0.61431.0` files
  on HMDFS; the SONAME `.so.0` and unversioned `.so` aliases were absent, so
  the loader failed and the two shared-library distribution checks skipped.
  This is preserved as a real upstream-test failure.
- An isolated diagnostic signed copies of all five versioned build-tree
  HarfBuzz libraries through separate output files, materialized `.so.0`
  aliases as ordinary files, verified five `.codesign` sections, and made the
  original failing `test-algs` executable pass. The successor applies the same
  operation before `meson test` and after package install. Static-only testing
  would hide the two shared-library distribution checks as skips and is not
  accepted.
- r6 `20260819T001945Z` executed the full suite successfully but its original
  post-run package validator expected `package_folder` in `conan graph info`.
  Conan supplied the complete RREV/PID/PREV there but correctly left
  `package_folder=null`; the matching successful `conan install` node held the
  materialized folder. The preserved r6 terminal therefore remains a validator
  FAIL, not W3 PASS.
- r7 `20260819T010115Z` corrected only that evidence-consumer boundary and used
  a new frozen input. It passed W0, 75/75 upstream tests, shared Conan create,
  the C consumer, 63/63 package files, and 15/15 ordinary signed shared-library
  alias files on `currentUser@10.62.215.229:2222`.

## Accepted r7 evidence

- Input tar SHA-256: `1149e1797417415e21cecb6d68e1869b6e2f653c3640a63b3486a31a517eeb92`
- Result tar SHA-256: `010979c158a39760ba83aa23e4f7c27bb1c7f85be81c0827fa070491720941a1`
- Runner receipt SHA-256: `e98d3d5a610903f64f0df1e942a5e0b5447cf414bcfaaae1953765945e1d1f4a`
- Independent readback SHA-256: `0ed625213945ff306ddfefe411c30d80083a02a5beaba9ab664199f454c0d5d1`
- Collected summary SHA-256: `edb87894926b00dcaf04e2c9455e35d79813f4ad6e8a8b53dbfdf0a6207d7937`
- HarfBuzz RREV: `d95aa2283a886e19705accd5a38c7aa9`
- HarfBuzz PID: `02e364f2d646dda8acabc40d95696553e6e53235`
- HarfBuzz PREV: `1ac65b51d4fb18288f6913c88114e961`
- Consumer: `harfbuzz 14.3.1 shaping and fetch APIs: PASS (7 glyphs)`

The package is local W3 evidence only. No upload or `/release` occurred; merge,
official release, and fresh artifact-registry retrieval are still required.

## Local finish boundary

- `20260819T025527Z` was interrupted with wrapper RC130 before any Conan build.
  Missing orig/work context sent `refresh-patch` into a same-directory full
  repository scan. The preserved log SHA-256 is
  `acc9d2883fae3b4ff3fdc54ebd7097759b427058c9e6cc78b77728316c5ff9de`.
- `20260819T031657Z` reached Conan G2 but was interrupted with wrapper RC120
  when a read-only process check exposed `meson compile -j24` and Ninja
  `-j 24`. That run is not accepted under the single-job rule. Its log
  SHA-256 is
  `1637c06254a15a31e6203b1411e5e2fa8f99dddbe054a628e2e1512f7bdf3c89`.
- `20260819T032711Z` used a fresh task-only Conan home whose `global.conf`
  SHA-256 is
  `26e23d2b124ca4bfe6d42de1375288abdaa5ebc1524fa60e545aa03089d9c152`.
  Both host and build profiles read back `tools.build:jobs=1`; live process
  checks saw `meson compile -j1` and Ninja `-j 1`. Conan G2 and the embedded
  local CI gate passed, producing `.ci-result.json` SHA-256
  `319ac818b4e1d8339f6d7abaa25c8f3892eaa35e9c293042650391b214c91810`.
- The accepted local finish wrapper still returned RC1. The nonblocking G0
  clean verifier could not execute `/data/service/hnp/bin/bash`,
  `gen_summary` raised `'str' object has no attribute 'append'`, and the old
  readiness check requested legacy `packaging/` and `.staging-verified`.
  These framework/local-environment results are preserved and are not called
  PASS. The full finish log SHA-256 is
  `7dcaf57a0454f93f383fd7c5ea5a86f3b9a27ae4254360bc8eb0c1626b97cff5`.

The Linux finish run is only a local CI gate. It does not replace r7's native
OHOS/arm64 evidence or the current PR HEAD's official CI.
---

**编译结束**: 2026-08-19 11:27
**最终状态**: built
