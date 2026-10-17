# p11-kit-server 0.26.2 HarmonyOS adaptation

## Status

- Issue: 2072.
- Branch: `feat/p11-kit-server-0.26.2-2072`.
- Worktree: `D:\harmonyos\worktrees\p11-kit-server`.
- Dependency: `p11-kit/0.26.2` from separately merged PR #5125.
- Result: Shadow CI passed on HarmonyOS 6.0 aarch64 with upstream tests 9/9 and test_package 2/2.

## Package boundary

`p11-kit-server` is a binary subpackage built from the upstream p11-kit source tree. The package retains only:

- `bin/p11-kit-server`: creates and manages the local PKCS#11 forwarding socket.
- `bin/p11-kit-remote`: serves a module or selected tokens over stdin/stdout.
- `licenses/COPYING`.

Both commands use the exact `p11-kit/0.26.2` runtime dependency. The core library adaptation remains outside this issue and PR.

## Build configuration

- Meson build with `libffi`, trust module, systemd, NLS, completions, documentation, and post-install tests disabled.
- Focused upstream server tests remain enabled.
- Non-executable upstream helper scripts are invoked explicitly through `sh`.
- `llvm-ar` and `llvm-ranlib` are derived from the configured compiler directory when absent from the profile.
- Packaged OHOS ELF commands are re-signed after installation and selection.
- The versioned SDK `llvm/lib` is located from `clang --print-resource-dir`, with compiler `realpath` as a fallback.

## Root-cause analysis

Earlier CI failures had four independent causes:

1. The branch had not incorporated the merged dependency recipe, so Conan could not resolve `p11-kit/0.26.2`.
2. The recipe replaced the runner's socket-capable `TMPDIR` with an HMDFS build path. Filesystem AF_UNIX bind returns `EPERM` on HMDFS, but succeeds under `/data/storage/el2/base/cache`.
3. `/data/service/hnp/bin/clang` is a relative link into a versioned SDK. The Conan Python runtime did not reliably resolve it with `os.path.realpath()`, causing the false `/data/service/hnp/lib/libxml2.so.16` failure.
4. Running all eight C cases in one process deterministically left the fourth case with stale dynamically loaded client-module state. Every unchanged named case passes when the upstream runner starts it in a separate process.

The fixes select `TMPDIR` by performing a real filesystem bind probe, locate the SDK through clang itself, and run each original C test name in an isolated process. No upstream assertion or expected value is weakened.

The optional `p11tool` installed on the device cannot load its ambient GnuTLS library. The shell test treats this optional probe as unavailable and continues the mandatory server start/address/PID/stop assertions.

## Upstream tests

The build executes these eight original `test-server.c` cases independently:

- `/server/initialize`
- `/server/initialize-no-address`
- `/server/initialize-address-from-config`
- `/server/open-session`
- `/server/open-session-write-protected`
- `/server/all/initialize`
- `/server/all/initialize-no-address`
- `/server/all/open-session`

It then executes `test-server.sh`, including the mandatory server lifecycle assertions. Result: 9 passed, 0 failed.

## Consumer tests

`test_package`:

- compiles with `-std=c11 -Wall -Wextra -Werror`;
- requires a successful filesystem AF_UNIX bind in the selected `TMPDIR`;
- verifies exactly the two owned commands are packaged;
- executes both commands and validates their usage contracts;
- verifies the server's no-token exit status.

Result: 2 test_package workflows passed. CI's destructive negative test also passed by confirming the test fails when `bin/` is removed.

## Shadow CI evidence

- Tested commit: `b3ffa5b6c04ec6ae03ac99f5d97e0bde190a8fb8`.
- Run directory: `/storage/Users/currentUser/ohpc-ci-shadow/runs/b3ffa5b6c04e-20260813T165738Z-server-dep-run-8412`.
- Result: setup 0, dependency restore 0, build/test 0.
- Gates: L0 pass, L1 pass, L4 pass, L5 pass.
- L2: non-blocking skip because the generic scanner's `--version/--help` invocation does not match these subcommands; test_package is the authoritative command-contract check.
- Build Summary: total 1, success 1, failed 0.
- Upstream: 9/9 passed.
- test_package: AF_UNIX bind and command contracts passed.
- Source archive SHA256: `09fd9f44da4813a3141e73d5e7cf7008e5660d0405f13d56c15e1da9dcecf828`.
- Shadow source archive SHA256: `960b532152df84970fe804e5dfee1910726b82ccbb6b72108bd38075bcd6b4ff`.
- Dependency cache SHA256: `d3a8ee38253e20274c9038a5fef787b1c606da6f24eaf912fa66fbc41f108ebf`.
- Build log SHA256: `3b0ef5a16cd82b3a441b4e8a41af1b0ef4768361813bd56cf4bd00fee0c52d5e`.

## Infrastructure notes

- CI pre-download truncates hyphenated URLs into pseudo-names such as `gh` and `p11`, and the worker lacks `curl`. Conan receives the complete URL and downloads successfully, so this is a non-fatal infrastructure defect outside the version-scoped PR.
- L0k warns that application packages normally have a software-level `commands.json`. This issue is restricted to `archives/p/p11-kit-server/0.26.2/`; L0 treats the missing file as non-blocking.

## Official CI command

```sh
CI_PACKAGES="archives/p/p11-kit-server/0.26.2" zsh ci/conan/build_and_test.sh
```

Expected evidence: Build Summary 1/1, L0/L1/L4/L5 pass, upstream 9/9, and test_package execution. The generic L2 warning is non-blocking and is covered by the package-specific command-contract test.
