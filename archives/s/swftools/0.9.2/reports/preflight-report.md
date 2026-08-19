# swftools 0.9.2 preflight report

Date: 2026-08-14

Issue: #2168

Scope: host-side preparation and single-package OHOS shadow CI

| Check | Result | Evidence |
|---|---|---|
| Worktree isolation | PASS | `D:\harmonyos\worktrees\swftools`, branch `feat/swftools-0.9.2-2168` |
| Source download | PASS | MacPorts mirror returned 2,675,939-byte archive |
| Source SHA256 | PASS | `bf6891bfc6bf535a1a99a485478f7896ebacbe3bbf545ba551298080a26f01f1` |
| Build-system analysis | PASS | In-source Autotools; `configure.in` and generated `configure` present |
| W0 required dependency | PASS | `zlib/1.3.1` recipe revision `2ee7c0eeb8f4dfef8982d0c5c1551a61` downloaded from `ohpcd` |
| Optional dependency policy | PASS | Optional probes disabled; no dependency adaptation mixed into issue #2168 |
| Patch dry-run | PASS | GNU `patch --dry-run -p1` and Conan `patch-ng` (`fuzz=false`) applied all four patches in order |
| Conan source | PASS | `conan source` downloaded and verified the archive using the recipe |
| Conan recipe load/export | PASS | Python/YAML parse, `conan inspect`, `conan export`, and a valid Linux dependency graph completed |
| Native/OHOS build | PASS | R7 built `swftools/0.9.2` for OHOS on the connected device |
| Package contents | PASS | 13 signed command-line tools were present in the Conan package |
| test_package runtime | PASS | `swfc` compiled `smoke.sc`; `swfdump` parsed the result and verified version/frame data |
| Shadow CI gates | PASS | G0 and L0/L1/L2/L4/L5 passed; summary reported `Total: 1`, `Success: 1`, `Failed: 0` |

The host dependency graph resolves `zlib/1.3.1`; its Linux/GCC binary is
reported missing, which is expected because this round validates the published
recipe and does not build a non-OHOS substitute.

## Shadow CI evidence

- Code revision: `62dba31e0de7a5c620b725b4eaf3e7dc789eb0d9`
- Standard run: `/storage/Users/currentUser/ohos-test-runs/codex-swftools-issue2168-shadow-ci-r7-20260814-215337-18784`
- Shadow run: `/storage/Users/currentUser/ohos-users/codex/swftools-0.9.2-2168-42b6d61a68-20260814-1808/ohpc-ci-shadow/runs/codex-swftools-issue2168-shadow-ci-r7-20260814-215337-18784`
- Recipe revision: `a1f4bd8e1c55a6d884a0469da3efae86`
- Package ID: `d19813127f0ec2ca84c0b48cbd85080965097448`
- Package revision: `2102587fdcd1a5acf5da7fb5a20d0cdf`

The exact package reference created by R7 is:

```text
swftools/0.9.2#a1f4bd8e1c55a6d884a0469da3efae86:d19813127f0ec2ca84c0b48cbd85080965097448#2102587fdcd1a5acf5da7fb5a20d0cdf
```
