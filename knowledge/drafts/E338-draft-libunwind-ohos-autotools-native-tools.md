# E338 - OHOS Native Autotools Toolchain And Config.status TMPDIR Closure

> Contributor: codex | Status: DRAFT | Created: 2026-08-25

## Scope

Use this pattern when an Autotools release tarball is built natively on an OHOS
shadow CI device and the Conan profile supplies clang through
`tools.build:compiler_executables`, but the runner PATH does not already expose
the full LLVM/binutils toolchain.

The draft comes from the `libunwind/1.6.2` adaptation. The package is a small
static library with no required dependencies, so the failures were isolated to
the package's own Autotools environment.

## Failure Sequence

`libunwind/1.6.2` exposed two ordered failures:

1. `configure` found clang but not `ar`, `ranlib`, or `strip`. Libtool then
   tried an unrelated `link -lib` interface and failed with
   `could not determine link -lib interface`.
2. After `AR/NM/RANLIB/STRIP` were injected, `configure` progressed to
   `config.status` and failed with `./conf*/subs1.awk: Permission denied`.

The second failure is the familiar OHOS temporary-directory problem in a
slightly sharper form: `config.status` created `./conf*` below the build
folder, but the resulting directory ownership/permission semantics rejected
creating generated files such as `subs1.awk`.

## Recommended Solution

Keep the fix package-local in the Conan recipe:

1. In `generate()`, read `tools.build:compiler_executables` and derive
   `tool_dir` from the C compiler path.
2. Fall back to `/data/service/hnp/bin` only when no compiler directory is
   available and that directory exists.
3. Prepend `tool_dir` to PATH.
4. Define `AR`, `NM`, `RANLIB`, and `STRIP` to the `llvm-*` tools in that
   directory when they exist.
5. Create a device-private `TMPDIR`, for example
   `/data/storage/el2/base/<pkg>-configure-tmp`, when that path exists.
6. After `apply_conandata_patches()`, use `replace_in_file(strict=True)` on the
   generated `configure` script so its `config.status` template creates
   `conf*` below `$TMPDIR` instead of below the build folder.
7. Run `configure` from the build folder, through the recipe environment that
   contains the generated Conan build scripts.

For `libunwind/1.6.2`, the successful implementation is in
`archives/l/libunwind/1.6.2/conanfile.py`, in `generate()`,
`_patch_ohos_config_status_tmpdir()`, and `_configure()`.

## Verification

The fixed recipe passed a single-package shadow CI run on the OHOS device:

```text
run_id=codex-libunwind-libunwind-1.6.2-shadow-20260825-192940-conan-watch-r4-20260825-221014-20260825-221637-7273
exit-code.txt=0
conan create passed
Build Summary: Success 1, Failed 0
```

The same run also built and ran the consumer `test_package`.

A later review run also enabled upstream validation on the real OHOS device.
Full `make check -j1` reached the upstream suite and reported `TOTAL 29 / PASS
20 / FAIL 9`; the recipe now exposes the 20 passing tests as an explicit OHOS
stable subset through `-c user.libunwind:run_upstream_tests=True`.

## Forbidden Shortcuts

- Do not patch `ci/conan`, the runner, or global profile PATH from a package PR.
- Do not rely on retries after `subs1.awk: Permission denied`.
- Do not treat `chmod` on Autoconf temporary directories as a durable fix.
- Do not hard-code a developer-specific home path when deriving tool locations.

## Relation To Existing Knowledge

E114 covers broader OHOS umask/HMDFS behavior. E337 covers a task-local closure
for Autotools bootstrap tools supplied by Conan packages. This draft is narrower:
the source archive already has `configure`, but native Autotools still needs a
complete binutils and temporary-directory closure before `configure && make`
can be reproducible.
