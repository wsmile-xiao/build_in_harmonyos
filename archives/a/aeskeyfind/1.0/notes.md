# aeskeyfind 1.0 HarmonyOS Adaptation Notes

## Issue

- issue: #1844
- 前置适配阶段未在本地上下文找到明确 issue；后续由用户补充确认为 #1844。

## Version And Source

- Requested target version: `1`
- Conan/archive version used: `1.0` (Conan 2.29 rejects pure integer package version `1`)
- Upstream release string in README: `AESKeyFinder 1.0 (2008-07-18)`
- Source URL: `https://deb.debian.org/debian/pool/main/a/aeskeyfind/aeskeyfind_1.0.orig.tar.gz`
- SHA256: `1417e5c1b61e86bb9527db1f5bee1995a0eea82475db3cbc880e04bf706083e4`
- Homepage from Debian source metadata: `https://citp.princeton.edu/our-work/memory/code/`

## W0 Dependency Check

- Required Conan dependencies: none
- Optional dependencies: none
- Build/runtime dependencies are limited to libc/POSIX APIs (`open`, `fstat`, `mmap`, `getopt`) and a C compiler.

## Source And Build Analysis

- Build system: plain Makefile
- Upstream files: `aeskeyfind.c`, `aes.c`, `util.c`, headers, `Makefile`, `README`, `LICENSE`
- Upstream Makefile has no `install` target and no `check` target.
- Recipe builds with `make -j1`, injects `CC` from `tools.build:compiler_executables`, and overrides `CFLAGS` with C99, large-file, and build-type flags.
- Package installs the single CLI binary to `bin/aeskeyfind`, plus license and README.
- `package_type = "application"` and `cpp_info.bindirs = ["bin"]`; software-level `commands.json` declares the `aeskeyfind` command.

## Patch Notes

- `0001-fix-portable-c-build.patch`
  - fixes `sbox` declaration from 255 to 256 entries;
  - changes memory-image length handling from `unsigned int` to `size_t`;
  - guards oversize/negative `st_size` before `mmap`;
  - fixes the AES key-core byte rotation expression that used a negative modulo;
  - makes `set_byte()` use unsigned 32-bit shifts.

These are aeskeyfind source portability fixes and do not introduce or adapt a dependency package.

## Test Strategy

- Upstream has no bundled test target.
- `test_package/test_aeskeyfind.py` provides three consumer checks:
  - `aeskeyfind -h` prints usage text;
  - a too-small memory image returns the expected error path;
  - a generated memory image containing the standard AES-128 key schedule recovers `000102030405060708090a0b0c0d0e0f`.

## Local Validation

- Windows host has Conan 2.29.1 available.
- `python` syntax/AST check passed for `conanfile.py`, `test_package/conanfile.py`, and `test_package/test_aeskeyfind.py`.
- `commands.json` parsed successfully with `python -m json.tool`.
- Patch dry-run passed with `git apply --check` against the extracted upstream tarball.
- `conan inspect .` parsed the recipe and reports `package_type: application`, no requirements, and version `1.0`.
- `conan export . --user=ohpcd --channel=stable` passed for `aeskeyfind/1.0@ohpcd/stable`.
- Source download/SHA256 was verified by `conan source`; the temporary extracted files were removed from the worktree.
- `conan download "aeskeyfind/1.0" -r=ohpcd --only-recipe` was blocked by the remote with `system acceleration policy not enabled`, so registry collision remains pending.
- Windows host currently lacks `zsh`, `make`, and `clang`, so single-package CI / `conan create` was not attempted locally.

## OHOS Validation

- Remote host: `currentUser@frp-tip.com:33332`
- Remote repo: `/storage/Users/currentUser/validation/build_in_harmonyos`
- Build log: `/storage/Users/currentUser/aeskeyfind-build-20260805-022641.log`
- Branch-name validation rerun log: `/storage/Users/currentUser/aeskeyfind-build-20260805-072444-branch.log`
- Command:

```sh
CI_PACKAGES="archives/a/aeskeyfind/1.0" zsh ci/conan/build_and_test.sh
```

- Result: pass
- Build summary: `Total: 1`, `Success: 1`, `Failed: 0`
- Gate summary:
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: test_package executed`
  - `L2_RESULT=skip: aeskeyfind version/help failed`
  - `L4_RESULT=pass: patches clean`
  - `L5_RESULT=pass: bin/ has content`
- L2 note: CI probes `--version/--help`; aeskeyfind supports short `-h`, which is already exercised in `build()` and the test package, so this is a non-blocking smoke warning.
- Rerun with `CI_BRANCH=feat/aeskeyfind-1` also passed with the same gate summary.

## Next OHOS / Shadow CI Commands

```sh
CI_PACKAGES="archives/a/aeskeyfind/1.0" zsh ci/conan/build_and_test.sh
```

```sh
/path/to/run-ohos-shadow-ci.sh archives/a/aeskeyfind/1.0
```
