# zig 0.16.0.1 HarmonyOS adaptation notes

## Context

- Target package: `zig/0.16.0.1`
- Branch: `feat/zig-0.16.0`
- Worktree: `D:\harmonyos\worktrees\zig`
- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1562
- Trigger: `minizign/0.1.13` declares `minimum_zig_version = "0.16.0"` in `build.zig.zon`. Because `zig/0.16.0` is already published in ohpcd, the OHOS test-runner fix is packaged as `zig/0.16.0.1`; the packaged compiler still reports upstream Zig version `0.16.0`.

## W0 Dependency Check

- `zig/0.16.0` was not present locally or in the minizign W0 notes when the first adaptation started.
- Follow-up check on 2026-08-08 found `zig/0.16.0` already published; CI L0j rejects changing that recipe, so this follow-up uses `zig/0.16.0.1`.
- Zig itself is packaged from the official upstream distribution and has no Conan package dependencies.

## Source And Build-System Analysis

- Official release index: `https://ziglang.org/download/index.json`
- Version date in official index: `2026-04-13`
- Source archive: `https://ziglang.org/download/0.16.0/zig-0.16.0.tar.xz`
- Source sha256: `43186959edc87d5c7a1be7b7d2a25efffd22ce5807c7af99067f86f99641bfdf`
- Bootstrap archive: `https://ziglang.org/download/0.16.0/zig-bootstrap-0.16.0.tar.xz`
- Bootstrap sha256: `2a8266a4205772ef40838c8cbdf14875855a515ff3adf89b49c2d2ae93613d10`
- OHOS package archive: `zig-aarch64-linux-0.16.0.tar.xz`
  - Primary URL: `https://ziglang.org/download/0.16.0/zig-aarch64-linux-0.16.0.tar.xz`
  - Fallback mirrors from Zig official `community-mirrors.txt`:
    - `https://zig.linus.dev/zig/0.16.0/zig-aarch64-linux-0.16.0.tar.xz`
    - `https://pkg.hexops.org/zig/0.16.0/zig-aarch64-linux-0.16.0.tar.xz` was probed but not kept in the final order because the OHOS runner stalled before download progress.
  - Conan URL order prefers mirrors first because the official source was slow on the OHOS runner; official `ziglang.org` remains the final fallback.
  - sha256 remains the official value `ea4b09bfb22ec6f6c6ceac57ab63efb6b46e17ab08d21f69f3a48b38e1534f17`

Zig from source is a compiler/toolchain build. The official release provides a
bootstrap archive plus platform-specific tool distributions. Building from
source would pull a heavy LLVM/LLD/Clang toolchain path, so this front-loaded
dependency package uses the official Zig binary distribution as a Conan build
tool package.

## Packaging Strategy

- `package_type = "application"`
- `package_id()` removes `compiler`, `build_type`, and `os.version`; package ID keeps only runtime `os` and `arch`.
- OHOS `armv8` maps to Zig's official `aarch64-linux` archive.
- Settings-dependent official archive selection is done in `build()` because
  Conan 2 forbids accessing `self.settings` in `source()`.
- The official distribution layout is preserved inside `bin/`, keeping the real
  `zig` executable and the required `lib/` directory as siblings.
- On OHOS, the official Zig ELF is moved to `bin/zig-real`, self-signed with
  `binary-sign-tool`, and kept beside `bin/lib`.
- On OHOS, `bin/zig` is a compatibility wrapper that downstream recipes can
  still call as `zig`. It retries after `AccessDenied` / `Permission denied` /
  `failed to spawn build runner` / `failed to spawn and capture stdio`, signing
  generated executable ELF files under `.zig-cache`, `zig-cache`, and `zig-out`.
  It also signs exact executable paths reported by Zig in `failed command:` and
  `failed to spawn ... AccessDenied` diagnostics, so custom Zig cache
  directories can be handled without every downstream recipe adding bespoke
  signing roots.
- On OHOS, `bin/zig-ohos-sign-generated` is packaged as a reusable helper for
  downstream recipes that need to explicitly sign generated Zig executables in
  custom directories.
- On OHOS, package-time standard-library patching changes Zig 0.16.0
  `std/Io/Threaded.zig` `copy_file_range` / `sendfile` `OVERFLOW` branches from
  panic behavior to `error.Unimplemented`, allowing Zig's existing read/write
  fallback to complete `zig build install` on HarmonyOS.
- On OHOS, package-time standard-library patching also changes the default
  `std.Build.addRunArtifact()` behavior for Zig unit-test artifacts to use the
  terminal exit-code runner instead of Zig 0.16.0's stdio server protocol
  (`--listen=-`). This keeps downstream `zig build test` usable on HarmonyOS,
  where signed test runner ELF files execute normally but the server protocol
  can stall waiting for a response.
