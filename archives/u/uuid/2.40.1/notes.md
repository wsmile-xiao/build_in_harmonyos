# uuid 2.40.1 adaptation notes

## Scope

- Package: uuid/2.40.1
- Upstream source: util-linux 2.40.1
- Issue: #808

## Adaptation

- Added a Conan Autotools recipe.
- Builds only util-linux `libuuid` with `--disable-all-programs --enable-libuuid`.
- Disables Python bindings and install-time chown/setuid handling for CI portability.
- Defaults to static library packaging.
- Derives the Autotools build triplet from `settings_build.arch` and the host triplet from `settings.arch`.
- Uses the toolchain-provided awk, or falls back to an available `gawk`/`awk` executable.
- Applies the `configure` TMPDIR portability change through Conan patches.

## Tests

- Added a CMake-based `test_package` that checks installed headers and pkg-config metadata.
- The test builds and runs a C program that exercises `uuid_generate`, `uuid_unparse_lower`, `uuid_parse`, `uuid_compare`, `uuid_clear`, and `uuid_is_null` when target execution is available.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Linux x86_64 Release and Debug `conan create` completed through packaging.
- The packaged static library passed the C API smoke test in `test_uuid.c`.
- GitCode CI `conan-build-test` #9052 passed for PR #2618 on `archives/u/uuid/2.40.1`, including the OHOS/aarch64 build and Conan `test_package`.
