# zig 0.15.2 HarmonyOS adaptation notes

## Context

- Target package: `zig/0.15.2`
- Branch: `feat/zig-0.15.2-2235`
- Worktree: `D:\harmonyos\worktrees\zig-0.15.2`
- Issue: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2235
- Adaptation path: Path A (base adaptation) + Path B (knowledge contribution candidate).
- Reuse proof: `ncdu2/2.9.2` issue #2233 consumes Zig 0.15.2 and passed its
  complete 13-test upstream target plus the Conan consumer test on HarmonyOS.

## W0 Availability Check

Zig is packaged from the official upstream binary distribution and has no
Conan dependencies. The ohpcd remote publishes Zig 0.16.x recipes but did not
provide `zig/0.15.2`; this issue delivers 0.15.2 as an independently scoped
HarmonyOS toolchain package.

## Path B Candidate

The Path B contribution is the reusable HarmonyOS execution bridge for Zig
command scripts and generated ELF files. Signed ELF launchers invoke sibling
shell implementations on hmdfs, while the Zig wrapper signs generated build
and test executables and retries the original command. Detailed evidence is in
`reports/path-b-candidate.md`.

## Source And Build-System Analysis

- Official release index: `https://ziglang.org/download/index.json`
- Release date: `2025-10-11`
- Source archive SHA-256: `d9b30c7aa983fcff5eed2084d54ae83eaafe7ff3a84d8fb754d854165a6e521c`
- Bootstrap archive SHA-256: `a6845459501df3c3264ebc587b02a7094ad14f4f3f7287c48f04457e784d0d85`
- OHOS archive: `zig-aarch64-linux-0.15.2.tar.xz`
- OHOS archive SHA-256: `958ed7d1e00d0ea76590d27666efbf7a932281b3d7ba0c6b01b0ff26498f667f`
- All supported official platform hashes are recorded in `conandata.yml`.

Building Zig from source requires its LLVM/LLD/Clang bootstrap toolchain. This
recipe instead packages official release binaries as a Conan application/tool.
The official distribution layout is preserved so `zig` and `lib/` remain
siblings.

Zig 0.15.2 differs materially from the existing 0.16 recipe:

- It has no `lib/std/Io/Threaded.zig`, so the 0.16 OVERFLOW fallback patch is
  intentionally not carried over.
- `lib/std/Build.zig` defaults generated test runners to server mode when no
  explicit runner is configured. The OHOS package changes that single default
  from `else true` to `else false`, retaining explicit server-mode requests.
- The aarch64 backend already uses `unimplementedSendFile`, so no additional
  sendfile compatibility patch is needed at this stage.

## Packaging Strategy

- `package_type = "application"`.
- Package identity removes compiler, build type, and OS version, while retaining
  runtime OS and architecture.
- OHOS `armv8` maps to the official `aarch64-linux` archive.
- The OHOS command names are signed ELF launchers because hmdfs rejects direct
  execution of generated shell scripts. Each launcher invokes its sibling `.sh`.
- On OHOS the official executable becomes `zig-real`, is self-signed, and is
  fronted by the signing/retry launcher and wrapper.
- The wrapper signs generated executables in standard and explicitly reported
  cache paths, then retries AccessDenied failures.
- `zig-ohos-sign-generated` remains available to downstream recipes.

## Test Package

The test package makes five substantive checks:

1. Run the packaged compiler and assert exact version `0.15.2`.
2. Compile the checked-in `smoke.zig` through `build.zig`.
3. Run the generated smoke executable.
4. Install it to `zig-out/bin`.
5. Assert the installed executable exists and runs successfully.

Upstream full tests are not run because the recipe packages the official binary
distribution rather than building Zig from source.

## Local Verification

On 2026-08-17:

- Official Windows and aarch64-linux archives were downloaded and their hashes
  matched `conandata.yml`.
- `conan inspect .`: passed with Conan 2.29.1.
- `conan create .` for Windows x86_64: passed.
- Conan packaged 144 top-level entries from the official distribution.
- `zig version` returned `0.15.2`.
- `zig build run install --summary all -Doptimize=ReleaseSmall` reported
  `Build Summary: 5/5 steps succeeded`; compile, run, and install passed.
- The OHOS stdlib patch method ran against the official aarch64-linux
  `Build.zig`; the old target count became 0 and the patched target count was 1.

## Real-Device Verification

On 2026-08-17, the allocated HarmonyOS aarch64 device window was used through
the global single-package runner lock.

- Shadow CI run:
  `/storage/Users/currentUser/ohos-test-runs/codex-zig-0.15.2-2235-shadow-ci-r2-20260817-091735-40486`
- Shadow CI verified commit `2e179b21575eaa0df70dd86e52b337198e37737a`
  and the selected CI/package input hashes.
- Setup passed, but L0 failed only at `commands_json_r38`; L1/L2/L4/L5 were
  skipped. The required software-level `archives/z/zig/commands.json` change is
  outside this issue's allowed version directory.
- Isolated device `conan create` run:
  `/storage/Users/currentUser/ohos-test-runs/codex-zig-0.15.2-2235-conan-create-r2-20260817-091835-41071`
- Conan 2.29.1 created package ID
  `876049f3ae10a4560da345bb02378e03e212bc8c`, package revision
  `dc58c1e12eb784152e7cee847e6fae59`, and completed `test_package` with exit 0.
- The packaged launcher returned `zig version` = `0.15.2`.
- The first generated build runner and smoke executable received the expected
  HarmonyOS `AccessDenied`; the wrapper signed the generated ELF files and
  retried successfully. The final `Build Summary` reported `5/5 steps succeeded`.

## Reproduction Commands

From the Zig worktree root, with an allocated single-package device window:

```sh
CI_PACKAGES="archives/z/zig/0.15.2" zsh ci/conan/build_and_test.sh
```

Shadow CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/z/zig/0.15.2
```