- Software-level `commands.json` is present for R38 tool package compliance.

This is specifically to avoid downstream dependency gaps: recipes such as
`minizign/0.1.13` and later Zig-based recipes should use
`self.tool_requires("zig/0.16.0.1")` when they need the OHOS generated
test-runner fixes. Compiler or build type profile changes should not create new
Zig binary IDs.

## Test Package

Prepared tests:

1. Run `zig version` and assert exact output `0.16.0`.
2. Copy a tiny Zig project with `build.zig` and `smoke.zig` into the test work
   directory.
3. Run `zig build run install --summary all -Doptimize=ReleaseSmall`.
4. The OHOS/Linux shell test uses custom `ZIG_GLOBAL_CACHE_DIR` and
   `ZIG_LOCAL_CACHE_DIR` paths to cover downstream recipes that do not use
   Zig's default `.zig-cache` location.
5. Assert `zig-out/bin/smoke` exists after the install step.
6. On Windows, run the installed executable directly once more.

Upstream full tests are not run in this recipe because this recipe packages the
official Zig distribution rather than building Zig itself.

## Local Verification

Current session verification:

- Official Zig 0.16.0 index fetched successfully and sha256 values recorded in `conandata.yml`.
- Worktree created from `origin/main` on branch `feat/zig-0.16.0`.
- `conan inspect .`: passed.
- `conan graph info .` for OHOS/armv8: passed.
- Package ID invariant check: OHOS/armv8 Release and Debug both produced package ID `876049f3ae10a4560da345bb02378e03e212bc8c`; changing build-profile compiler version also kept the same package ID.
- `conan download "zig/0.16.0" -r=ohpcd --only-recipe`: still unavailable before this PR, remote returned `system acceleration policy not enabled`.
- `conan create . --user=ohpcd --channel=stable --build=missing` on Windows x86_64: passed with `zig-x86_64-windows-0.16.0.zip` downloaded from `https://zig.linus.dev/zig/0.16.0/` with official sha256 verification.
  - The test ran `zig version` and got `0.16.0`.
  - The test ran `zig build run install --summary all -Doptimize=ReleaseSmall`.
  - Zig reported `Build Summary: 5/5 steps succeeded`; the generated executable ran successfully and `install` produced `zig-out/bin/smoke`.
