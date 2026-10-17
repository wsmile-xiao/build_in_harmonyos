# kicad-templates 10.0.0 verification report

Date: 2026-09-20

## Result

Package-level OHOS verification passed for the connected HarmonyOS 6.0 x86_64
VM. A real Conan package was created with the local OpenHarmony x86_64
cross-toolchain, its test package was rebuilt by `conan test`, and the exact
Conan-installed resource tree plus the generated OHOS probe passed in the VM:
`SUMMARY named=20 passed=20 failed=0 deferred=0`. The repository's standard
aarch64 profile was not run because this VM exposes an x86_64 PC target and the
standard `/data/service/hnp` paths are not present on this Windows host.

Windows-safe static checks, repository preflight, source/resource census, and
the host consumer probe ran. The host probe produced
`SUMMARY named=20 passed=19 failed=0 deferred=1`; this is host-only evidence.

## Inputs and profile

- Official source SHA-256:
  `3d188b0c1cda84dfa11ef9e6bbf4cb5b509ba68555bd6e4d8d7224ddd1112880`.
  This is the pinned and previously Conan-validated archive hash preserved in
  `conandata.yml`; the fresh standalone download was blocked by this host's
  network sandbox.
- Conan: 2.29.1.
- Profile: `ci/conan/profiles/ohos-aarch64` for both host and build.
- Profile settings: `os=OHOS`, `os.version=6.0`, `arch=armv8`,
  `compiler=clang`, `compiler.version=15`, `compiler.libcxx=libc++`,
  `compiler.cppstd=17`, `build_type=Release`.
- Profile compiler paths: `/data/service/hnp/bin/clang` and
  `/data/service/hnp/bin/clang++`.
- Package ID selected by Conan:
  `da39a3ee5e6b4b0d3255bfef95601890afd80709`.
- VM validation profile: `tmp/conan-profiles/ohos-x86_64-cross`, targeting
  `os=OHOS`, `os.version=6.0`, `arch=x86_64`, with the OpenHarmony 26.0.0
  clang 15.0.4 SDK and CMake toolchain.

## Test census and installed-resource evidence

- Upstream tests: 0. The resource-only upstream project has no test entry.
- Consumer checks: 20 named checks.
- Official source census: 19 projects, 20 canonical top-level worksheet
  names, and recursive counts 19 PCB / 19 SCH / 19 PRO / 36 WKS.
- A host installation-shaped fixture assembled with upstream's project-copy
  and flattened worksheet semantics contained 177 files.
- Host result: `SUMMARY named=20 passed=19 failed=0 deferred=1`, exit 0.
- Native OHOS result from the Conan-installed package:
  `SUMMARY named=20 passed=20 failed=0 deferred=0`, exit 0.
- Conan package installed-file count: 177 files in the validated
  `share/kicad/template` resource tree.

## Package and verifier commands

```text
python -X utf8 scripts/ohc-run.py conan-verify kicad-templates 10.0.0 --profile ohos-aarch64 --project-dir C:\Users\ASUS\AppData\Local\Temp\kicad-conan-verify-detail-f0946d6568f24c578c0c60651e086c9a
exit 1; G1 PASS, G2 blocked by absent /bin/sh on Windows
```

After the standard no-patch Conan hooks were added, the repository verifier's
G1 recipe-completeness gate passed. A fresh Windows run then reached G2 and
returned 1 before launching Conan because the verifier executes its generated
command through `/bin/sh`, which is absent on this Windows host
(`[WinError 2]`). This host-tooling result is neither a recipe failure nor
package success. The connected VM was validated separately with the local
x86_64 OpenHarmony SDK profile below.

```text
conan create archives/k/kicad-templates/10.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=kicad-templates/* -c tools.build:jobs=4
first sandboxed attempt: exit 7 (Conan cache write denied)
normal-cache rerun: exit 1
```

The fresh normal-cache run exported recipe revision
`fabcd9de546dffa3cb166e6334a1850b`, called both standard no-patch hooks (each
reported that no patches are defined), resolved the profile, selected the
platform-neutral package ID, downloaded the verified source, and generated the
Conan CMake toolchain and environment files. It then failed at
`CMake.configure()` with `ConanException: Error 1 while executing` because this
host lacks the repository's standard `/data/service/hnp` environment. The
local OpenHarmony SDK cross profile below was used for the successful package
build and test-package compilation.

