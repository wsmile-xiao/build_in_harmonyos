# Local preflight

Date: 2026-08-12

## Dependency checks

All dependency recipe checks used `conan download <ref> -r=ohpcd --only-recipe`.

- `linux-pam/1.7.2`: passed
- `flex/2.6.4`: passed
- `bison/3.8.2`: passed

## Source check

- URL: https://www.kernel.org/pub/linux/utils/kbd/kbd-2.8.0.tar.xz
- SHA256: `01f5806da7d1d34f594b7b2a6ae1ab23215344cf1064e8edcd3a90fef9776a11`
- Build system: Autotools release tarball
- Target: `src/libcommon` and `src/vlock`

## Recipe and patch checks

- `python -m json.tool archives/k/kbd-vlock/commands.json`: passed
- `python -m py_compile conanfile.py test_package/conanfile.py test_package/test_smoke.py`: passed
- `conan inspect archives/k/kbd-vlock/2.8.0`: passed
- `git apply --check patches/0001-libcommon-portable-program-name.patch`: passed against the official extracted source
- Ordered patch application (`0001` then `0002`) on a clean source copy: passed

## OHOS runner verification

- Job root: `/storage/Users/currentUser/ohos-users/codex-kbd/kbd-vlock-2.8.0-20260812-r1`
- Final run: `/storage/Users/currentUser/ohos-test-runs/codex-kbd-2.8.0-kbd-vlock-2.8.0-20260812-r1-conan-20260812-190531-49229`
- Command: `zsh ci/conan/build_and_test.sh archives/k/kbd-vlock/2.8.0`
- Result: passed, exit code 0.
- L0/L1/L4/L5: pass.
- L2: runner-level version/help probe reported a non-blocking skip. The Conan
  `test_package` did execute `vlock --version` and `vlock --help` through the
  generated `conanrun` environment so PAM runtime libraries were available.
- Upstream vlock-specific tests: 0/0, not applicable; no dedicated vlock test
  cases were found in the kbd 2.8.0 upstream tests.
- Added smoke assertions: 3/3 passed.
- Build summary: Total 1, Success 1, Failed 0.

## Notes

- The local Windows/WSL environment was used for static preflight only.
- The OHOS runner build confirmed configure, component build, package install,
  ELF signing, and test_package smoke execution.