- `conan create . --build=missing` without user/channel was also started to mirror CI's unset `CONAN_USER/CONAN_CHANNEL` behavior, but the local Windows run hit the tool timeout while creating a separate cache entry. It is not counted as an OHOS or recipe failure; CI/shadow should run the targeted command below.
- First OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-011848-38237` reached CI L0 and failed at `L0c: No test source files in test_package/`. The initial test generated Zig source dynamically; the recipe was updated to include a real `test_package/smoke.zig` source file for CI static checks.
- Second OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-012040-39010` still failed L0c because the CI source-file allowlist only includes `.c/.cpp/.cc/.cxx/.sh/.py`, not `.zig`. Added `test_package/test.sh` as the CI-recognized test entrypoint; it runs `zig version`, compiles `smoke.zig`, and executes the generated program.
- Third OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-012309-39923` passed L0, then failed before build because the isolated `CONAN_HOME` lacked project `settings.yml`, so Conan did not recognize `settings.os=OHOS`. The job `conan-home` was seeded from remote `$HOME/.conan2`.
- Fourth OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-012404-40345` reached `conan create` and began downloading the official `zig-aarch64-linux-0.16.0.tar.xz`; official source was slow, so the recipe was updated with Zig official community mirror fallback URLs for the same archive and sha256.
- Fifth OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-014622-46857` used mirror-first order with `pkg.hexops.org`, but stalled after `Calling build()` without download progress. The run was stopped and the URL order changed to prefer `zig.linus.dev`, with official `ziglang.org` as fallback.
- Sixth OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-020131-51516` downloaded successfully from `zig.linus.dev`, packaged Zig, then failed in test_package with `/system/bin/sh: .../bin/zig: Permission denied`. Manual signing of packaged `bin/zig` with `binary-sign-tool sign -selfSign 1` made `zig version` return `0.16.0`; recipe updated to sign `bin/zig` during `package()` on OHOS.
- Seventh OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-020509-53195` verified signed packaged `zig version` works, then failed running the Zig-built `./smoke` executable with `Permission denied`. Updated `test_package/test.sh` to self-sign the generated smoke executable before running it.
- Eighth OHOS runner attempt `codex-0.16.0-zig-0.16.0-manual-conan-20260728-020942-55289` passed with exit code 0.
  - `zig-aarch64-linux-0.16.0.tar.xz` downloaded from `https://zig.linus.dev/zig/0.16.0/`.
  - `package()` self-signed packaged `bin/zig`, and `zig version` returned `0.16.0` in `test_package`.
  - `test_package/test.sh` compiled `smoke.zig`, self-signed the generated `./smoke` executable, and ran it successfully.
  - CI gates reported: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`, `L4_RESULT=pass`, `L5_RESULT=pass`.
- Upstream full test attempt on Windows host, 2026-07-28 to 2026-07-29:
  - Command: `zig build test --summary all -j1 --maxrss 20000000000` from the official `zig-0.16.0` source tree, using official `zig-x86_64-windows-0.16.0.zip`.
  - Result: failed with exit code 1 after running the upstream full test entrypoint.
  - Summary: `6686/7691 steps succeeded (965 skipped, 31 failed); 108372/111213 tests passed (2764 skipped, 65 failed, 12 crashed)`.
  - Main failures observed on the Windows host: `test-c-abi-x86-windows-gnu-pentium4-*` C ABI failures/crashes, `test-std` Windows `readlink`/non-symlink failures, `math.isnan`/`math.wrap` failures on selected Windows targets, and several MSVC target tests failing with `LibCStdLibHeaderNotFound`.
- Upstream full test attempt on OHOS true device, 2026-07-29:
  - Command: `zig build test --summary all -j1 --maxrss 20000000000` from the official `zig-0.16.0` source tree, using the signed packaged `zig/0.16.0` binary.
  - Result: failed before entering the test matrix because Zig's generated build runner was unsigned and HarmonyOS rejected execution.
  - Error: `failed to spawn build runner .zig-cache/o/.../build: AccessDenied`.
  - This confirmed the need for a reusable OHOS wrapper rather than only signing the packaged `zig` binary.

## Path B Candidate Work

- Added an OHOS `bin/zig` wrapper and `bin/zig-ohos-sign-generated` helper to
  handle the common Zig-generated executable signing problem for downstream
  `zig build` / `zig build run` / `zig build test` workflows.
- Added package-time OHOS Zig stdlib patching so `copy_file_range` /
  `sendfile` `OVERFLOW` falls back to normal read/write copying instead of
  panicking during `zig build install`.
- Added package-time OHOS Zig `std.Build` patching so default Zig unit tests run
  in terminal mode rather than `--listen=-` server mode. This avoids the
  minizign-observed `test runner failed to respond for 59.999s` failure while
  preserving ordinary test exit-code failures.
- Extended the OHOS wrapper retry matcher to include `failed to spawn and
  capture stdio`, which is the Zig build-system error surfaced when a generated
  test runner executable is still unsigned.
- Added a narrow wrapper fallback for remaining `--listen=-` test-runner
  timeouts: the wrapper signs generated executables and reruns each reported
  `failed command` without `--listen=-`; the fallback succeeds only if all
  rerun test binaries exit successfully.
- Upgraded `test_package` from `zig build-exe` to `zig build run install`,
  covering generated build runner execution, generated test executable
  execution, and install output.
- Evidence report: `reports/path-b-candidate.md`.
- Intermediate OHOS wrapper runner
  `codex-zig-zig-0.16.0-b-wrapper-conan-20260729-132058-47103` proved the
  first generated build runner signing retry worked, then exposed the
  `copy_file_range` `OVERFLOW` install-step panic.
- Final OHOS runner
  `/storage/Users/currentUser/ohos-test-runs/codex-zig-zig-0.16.0-b-wrapper-conan-final2-20260729-134856-64268`
  passed with exit code 0.
  - The log first showed generated build runner `AccessDenied`, then generated
    `smoke` executable `AccessDenied`, and finally `Build Summary: 5/5 steps
    succeeded` after wrapper retries.
  - Final gates: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`,
    `L4_RESULT=pass`, `L5_RESULT=pass`.