```text
conan create archives/k/kicad-templates/10.0.0 -pr:h=C:\Users\ASUS\Desktop\build_in_harmonyos\tmp\conan-profiles\ohos-x86_64-cross -pr:b=C:\Users\ASUS\Desktop\build_in_harmonyos\tmp\conan-profiles\windows-mingw --build=kicad-templates/* -c tools.build:jobs=1
exit 0; package created with 177 installed resource files

conan test archives/k/kicad-templates/10.0.0/test_package kicad-templates/10.0.0 -pr:h=C:\Users\ASUS\Desktop\build_in_harmonyos\tmp\conan-profiles\ohos-x86_64-cross -pr:b=C:\Users\ASUS\Desktop\build_in_harmonyos\tmp\conan-profiles\windows-mingw --build=never --no-remote
exit 0; test package rebuilt and executed through the VM runner; `SUMMARY named=20 passed=20 failed=0 deferred=0`
```

The final cross-build test used the following explicit runner setting. The
runner transfers the Conan-installed `share/kicad/template` tree and the
generated OHOS probe to the connected HarmonyOS 6.0 x86_64 VM through `hdc`,
then returns the probe exit code:

```text
KICAD_TEMPLATES_VM_RUNNER=powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\ASUS\Desktop\build_in_harmonyos\tmp\run-kicad-templates-probe-vm.ps1
```

The native OHOS rerun command is exactly:

```sh
conan create archives/k/kicad-templates/10.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 '--build=kicad-templates/*' -c tools.build:jobs=4
```

Run it in the HarmonyOS 6.0 VM with CMake and the configured
`/data/service/hnp` compiler paths, and require the 20/20 summary above.

The final `conan test` transferred the generated
`test_package/build/clang-15-x86_64-17-release/kicad_templates_probe` and the
Conan package's installed resource directory to the connected VM. Running
that exact pair produced the native OHOS 20/20 summary.

## Consumer and reversible failure evidence

The probe was compiled with:

```text
D:\mingw64\bin\g++.exe -std=c++17 -Wall -Wextra -Wpedantic -Werror archives\k\kicad-templates\10.0.0\test_package\kicad_templates_probe.cpp -o tmp\kicad_templates_probe.exe
exit 0
```

The host fixture run exited 0 with 19 passes and one explicitly deferred OHOS
check. The `rejects_truncated_s_expression` check now writes a truncated PCB
fixture inside a unique temporary directory, validates it through the same
file-reading function used for installed PCB/SCH/WKS resources, rejects it,
and removes the temporary directory through scoped cleanup. For the
supplemental reverse test, the exact fixture directory
`share/kicad/template` was moved to the sibling `template.relocated`, the same
probe was run against the now-missing original path, and a `finally` block
restored the directory. The reverse run exited 1 with
`SUMMARY named=20 passed=4 failed=15 deferred=1`; restoration was then verified
as true with all 177 files present.

This proves the consumer's missing-resource failure behavior and reversible
cleanup on the host fixture. The corresponding Conan-package resource tree
was also tested in the VM: moving the installed resource directory aside
produced a nonzero probe result, and restoring it returned the same probe to
20/20.

### Conan-package reverse-resource VM test

The observed VM result for the package returned by `conan cache path` was:

```text
REVERSE_VM_EXIT=1
SUMMARY named=20 passed=4 failed=16 deferred=0
RESTORED_VM_EXIT=0
SUMMARY named=20 passed=20 failed=0 deferred=0
```

For a VM that has Conan itself installed, the repository also provides the
following complete reverse-Conan procedure. The package ID is read from
Conan's JSON metadata, and `conan cache path` resolves the installed package
directory. The script checks
the exact resource suffix before moving only `share/kicad/template` to a
unique temporary backup. The reverse run is captured in a temporary log and
must show the probe's 20-check summary plus concrete missing-resource failures.
The EXIT/signal traps restore the directory on every exit; after the expected
failure, the script restores explicitly and reruns the same consumer to require
the native OHOS 20/20 summary. No cache cleanup command is used.

