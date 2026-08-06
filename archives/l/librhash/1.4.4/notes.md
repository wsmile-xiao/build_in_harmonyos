# librhash 1.4.4 adaptation notes

## Scope

- Issue: 1890
- Worktree: `D:\harmonyos\worktrees\librhash`
- Branch: `feat/librhash-1.4.4-1890`
- Package path: `archives/l/librhash/1.4.4`

## W0 dependency check

- Required dependencies: none.
- Optional dependencies: OpenSSL and gettext are intentionally disabled.
- Rationale: existing `archives/r/rhash/1.4.4` notes record gettext build issues and shared-library symlink issues on OHOS; librhash can provide the core API without these optional features.

## Source and build analysis

- Source URL: `https://github.com/rhash/RHash/archive/refs/tags/v1.4.4.tar.gz`
- SHA256: `8e7d1a8ccac0143c8fe9b68ebac67d485df119ea17a613f4038cda52f84ef52a`
- Build system: custom `configure` plus Makefile.
- Library target: `make -j1 lib-static`, producing `librhash/librhash.a`.
- Upstream library test target: `make -j1 test-lib-static`, producing and running `librhash/test_static`.

## Conan strategy

- Build static `librhash.a` only.
- Package headers: `rhash.h` and `rhash_torrent.h`.
- Disable shared library generation to avoid symlink handling on HMDFS.
- Disable OpenSSL/gettext to keep W0 dependency-free.
- Use compiler paths from Conan `tools.build:compiler_executables` and pass them to `configure` with `--cc`/`--ar`.
- If `make` is unavailable on the OHOS worker, fall back to compiling the `librhash/Makefile` source list directly with clang and the SDK `llvm-ar`; still builds and runs upstream `librhash/test_lib.c` as `test_static`.
- Set `TMPDIR` inside the Conan build folder for configure-time probes.
- `test_package` avoids CMake because the target worker did not expose `cmake`; it compiles `test.c` directly with the Conan profile C compiler and links against `librhash.a`.

## Validation status

- Local source download and SHA256 check: passed on Windows host.
- Static recipe/test files: prepared.
- Read-only Python AST syntax check for both `conanfile.py` files: passed.
- Whitespace scan for the target directory: passed.
- Host tool availability: `conan`, `make`, `clang`, `cmake`, and `zsh` are not on the Windows PATH in this session, so a local `conan create` or CI dry run was not feasible here.
- Full OHOS single-package shadow CI: passed on 2026-08-06.
  - Runner log location retained locally; external IPs and device paths are intentionally omitted from the public archive.
  - Summary: `Total: 1`, `Success: 1`, `Failed: 0`
  - Gates: `L0=pass`, `L1=pass`, `L2=skip` (no `bin/`), `L4=pass`, `L5=pass`
  - Upstream library test evidence: `./test_static` printed `All sums are working properly!`
  - Consumer test evidence: `test_package` compiled and ran `test_librhash`; L1e destructive negative test confirmed the test depends on `librhash`.

## Next commands

```sh
cd D:/harmonyos/worktrees/librhash
CI_PACKAGES="archives/l/librhash/1.4.4" zsh ci/conan/build_and_test.sh
```

If using the shadow CI runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/librhash/1.4.4
```
