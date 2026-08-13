# kbd-vlock 2.8.0

## Issue

No explicit issue number was found in the local project files or conversation
context. Marked as `TBD` for handoff.

## Source

- Upstream package: kbd 2.8.0
- URL: https://www.kernel.org/pub/linux/utils/kbd/kbd-2.8.0.tar.xz
- SHA256: `01f5806da7d1d34f594b7b2a6ae1ab23215344cf1064e8edcd3a90fef9776a11`

## W0 Dependency Check

- `linux-pam/1.7.2`: available in the OHOS Conan cache/registry.
- `flex/2.6.4`: available in the OHOS Conan cache/registry.
- `bison/3.8.2`: available in the OHOS Conan cache/registry.

## Build Analysis

- Build system: Autotools release tarball with generated `configure`.
- Target component: `src/vlock` plus private `src/libcommon/libcommon.a`.
- Configure keeps `--enable-vlock` and disables libkeymap, libkfont,
  compression, tests, and NLS.
- Build intentionally runs only `make -C src/libcommon` and
  `make -C src/vlock`; full upstream `make check` covers unrelated kbd tools
  and libraries outside this component package.
- The kbd 2.8.0 tarball has no dedicated upstream vlock test case; upstream
  test pass rate for this component is recorded as `0/0 (N/A)`.

## OHOS Adaptation

- `0001-libcommon-portable-program-name.patch`: removes runtime reliance on
  glibc-only `program_invocation_short_name`.
- `0002-vlock-disable-vt-ioctls-on-ohos.patch`: builds vlock without Linux
  virtual-console ioctls when `KBD_VLOCK_DISABLE_VT_IOCTL` is defined.
  Current-tty mode remains available; `-a/--all` is rejected on OHOS pending
  platform VT capability confirmation.
- The recipe creates minimal OHOS tool wrappers for `pkg-config` and the
  Autoconf `flex` probe because the runner cache lacks a usable `pkg-config`
  package and the `flex/2.6.4` binary package does not expose `bin/flex`.
- The recipe redirects Autoconf `config.status` temporary directories to a
  writable build temp dir and uses `umask 022` to avoid HMDFS
  `./confXXXXXX/subs1.awk: Permission denied` failures.

## Validation

- Local:
  - `python -m json.tool archives/k/kbd-vlock/commands.json`: passed.
  - `python -m py_compile conanfile.py test_package/conanfile.py test_package/test_smoke.py`: passed.
  - `conan inspect archives/k/kbd-vlock/2.8.0`: passed.
- OHOS runner:
  - Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-kbd-2.8.0-kbd-vlock-2.8.0-20260812-r1-conan-20260812-190531-49229`
  - Command: `zsh ci/conan/build_and_test.sh archives/k/kbd-vlock/2.8.0`
  - Result: success, exit code 0.
  - L0/L1/L4/L5: pass.
  - L2: runner-level version/help probe reported non-blocking skip; the
    package `test_package` executed `vlock --version` and `vlock --help`
    through Conan's run environment, including the PAM runtime library path.
  - Added smoke assertions: 3/3 passed.
  - Build summary: Total 1, Success 1, Failed 0.

## Next Commands

```sh
CI_PACKAGES="archives/k/kbd-vlock/2.8.0" zsh ci/conan/build_and_test.sh
```

Shadow CI equivalent:

```sh
/path/to/run-ohos-shadow-ci.sh archives/k/kbd-vlock/2.8.0
```
