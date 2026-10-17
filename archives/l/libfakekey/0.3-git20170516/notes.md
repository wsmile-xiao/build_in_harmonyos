# libfakekey 0.3-git20170516 adaptation notes

## Source provenance

- Official repository: `https://git.yoctoproject.org/libfakekey`
- Tag: `0.3`
- Commit: `7ad885912efb2131e80914e964d5e635b0d07b40`
- Commit author date: `2017-05-16T11:57:27+03:00`
- The reference archive was compared byte-for-byte by file content with this tag.
- `conandata.yml` records the SHA-256 of `git archive --format=tar --prefix=libfakekey/ 0.3 | xz -c`.

## Dependency preflight (W0)

Both direct dependencies were found in the `ohpcd` Conan remote before adaptation:

- `libx11/6.4.0`
- `libxtst/6.1.0`

An OHOS armv8 `conan install --build=never` resolved the complete X11 dependency chain successfully.

## Build adaptation

The upstream project is a single C source file with an Autotools frontend. The recipe compiles the source directly with Conan's configured Clang and packages the public header, library, and pkg-config file. This avoids depending on generated Autotools files while preserving every exported function.

The recipe force-includes the standard `<string.h>` header because the source calls `memset` and `strlen`; modern Clang rejects undeclared C library functions. The official source remains unchanged. No HarmonyOS stub, feature removal, or platform macro injection is used.

On the device's HMDFS workspace, Git treats the freshly cloned checkout as having a different owner. Commit verification therefore passes `-c safe.directory=<checkout>` to that single `git rev-parse` invocation; it does not change the user's global Git configuration.

## Upstream test inventory and execution (R51)

| Item | Result |
|---|---|
| `tests/` source files | 1 (`tests/fakekey-test.c`) |
| Automake `TESTS` entries | 0 |
| Registered `make check` tests | 0 |
| Actual upstream integration programs | 1 (`fakekey-test`) |
| Upstream integration execution | 1/1 passed under host Xvfb |

The upstream program opens an X display and sends `hello HELLO worldly world` through XTEST. It was executed unchanged with `xvfb-run -a ./tests/fakekey-test`, exit code 0. The recipe also compiles this exact source against the produced library.

The HarmonyOS PC device currently exposes neither an X11 display nor Xvfb/Xwayland, so it cannot honestly execute graphical injection. This is an environment capability boundary, not a skipped compile failure. Device-side tests instead validate the public API's documented NULL-display behavior and a HarmonyOS-specific runtime identity check.

## Test totals

- Upstream actual: 1 integration case, 1/1 passed.
- Added consumer tests: 2 cases, including 1 HarmonyOS-specific case.
- Adapted total: 3 cases, which is greater than the upstream actual count.

## Verification results

- Host upstream baseline: `autoreconf -fi`, `configure`, `make`, `make check`, and `xvfb-run -a ./tests/fakekey-test` all succeeded; upstream result 1/1.
- Host OHOS SDK cross-build: both shared and static Conan package builds succeeded with the published OHOS arm64 dependency binaries.
- HarmonyOS PC native build: full `conan create` with the competition `ohos-aarch64` profile succeeded.
- HarmonyOS PC consumer tests: 2/2 passed, including the HarmonyOS-specific `uname` assertion.

## Known runtime requirement

Applications must supply a working X11 display with the XTEST extension for real keyboard event injection.
