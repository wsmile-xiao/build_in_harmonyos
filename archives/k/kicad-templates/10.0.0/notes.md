# kicad-templates 10.0.0 HarmonyOS verification notes

## Current state

The package recipe, metadata, and 20-check consumer contract are verified.
Using the local OpenHarmony SDK 26.0.0 x86_64 cross profile, Conan created the
package and rebuilt the test package. The generated probe and the exact Conan
package resource tree passed in the HarmonyOS 6.0 x86_64 VM. The final
`conan test` uses `KICAD_TEMPLATES_VM_RUNNER` for the cross-built OHOS binary;
it fails if the runner is missing rather than silently skipping execution.

The preserved official source SHA-256 is
`3d188b0c1cda84dfa11ef9e6bbf4cb5b509ba68555bd6e4d8d7224ddd1112880`.
The source census is 19 projects, 20 canonical top-level worksheets, and
19/19/19/36 recursive PCB/SCH/PRO/WKS files. An installation-shaped host
fixture contained 177 files.

## Test results

- Upstream tests: 0; upstream provides no executable test entry.
- Host consumer: `SUMMARY named=20 passed=19 failed=0 deferred=1`, exit 0.
- Supplemental missing-resource run: exit 1; the temporarily relocated
  `share/kicad/template` directory was restored with all 177 files.
- Conan package VM reverse-resource run: `REVERSE_VM_EXIT=1` with
  `SUMMARY named=20 passed=4 failed=16 deferred=0`; restored rerun returned
  `RESTORED_VM_EXIT=0` with `SUMMARY named=20 passed=20 failed=0 deferred=0`.
- Native OHOS target: `SUMMARY named=20 passed=20 failed=0 deferred=0`, exit 0.
- Explicit `conan test` returned 0; it rebuilt the OHOS test package and used
  `KICAD_TEMPLATES_VM_RUNNER` to execute the generated probe in the VM, with
  `SUMMARY named=20 passed=20 failed=0 deferred=0`.
- Repository recipe completeness G1 and package static checks passed. The full
  verifier reached G2 but its generated command requires `/bin/sh`, absent on
  this Windows host, so it returned 1 without producing a package. The broader
  repository test runner's only stopped file requires the native OHOS Git path;
  the shell junk check also fell back to the entire historical repository
  because this checkout has no `origin/main`.

## Standard aarch64 VM rerun

```sh
conan create archives/k/kicad-templates/10.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  '--build=kicad-templates/*' \
  -c tools.build:jobs=4
```

The connected VM is x86_64, so the standard aarch64 profile above remains an
additional target to validate when its `/data/service/hnp` toolchain is
available. The x86_64 package validation and reversible resource test are
recorded in `reports/test-report.md`. Do not delete or clear any Conan cache.

## Deferred minor

Empty top-level `(version)` or `(generator)` lists can still satisfy the
s-expression parser's header-presence check. That value-semantics tightening is
outside this fix wave and was deliberately deferred; the filesystem truncation
test did not require broadening the parser.

## Final validation

The final edited Task 4 files passed YAML parsing (`YAML_OK files=3`), the
six-token unfinished-value scan (`TOKEN_SCAN_OK files=3 matches=0`), and
`git diff --check`; each command exited `0`. The exact commands and observed
outputs are recorded in `reports/test-report.md` under “Final post-edit
validation.” These checks complement the successful Conan/OHOS x86_64 VM
validation above.

## Draft PR documentation

`reports/pr-body.md` is the package-facing draft organized from the repository
competition PR template. It deliberately reports the host fixture as
`SUMMARY named=20 passed=19 failed=0 deferred=1` plus the observed
`SUMMARY named=20 passed=20 failed=0 deferred=0` from the Conan package in the
HarmonyOS VM. The standard aarch64 profile remains separately documented as
requiring its native `/data/service/hnp` environment.