```sh
set -eu

repo_root="$(pwd -P)"
recipe_ref='kicad-templates/10.0.0'
profile="$repo_root/ci/conan/profiles/ohos-aarch64"
test_context="$repo_root/archives/k/kicad-templates/10.0.0/test_package"

package_id="$(
  conan list "$recipe_ref:*" --format=json |
    python3 -c 'import json, sys
data = json.load(sys.stdin)["Local Cache"]["kicad-templates/10.0.0"]["revisions"]
ids = sorted({pid for rev in data.values() for pid in rev.get("packages", {})})
if len(ids) != 1:
    raise SystemExit(f"expected exactly one cached package ID, found {ids}")
print(ids[0])'
)"
package_ref="$recipe_ref:$package_id"
package_root="$(conan cache path "$package_ref")"
resource_dir="$package_root/share/kicad/template"

case "$resource_dir" in
  "$package_root"/share/kicad/template) ;;
  *) echo "unsafe resource path: $resource_dir" >&2; exit 2 ;;
esac
[ -d "$resource_dir" ] || {
  echo "missing installed resource directory: $resource_dir" >&2
  exit 3
}

backup_root="$(mktemp -d "${TMPDIR:-/tmp}/kicad-templates-reverse.XXXXXX")"
backup_dir="$backup_root/template"
reverse_log="$backup_root/reverse.log"
restored_log="$backup_root/restored.log"
moved=0
restoration_reported=0

restore_resource() {
  if [ "$moved" -eq 1 ]; then
    if [ -e "$resource_dir" ]; then
      echo "refusing to overwrite during restore: $resource_dir" >&2
      return 1
    elif mv -- "$backup_dir" "$resource_dir"; then
      moved=0
    else
      echo "restore failed: $resource_dir" >&2
      return 1
    fi
  fi
  if [ ! -d "$resource_dir" ]; then
    echo "restoration verification failed: $resource_dir" >&2
    return 1
  fi
  if [ "$restoration_reported" -eq 0 ]; then
    echo "RESTORE_OK resource_dir=$resource_dir"
    restoration_reported=1
  fi
}

cleanup() {
  status=$?
  trap - EXIT HUP INT TERM
  if ! restore_resource; then
    status=1
  fi
  rm -f -- "$reverse_log" "$restored_log"
  rmdir "$backup_root" 2>/dev/null || status=1
  exit "$status"
}

run_consumer() {
  conan test . "$recipe_ref" \
    -pr:h="$profile" \
    -pr:b="$profile" \
    --build=never \
    --no-remote
}

require_log_line() {
  expected="$1"
  log_file="$2"
  if ! grep -F -- "$expected" "$log_file" >/dev/null; then
    echo "missing required probe output: $expected" >&2
    return 1
  fi
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

mv -- "$resource_dir" "$backup_dir"
moved=1

cd "$test_context"
set +e
run_consumer >"$reverse_log" 2>&1
consumer_rc=$?
set -e
cat "$reverse_log"
echo "REVERSE_CONAN_EXIT=$consumer_rc"

if [ "$consumer_rc" -eq 0 ]; then
  echo "reverse-Conan test unexpectedly succeeded with resources absent" >&2
  exit 4
fi
require_log_line 'SUMMARY named=20 ' "$reverse_log"
require_log_line '[FAIL] resource_root_exists' "$reverse_log"
require_log_line '[FAIL] official_project_directories' "$reverse_log"
require_log_line '[FAIL] recursive_pcb_count' "$reverse_log"

restore_resource

set +e
run_consumer >"$restored_log" 2>&1
restored_rc=$?
set -e
cat "$restored_log"
echo "RESTORED_CONAN_EXIT=$restored_rc"

if [ "$restored_rc" -ne 0 ]; then
  echo "restored Conan consumer failed" >&2
  exit 5
fi
require_log_line 'SUMMARY named=20 passed=20 failed=0 deferred=0' \
  "$restored_log"

exit 0
```

Acceptance evidence is a nonzero `REVERSE_CONAN_EXIT`; a reverse log containing
`SUMMARY named=20` and the required missing-resource `[FAIL]` lines;
`RESTORE_OK`; and a restored rerun with `RESTORED_CONAN_EXIT=0` plus
`SUMMARY named=20 passed=20 failed=0 deferred=0`. The executed VM equivalent
tested the cached package's installed resource tree with the actual
`test_package` probe; it did not substitute the host fixture for Conan.

