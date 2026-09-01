# luvit 2.18.1.1 OpenHarmony PC notes

## Scope

This package adapts the official Luvit 2.18.1 source archive for OpenHarmony PC by packaging the Lua module tree (`init.lua`, `main.lua`, and `deps/`) and project metadata. Luvit runs on top of the external `luvi` runtime.

## Dependency boundary

The upstream `Makefile` creates self-contained `luvit`, `lit`, and `luvi` binaries by downloading `lit` and a `luvi` runtime. The OHPCD Conan remote currently has no `luvi` or `lit` package, so this recipe does not pretend to build those binaries. It packages the official Luvit Lua resources and documents the runtime requirement explicitly.

The upstream `package.lua` declares `luvi.version = "2.12.0"`.

## Build

No native compilation or source patch is required for the Lua resource package. The package phase installs:

- `share/luvit/init.lua`
- `share/luvit/main.lua`
- `share/luvit/deps/**`
- `share/luvit/tests/**`
- `share/luvit/.luvit-assets.json` (generated file inventory used by test_package)
- license and documentation files

## Tests

Upstream tests run with `luvi . -- tests/run.lua` and require a working luvi runtime. The package installs the upstream `tests/` tree, and `test_package` invokes `luvi <package>/share/luvit -- tests/run.lua` when a compatible luvi is available in `PATH`. The runner scans and executes 84 upstream `tests/test-*.lua` files.

Before the OpenDesk run, the suite was executed on the control host with the official luvi 2.12.0 Linux x86_64 binary: 250 TAP assertions ran, 249 passed, and `http-stream-finish - http stream end #1` failed reproducibly (a timing-sensitive upstream test; running the file standalone hangs). luvi 2.15.0 was also tried, but it aborts `tests/test-tls-remote.lua` because of an API/error-handling change, so it is not a compatible replacement.

OpenDesk runs on an aarch64 HarmonyOS device. luvi 2.12.0 (the version pinned by upstream `package.lua`) has no published aarch64 Linux asset. The 2026-08-14 queue job confirmed `luvi` is not in PATH; it downloaded the luvi 2.15.0 aarch64 binary successfully, but the device reports `Permission denied` when trying to execute it, so no compatible runtime could be staged. `test_package` therefore verified the complete resource inventory (every packaged file, required entry points, and all 84 upstream test files) and reported the missing external runtime explicitly instead of claiming upstream execution.

## Verification status

OpenDesk queue job `20260814-070628-bfc89f-20260814-misc2-3053-3057-3058-r1` on head `87d8e446d` passed `ci/conan/build_and_test.sh` with Build Summary Total 1 / Success 1 / Failed 0. `check_luvit_resources.py` verified 257 packaged files including all 84 upstream `tests/test-*.lua` files. `tests/run.lua` was not executed on the device because no compatible luvi runtime could be staged; the control-host luvi 2.12.0 x86_64 result remains 249/250 TAP assertions.

## Verification command

```bash
CI_PACKAGES="archives/l/luvit/2.18.1.1" zsh ci/conan/build_and_test.sh
```
