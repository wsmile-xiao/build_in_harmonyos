# serd 0.32.9 HarmonyOS adaptation notes

## Package scope

Serd is a lightweight C library for reading and writing RDF data, with the `serdi` command-line utility.

Upstream does not publish a release archive for the odd development version 0.32.9. This recipe pins official GitLab commit `0317806d56f9288294183b41074a6fd50a924f5a`; its `meson.build` declares version `0.32.9`. The downloaded archive is 380829 bytes with SHA-256 `4cec57d40ff913a4530043ffc6e37f80b758f08fb807ac8d73b832d31f336a78`.

## W0 dependency check

- Required Conan dependencies: none.
- Optional system dependency: `libm`, detected by Meson and exposed as `m` for Linux/OHOS consumers.
- The source tree contains no zix reference. The dependency declared by the historical `0.32.9-git` draft is not applicable to this pinned snapshot.

## Build configuration

- Meson build system.
- Static library by default to avoid target-side shared library signing/runtime loader surprises.
- `tools=enabled` keeps `serdi` available.
- `tests=enabled` and `build()` runs `meson.test()` for upstream verification.
- On OHOS, the Meson test commands invoke the four upstream Python scripts through the discovered Python interpreter because archive-mounted `0750` modes are not executable by the runner UID.
- Documentation, man HTML, and lint are disabled because they require documentation/lint tooling that is not part of the library runtime.
- Packaged `bin/serdi` is re-signed with `binary-sign-tool -selfSign 1` so it can run from the Conan cache during `test_package`.

## Test inventory

- Header warning test: 1.
- C unit tests: 8.
- `serdi` command, input, and I/O tests: 33.
- Data-driven RDF suites: 23.
- Total upstream Meson registrations: 65.
- `test_package`: 2 consumer checks (C API and packaged `serdi` conversion).

## Local preflight validation

- Official GitLab source archive downloaded and SHA-256 verified.
- Meson project version and options inspected from the unpacked source.
- Recipe and test sources are prepared from the HarmonyOS-validated 0.32.10 baseline.
- Temporary Conan 2.29.1 `inspect`, `export`, and `source` checks passed with isolated cache/source directories.
- The required Conan/Meson/Ninja/CMake/Clang toolchain is not available in the Windows host PATH, so `conan create` was run only in shadow CI.

## HarmonyOS device preflight

- Prepared an isolated repo and Conan home for this package.
- Copied the validated Conan `settings.yml` containing `os=OHOS` into the isolated home.
- Runner-executed `conan graph info` passed with no dependencies and the expected `OHOS 6.0`, `armv8`, Clang 15, static-library configuration.
- Conan 2.29.1, Meson 1.11.1, Ninja, OHOS Clang/LLVM tools, Bash, signing tools, and CMake 4.1.2 are available.
- CMake is under `/data/service/hnp/bin`, which must be prepended to the runner PATH.

## HarmonyOS shadow CI validation

- Successful runner: `codex-serd-serd-serd-0.32.9-483c5112-conan-r6-20260821-212504-56435`.
- Runner acquired the device-global lock with `--try-lock` and ended with `rc=0`.
- Upstream Meson suite: 65/65 passed (41 normal successes and 24 expected-failure successes).
- Conan `test_package`: 2/2 passed (`serd_c_api` and signed packaged `serdi` Turtle-to-NTriples conversion).
- CI gates: L0, L1, L2, L4, and L5 passed; the destructive negative test confirmed that the consumer test depends on the package.
- Build summary: total 1, success 1, failed 0.
- Package artifacts include `lib/libserd-0.a`, `include/serd-0/serd/serd.h`, and `bin/serdi`.

## Resolved device behavior

The initial device runs stopped when Meson tried to execute `run_suite.py`, `test_quiet.py`, `test_stdin.py`, and `test_write_error.py` directly. The archive/build copies retained mode `0750`; on this device mount, `chmod 755` returned success but the mode remained unchanged, so a chmod-only recipe fix was ineffective.

The final OHOS-only recipe adjustment rewrites the build copy of `test/meson.build` before configuration so Meson launches those scripts through `import('python').find_installation()`. No test body, argument, fixture, expected-failure marker, or registration is removed or replaced.

## Reproduction command

```sh
. "$HOME/ohos-users/codex-serd/serd-0.32.9-483c5112/env.sh"
cd "$CI_REPO_ROOT"
sh "$HOME/bin/ohos-test-runner.sh" \
  --user "$OHOS_ISOLATED_USER" \
  --lib serd \
  --task "$OHOS_ISOLATED_JOB-conan-r6" \
  --mode heavy \
  --try-lock \
  --path "$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:/data/service/hnp/bin" \
  --workdir "$CI_REPO_ROOT" \
  -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

Exit 75 means the device is busy and is not a serd failure.
