# sfic 0.1.7 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (musl)
- Clang (OHOS toolchain, via CI profile `ohos-aarch64`)
- Conan 2.29.1 (OHOS-adapted), remote: ohpcd

## Verification

- `conan create archives/s/sfic/0.1.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="sfic/*"`: exit 0
- `CI_PACKAGES="archives/s/sfic/0.1.7" zsh ci/conan/build_and_test.sh` (with PR diff): exit 0
- G0: passed
- KC: passed (KC1-KC5, 0 errors)
- JC: passed (JC1-JC6, 0 errors; single-software atomicity OK)
- L0: passed (L0i dependency tdb/1.4.15 in registry, L0j no version collision, L0k commands.json, L0m structure, L0h, L0q)
- L1: passed (make check executed in build() — log evidence present; test_package 7/7)
- L1e R34 negative test: passed (bin/ moved away → test.sh fails as expected, rc=1)
- L2: passed (`timeout 15 bin/sfic --version` → `sfic 0.1.7`, rc=0, no LD_LIBRARY_PATH needed — RPATH embedded)
- L4: passed (PIE + NOW/BIND_NOW + GNU_RELRO + NX stack; patches clean)
- L5: passed (bin/ has content)

## Upstream tests

sfic 0.1.7 ships **no test cases**: the autotools `check` target exists but
`src/Makefile.am` defines no TESTS/TESTS_SCRIPTS, so `make check` runs and
exits 0 with "Nothing to be done for 'check'". It is still invoked in
`build()` (log evidence for the L1c gate). No upstream test suite exists to
run; the reason is documented in notes.md and manifest.yaml.

## Dependency tests (tdb/1.4.15)

The hard runtime dependency tdb/1.4.15 (published in the ohpcd registry)
runs its complete upstream test suite during its own recipe build:
`make test`, 37 test programs, all passing on armv8/OHOS.

## test_package (consumer test)

The consumer test drives the installed sfic CLI as an end user:

1. `sfic --version` exits 0 (prints `sfic 0.1.7`)
2. `sfic -h` help text contains `simple file integrity checker`
3. `sfic -a DB1 -R <dir>` recursively builds a tdb metadata database
4. `sfic -l DB1` lists all recorded paths (verified: a.txt, sub/b.txt)
5. rebuild identical DB2, `sfic -n DB2 -o DB1` → exit 0 (no changes)
6. modify the tree, rebuild DB3, `sfic -n DB3 -o DB1` → non-zero exit and
   the modified path is reported (change detection)
7. db files exist on disk and the changed db differs from the original

- Test cases: 7
- Passed: 7
- Failed: 0
- Skipped: 0
- Pass rate: **100% (7/7)**

## Platform CI (build_in_harmonyos CI wall)

- Build #53218 (PR #11214, worker CI-007): **CI 校验通过** —
  Conan test_package: 通过, L0 门禁 (结构完整性): 通过
- Build #53336 (PR #11214, worker CI-007): **CI 校验通过** — 同上
- Note: earlier builds failed on the CI cluster with
  `fork failed: out of memory` in the G0 step (worker infrastructure
  OOM, conan build never started); both 2026-09-20 builds on worker
  CI-007 pass end-to-end.

## Result

The recipe was verified end-to-end on an OpenHarmony aarch64 device
(conan create + full CI gate simulation) and is eligible for `published`
status.
