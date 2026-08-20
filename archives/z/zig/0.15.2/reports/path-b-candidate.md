# zig 0.15.2 Path B Candidate

## Application

- Applicant: `xuguowei`
- Team: `Beidou Star`
- Date: 2026-08-17
- Package: `zig/0.15.2`
- Issue: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2235
- Branch: `feat/zig-0.15.2-2235`
- Requested path: Path A (base adaptation) + Path B (knowledge contribution candidate)

The final classification remains subject to project review. This report does
not claim Path C or complete upstream Zig test-suite coverage.

## Why Path B Applies

Zig is both a packaged executable and a build-system tool. On HarmonyOS,
signing only the official Zig ELF is insufficient: `zig build`, `zig build
run`, and `zig build test` generate new ELF build runners and applications and
execute them immediately. Those generated files initially fail with
`AccessDenied` until they are signed.

Zig 0.15.2 also exposed a separate hmdfs constraint. Generated shell command
wrappers had executable mode bits but could not be executed directly under the
SSH/Conan identity. The signed `zig-real` ELF worked, and invoking the wrapper
through `/system/bin/sh` worked, proving that the failure was at the script
entry rather than inside Zig.

The package adds a reusable two-layer execution design:

1. `zig-real` is the official aarch64 Zig ELF and is self-signed.
2. `zig` and `zig-ohos-sign-generated` are signed PIE launchers compiled with
   the device Clang.
3. Each launcher resolves `/proc/self/exe` and invokes its sibling `.sh`
   implementation through `/system/bin/sh`.
4. The Zig wrapper detects `AccessDenied`, signs executable ELF files in the
   cache/output roots, and retries the original command.
5. `ZIG_OHOS_SIGN_ROOTS` and `zig-ohos-sign-generated` expose the behavior to
   downstream Zig-based Conan recipes without duplicating signing logic.

This is a reusable execution bridge for command scripts and generated Zig ELF
files on HarmonyOS hmdfs, not a package-specific build flag.

## Increment Beyond Zig 0.16.0

The repository already contains a Zig 0.16.0 Path B candidate with generated
ELF signing/retry. This submission does not claim that existing mechanism as
new work. Its incremental contribution is:

- diagnosing direct script execution failure independently of mode bits;
- replacing public shell entries with signed ELF launchers while retaining
  their shell implementations and command names;
- adapting the approach to Zig 0.15.2's different standard-library layout;
- changing the 0.15.2 `std/Build.zig` default test-runner mode without carrying
  the inapplicable 0.16 `Io/Threaded.zig` patch;
- proving reuse through a real downstream `ncdu2/2.9.2` build and test run.

## Failure Evolution

The first isolated device `conan create` downloaded, verified, patched, and
packaged the official aarch64 distribution. `zig-real version` returned
`0.15.2`, but the public shell wrapper failed immediately:

```text
/system/bin/sh: .../bin/zig: Permission denied
```

Direct probes established the boundary:

- signed `zig-real` executed and returned `0.15.2`;
- `/system/bin/sh bin/zig version` returned `0.15.2`;
- direct execution of `bin/zig` failed despite executable mode bits.

After replacing the public script entries with signed ELF launchers, the
isolated Conan job completed with exit code 0. The first generated Zig build
runner and smoke executable produced the expected `AccessDenied`; the wrapper
signed them and retried. The final summary was:

```text
Build Summary: 5/5 steps succeeded
run success
install success
```

## Test Accounting

The recipe packages the official Zig binary distribution instead of building
the Zig compiler from source. The complete upstream compiler test suite was
not executed on HarmonyOS and is not counted as passed.

| Type | Count | Result | Coverage |
|---|---:|---:|---|
| Version execution | 1 | PASS | Exact `zig version` output `0.15.2` |
| Build integration | 1 | PASS | Generate and compile through `build.zig` |
| Generated ELF execution | 1 | PASS | Run the generated smoke executable |
| Install workflow | 1 | PASS | Install into `zig-out/bin` |
| Installed artifact execution | 1 | PASS | Run the installed executable |
| **Total** | **5** | **5/5 PASS** | Zig build/run/install workflow |

No upstream test file was weakened or modified. The package applies an
OHOS-only default-runner patch to the distributed standard library; explicit
upstream server-mode requests remain honored.

## Device Evidence

Shadow CI gate run:

```text
RUN_DIR=/storage/Users/currentUser/ohos-test-runs/codex-zig-0.15.2-2235-shadow-ci-r2-20260817-091735-40486
verified_commit=2e179b21575eaa0df70dd86e52b337198e37737a
setup_rc=0
L0_RESULT=fail: gate failed: commands_json_r38
L1/L2/L4/L5=skip: blocked_by_L0
```

The L0 failure is metadata-only: the software-level
`archives/z/zig/commands.json` does not list 0.15.2 and was outside the allowed
version-directory scope. It is not presented as a successful shadow CI run.

Isolated package and consumer run:

```text
RUN_DIR=/storage/Users/currentUser/ohos-test-runs/codex-zig-0.15.2-2235-conan-create-r2-20260817-091835-41071
exit_code=0
recipe_revision=501adb6c2fb136f4a58e15a2cb2d2412
package_id=876049f3ae10a4560da345bb02378e03e212bc8c
package_revision=dc58c1e12eb784152e7cee847e6fae59
```

Full package reference:

```text
zig/0.15.2#501adb6c2fb136f4a58e15a2cb2d2412:876049f3ae10a4560da345bb02378e03e212bc8c#dc58c1e12eb784152e7cee847e6fae59
```

Downstream reuse proof:

```text
package=ncdu2/2.9.2
RUN_DIR=/storage/Users/currentUser/ohos-test-runs/codex-ncdu2-2.9.2-2233-conan-create-r1-20260817-094126-49916
exit_code=0
upstream_zig_tests=13/13 PASS
consumer_test=PASS (version, help, deterministic scan, JSON export)
```

The downstream test used the validated Zig package through Conan cache
save/restore; no Zig source or recipe change was mixed into the ncdu2 branch.

## Reuse Contract

A downstream Zig-based recipe normally needs only:

```python
self.tool_requires("zig/0.15.2")
```

For non-standard output roots it can set `ZIG_OHOS_SIGN_ROOTS` or call:

```sh
zig-ohos-sign-generated <ROOT_OR_FILE>...
```

## Known Limits And Next Gate

- The complete Zig upstream test suite has not been executed on HarmonyOS.
- Standard shadow CI is still blocked by the out-of-version-directory R38
  metadata requirement; L0-L5 must be rerun after that scope is resolved.
- The package is not yet published to `ohpcd`; remote-only downstream builds
  remain blocked until publication.
- Path B is submitted as a candidate and requires project approval.