## Deferred minor

The s-expression parser currently treats an empty top-level `(version)` or
`(generator)` list as satisfying header presence. Tightening header-value
semantics is intentionally deferred because it is outside this fix wave and
is not required for the filesystem-based truncation test. The parser was not
broadened beyond the approved plan.

## Static and local CI evidence

The following checks passed:

```text
python -m py_compile archives/k/kicad-templates/10.0.0/conanfile.py archives/k/kicad-templates/10.0.0/test_package/conanfile.py
exit 0

conan inspect archives/k/kicad-templates/10.0.0 -f json
exit 0

conan graph info archives/k/kicad-templates/10.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=kicad-templates/* -f json
exit 0

python -X utf8 scripts/ohc/preflight.py . ba6c5fb998 HEAD
exit 0; PF1-PF9+R52 passed

ci/scripts/preflight_check.sh kicad-templates/10.0.0
exit 0 with a scratch Python shim; no Conan dependencies declared

ci/scripts/knowledge_check.sh .
exit 0; KC1-KC5 passed
```

`python -X utf8 tests/run_all.py` returned 1: 11 of 12 test files passed, while
`test_v1220.py` stopped after its early checks because it hard-codes the native
OHOS Git path `/data/service/hnp/git.org/git_2.45.2/bin/git`, absent on Windows.
The focused rerun returned the same host blocker. No kicad consumer assertion
failed in that repository suite.

`ci/scripts/junk_check.sh .` returned 1 because this checkout has no
`origin/main`; it fell back to all 26,741 tracked files and reported three
pre-existing archive marker files plus a 2,122-package atomicity count. The
focused Python preflight above passed for this feature range.

The CI-native `ci/conan/build_and_test.sh` was not runnable because it requires
zsh and a native OHOS execution machine; `zsh` is absent on this host. Its
package build responsibility is represented by the explicit `conan create`
attempt and remains blocked at the same native environment boundary.

## Integrity policy

`.ci-result.json` was neither created nor edited. No Conan/source cache or user
data was deleted. Scratch source material was copied read-only from the Conan
cache, and all relocation occurred only inside the task scratch fixture.

## Final post-edit validation

These commands were run from the repository root against the final edited
versions of the three Task 4 deliverables, immediately before the fix commit.

```powershell
python -X utf8 -c "from pathlib import Path; import yaml; files=[Path(r'archives/k/kicad-templates/10.0.0/conandata.yml'),Path(r'archives/k/kicad-templates/10.0.0/manifest.yaml'),Path(r'archives/k/kicad-templates/10.0.0/test_package/MANIFEST.yml')]; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in files]; print(f'YAML_OK files={len(files)}')"
```

Observed output: `YAML_OK files=3`; exit code: `0`.

```powershell
python -X utf8 -c "from pathlib import Path; files=[Path(r'archives/k/kicad-templates/10.0.0/reports/test-report.md'),Path(r'archives/k/kicad-templates/10.0.0/notes.md'),Path(r'archives/k/kicad-templates/10.0.0/test_package/MANIFEST.yml')]; tokens=('T'+'BD','TO'+'DO','FIX'+'ME','REPLACE'+'_ME','<'+'hash>','<'+'count>'); hits=[(str(p),token) for p in files for token in tokens if token.lower() in p.read_text(encoding='utf-8').lower()]; print(f'TOKEN_SCAN_OK files={len(files)} matches={len(hits)}'); raise SystemExit(bool(hits))"
```

Observed output: `TOKEN_SCAN_OK files=3 matches=0`; exit code: `0`.

```powershell
git diff --check -- archives/k/kicad-templates/10.0.0/reports/test-report.md archives/k/kicad-templates/10.0.0/notes.md archives/k/kicad-templates/10.0.0/test_package/MANIFEST.yml
```

Observed output: none; exit code: `0`.

## PR documentation

The draft PR body is stored in `reports/pr-body.md` and follows
`templates/积分赛事PR模板.md` in order. It carries forward the observed host
summary, the successful x86_64 HarmonyOS VM result, and the standard aarch64
profile limitation without promoting target values to results. This report
remains the command-level evidence authority, including the exact VM command
and the complete trap-based restoration procedure above.
