# libxft 2.3.9 adaptation notes

## Source and dependency boundary

- The official X.Org xz archive has SHA-256
  `60a25b78945ed6932635b3bb1899a517d31df7456e69867ffba27f89ff3976f5`.
- The independently downloaded official xz and gzip archives contain the same
  129-file source tree.
- Fresh isolated OHOS/arm64 W0 passed for all 12 dependency nodes with
  `--build=never`, complete RREV/PID/PREV values, `binary_remote=ohpcd`, no
  missing binary, and empty `info_invalid`.
- Direct dependencies are `libx11/1.8.13`, `libxrender/0.9.12`,
  `fontconfig/2.18.3`, `freetype/2.14.3`, and `xorgproto/2025.1`.

## Build design

The recipe uses the upstream Meson build and does not modify the source. The
shared `libXft.so.2` ABI is preserved. Conan-generated pkg-config metadata is
named to match the exact upstream dependency probes (`freetype2` and
`xproto`), and the installed `xft.pc` prefix is made relocatable.

## Test inventory

The release has no Automake `TESTS`, `check_PROGRAMS`, `check-local`, or Meson
`test()` entry, so the truthful upstream total is 0/0. The installed-package
suite has two independent consumers: one binds all 77 public functions and
checks version/FreeType initialization; the other checks Fontconfig name and
valid/invalid XLFD contracts. Together they contain 95 assertions.

## Current state

Official finish r10 exposed a recipe defect after all 96 Meson build
steps: HMDFS materialized `libXft.so.2` as a byte-identical regular file with
mode `0770`, while the source file had mode `0750`. Exact mode equality rejected
the safe group-write projection. The repaired contract preserves owner and
read/execute bits, permits only the HMDFS-added group-write bit, and still
rejects world-write and special bits. The production and test-package directed
matrix passed 14/14.

Fresh isolated W0 r14 passed for the repaired candidate with all 12 nodes,
five direct binary retrievals, `Missing=0`, and `info_invalid=0`. W3 r25 then
failed locally before SSH because a .NET-started Windows PowerShell child
inherited the PowerShell 7 module path and could not autoload `Get-FileHash`.
It remained unconsumed with `launch_count=0` and no remote effects.

The create-new r26 controller isolates the legacy Windows PowerShell module
roots. Its exact regression passed, and its single real-device transaction
built shared and static packages, passed upstream `0/0`, consumers `2/2`,
variant executions `4/4`, and 95 assertions. It used one launch on
`10.62.148.108:2222`, preserved the evidence archive, reported zero owned
remote processes, verified release, and passed two postrelease clean scans.
The current W3 evidence SHA-256 is
`446fb1e10393f2d961d4bde9b258e5b707e754e6a765b9e4e8b73c61e3b4e6c7`.
Official finish, Pre-PR, platform Review, exact-current-HEAD CI, and submission
remain pending.

Official finish r12 then passed the authoritative Conan create, package
consumers, and local CI gate and generated `.ci-result.json` with exit code 0
and a valid integrity hash. Its aggregate command returned 1 only after W3:
the repository-wide knowledge check reported missing fields in unrelated
existing entries, and the legacy submit-readiness check still required a
`packaging/` tarball that is not part of the current recipe archive contract.
The generated CI result and full failure archive were collected byte-for-byte;
the remote runner was absent, the owned root was removed, and two clean scans
passed. This is recorded truthfully as `partial_post_w3`, not as aggregate RC0.
---

**编译结束**: 2026-08-26 13:51
**最终状态**: built