- Follow-up minizign evidence, 2026-08-08:
  - Original OHOS run
    `/storage/Users/currentUser/ohos-test-runs/codex-minizign-conan-0.1.13-r7-20260808-180625-60998`
    showed `zig build test -Doptimize=ReleaseSmall` first failing with
    generated test runner `AccessDenied`, then, after
    `zig-ohos-sign-generated`, failing with `test runner failed to respond for
    59.999s` / `1m...` on commands containing `--listen=-`.
  - The same signed generated test binaries run successfully in terminal mode:
    probe runner
    `/storage/Users/currentUser/ohos-test-runs/codex-zig-minizign-test-runner-probe2-20260808-191427-11248`
    executed the minizign test binary directly and reported `All 15 tests
    passed`.
  - Temporary wrapper fallback validation
    `/storage/Users/currentUser/ohos-test-runs/codex-zig-minizign-zig-build-test-wrapper-fallback-20260808-192411-12980`
    reran the two reported `failed command` entries without `--listen=-` and
    passed both generated test binaries.
  - Temporary `std.Build` terminal-mode validation
    `/storage/Users/currentUser/ohos-test-runs/codex-zig-minizign-zig-build-test-buildzig-terminal-20260808-192918-14553`
    ran the standard downstream command
    `zig build test -Doptimize=ReleaseSmall`; the log had zero `--listen=-`
    occurrences, retried unsigned generated test binaries after signing, and
    reported `All 0 tests passed` plus `All 15 tests passed`.
  - Conclusion: generated test runner signing is necessary, but the remaining
    minizign failure is Zig 0.16.0's stdio server test protocol
    (`--listen=-`) stalling on OHOS. Terminal exit-code mode runs the same
    signed test binaries successfully.
- `zig/0.16.0.1` OHOS single-package runner, 2026-08-08:
  - RUN_DIR:
    `/storage/Users/currentUser/ohos-test-runs/codex-zig-conan-0.16.0.1-ohos-test-runner-fix-20260808-2019-20260808-202051-26038`
  - Exit code: 0.
  - `zig/0.16.0.1` exported and created package
    `876049f3ae10a4560da345bb02378e03e212bc8c`, package revision
    `934a0752feb4dc670ef5879bf315fd02`.
  - The test package ran packaged `bin/zig version` and got `0.16.0`.
  - The first `zig build run install` attempt showed generated build runner
    `AccessDenied` and generated smoke executable
    `failed to spawn and capture stdio ... AccessDenied`; the wrapper signed
    generated ELF files and retried.
  - Retry result: `Build Summary: 5/5 steps succeeded`, `run success`, and
    `install success`.
  - Final gates: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`,
    `L4_RESULT=pass`, `L5_RESULT=pass`.
  - Remote temp transfer files and test_package generated output were cleaned,
    and the device lock was released.
- Final `zig/0.16.0.1` OHOS custom-cache runner, 2026-08-08:
  - RUN_DIR:
    `/storage/Users/currentUser/ohos-test-runs/codex-zig-conan-0.16.0.1-custom-cache-signing-20260808-2029-20260808-203142-33172`
  - Exit code: 0.
  - `zig/0.16.0.1` exported as recipe revision
    `b20191da29f426bb08a79b6aa7f24968`; package revision
    `6995be7da677b75fb0e943c691816b84`.
  - The test package set `ZIG_GLOBAL_CACHE_DIR=zig-global-cache` and
    `ZIG_LOCAL_CACHE_DIR=zig-local-cache`.
  - Initial execution failed on `zig-local-cache/o/.../build: AccessDenied` and
    `./zig-local-cache/o/.../smoke: AccessDenied`, then wrapper exact-path
    signing retried successfully.
  - Retry result: `Build Summary: 5/5 steps succeeded`, `run success`, and
    `install success`.
  - Final gates: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`,
    `L4_RESULT=pass`, `L5_RESULT=pass`.
  - Remote temp transfer files and test_package generated output were cleaned,
    and the device lock was released.

## Next Real-Device / Shadow CI Commands

From the repository root in the zig worktree:

```sh
CI_PACKAGES="archives/z/zig/0.16.0.1" zsh ci/conan/build_and_test.sh
```

Shadow CI single-package runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/z/zig/0.16.0.1
```

Direct Conan smoke command for an isolated OHOS job:

```sh
cd archives/z/zig/0.16.0.1
conan create . --user=ohpcd --channel=stable \
  -s:h os=OHOS -s:h arch=armv8 -s:h compiler=clang -s:h compiler.version=15 -s:h compiler.libcxx=libc++ -s:h build_type=Release \
  -s:b os=OHOS -s:b arch=armv8 -s:b compiler=clang -s:b compiler.version=15 -s:b compiler.libcxx=libc++ -s:b build_type=Release \
  --build=missing
```

After Zig publishes to ohpcd, re-run downstream W0 checks:

```sh
conan download "zig/0.16.0.1" -r=ohpcd --only-recipe
conan list "zig/0.16.0.1:*" -r=ohpcd
```

Then minizign can re-run:

```sh
CI_PACKAGES="archives/m/minizign/0.1.13" zsh ci/conan/build_and_test.sh
```

## Blocking Points

- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1562
- `zig/0.16.0` is already published and should remain stable. Use
  `zig/0.16.0.1` for downstream recipes such as `minizign/0.1.13` that need
  generated test runner signing plus OHOS terminal-mode unit-test execution.
