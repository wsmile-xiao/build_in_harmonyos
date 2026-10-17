# jsmn 1.1.0 HarmonyOS adaptation notes

## Scope

- Package path: `archives/j/jsmn/1.1.0`
- Branch: `feat/jsmn-1.1.0`
- Issue: `#1517`

## W0 dependency check

jsmn is a single-header C JSON tokenizer. It has no required or optional Conan dependencies, so there are no dependency packages to pre-publish before this adaptation.

## Source and build-system analysis

- Source URL: `https://codeload.github.com/zserge/jsmn/tar.gz/refs/tags/v1.1.0`
- SHA256: `5f0913a10657fe7ec8d5794ccf00a01000e3e1f2f1e1f143c34a0f7b47edcb38`
- Upstream files: `jsmn.h`, `Makefile`, `test/tests.c`, examples and license.
- Build system: simple Makefile. There is no configure, CMake or Meson project.
- Packaging strategy: header-library; install `jsmn.h` into `include/` and `LICENSE` into `licenses/`.

## Tests

The recipe runs upstream `make test` on Linux/OHOS using the C compiler from `tools.build:compiler_executables.c`. The upstream Makefile builds and runs four variants:

- `test_default`
- `test_strict`
- `test_links`
- `test_strict_links`

The `test_package` is a consumer C test that includes `<jsmn.h>`, parses an object containing a string, array and primitive boolean, verifies token type/size/text, and checks the `JSMN_ERROR_NOMEM` error path.

## Next device or shadow CI command

Run only this package when a device/shadow CI slot is available:

```sh
CI_PACKAGES="archives/j/jsmn/1.1.0" zsh ci/conan/build_and_test.sh
```

Shadow CI runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/j/jsmn/1.1.0
```

## HarmonyOS real-device verification

Run date: 2026-07-27

Command:

```sh
CI_PACKAGES="archives/j/jsmn/1.1.0" zsh ci/conan/build_and_test.sh
```

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-jsmn-jsmn-1.1.0-conan-r4-20260727-190347-39484
```

Result:

- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`.
- L0: pass.
- L1: pass. Upstream `make test` ran four variants, each reporting `PASSED: 16`, `FAILED: 0`; `test_package` printed `test jsmn 1.1.0: PASS`.
- L2: skip, because jsmn is a header-only library with no `bin/` directory.
- L4: pass, no patches.
- L5: warn, because this header-only package intentionally has no `bin/` or `lib/` artifacts; package content includes `include/jsmn.h` and `licenses/LICENSE`.

Device runner note: the interactive device profile needed a job-local compiler wrapper because the repository default profile points to `/data/service/hnp/bin/clang`, which is not present on this shared interactive device. This did not change the submitted recipe.

## Upstream-only real-device rerun

Run date: 2026-07-27

Command:

```sh
make -B test CC=/storage/Users/currentUser/ohos-users/codex/jsmn-1.1.0/tools/clang
```

RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-jsmn-jsmn-1.1.0-upstream-r1-20260727-191044-43142
```

Result: pass. The upstream Makefile rebuilt and executed all four variants:

- `test_default`: `PASSED: 16`, `FAILED: 0`.
- `test_strict`: `PASSED: 16`, `FAILED: 0`.
- `test_links`: `PASSED: 16`, `FAILED: 0`.
- `test_strict_links`: `PASSED: 16`, `FAILED: 0`.
