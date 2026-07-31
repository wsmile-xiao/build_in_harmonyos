# nss-wrapper 1.1.16 OpenHarmony adaptation record

## Basic information

- Software: nss-wrapper
- Version: 1.1.16
- Build system: CMake
- Target: Linux or OHOS libc environments with nsswitch-compatible headers

## Build guidance

The package builds upstream `nss_wrapper` as a shared library and installs the
helper script `nss_wrapper.pl`. The Conan test package runs the library through
`LD_PRELOAD` and verifies passwd, group, uid/gid, and hostname substitution.
The official upstream CTest suite is not enabled by default because it requires
a consumable `cmocka` test framework package.

## Known limits

`nss-wrapper` intercepts libc name-service calls through `LD_PRELOAD`. OHOS
does not expose glibc `nss.h` or Solaris `nss_common.h`, so the package carries
a narrow patch that defines the glibc-compatible NSS status enum under the
`NSS_WRAPPER_PROVIDE_STATUS_ENUM` feature macro, auto-detected by CMake when
`nss.h` and `nss_common.h` are absent. The local Windows workspace can validate
recipe syntax and Conan export only.

## Verification

Local verification performed:

- `python -m py_compile conanfile.py test_package/conanfile.py`
- `conan inspect .`
- `conan export .`
- `git diff --check -- archives/n/nss-wrapper`

OHOS old-port verification:

- `conan create` passed in
  `/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-nss-wrapper-1.1.16-conan-r7-oldport-final-20260730-071122-59157`.
- `test_package` verifies LD_PRELOAD passwd/group/hostname behavior.
- Official upstream CTest entries were inventoried but not run because
  `UNIT_TESTING=ON` requires `cmocka >= 1.1.0`; details are tracked in
  `1.1.16/reports/upstream-tests.md`.
