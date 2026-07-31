# nss-wrapper 1.1.16 adaptation notes

## Environment

- Build system: CMake
- Date: 2026-07-30
- Status: built

## Build flow

The Conan recipe downloads upstream `nss_wrapper-1.1.16.tar.gz`, configures
CMake with `UNIT_TESTING=OFF` by default, builds the shared interposition
library, and installs upstream CMake/pkg-config files plus `nss_wrapper.pl`.
The optional `with_upstream_tests=True` mode adds the test-only
`cmocka/2.0.2` dependency, enables `UNIT_TESTING=ON`, and runs CTest during
the Conan build step.

## Platform findings

| # | Finding | Impact | Handling |
|---|---------|--------|----------|
| 1 | OHOS does not provide `nss.h` or Solaris `nss_common.h`; upstream stops with `No nsswitch support detected`. | Build cannot compile module status handling even though the needed ABI is only the glibc-compatible NSS status enum. | `0001-ohos-nss-status.patch` defines `NSS_WRAPPER_PROVIDE_STATUS_ENUM` when both NSS headers are missing, uses that feature macro for the fallback enum, and guards an unconditional `getgrent_r` libc binding with the upstream `HAVE_GETGRENT_R` configure result. |
| 2 | Runtime behavior depends on `LD_PRELOAD` interposing libc functions. | A simple link test does not prove NSS behavior. | Test package runs under `LD_PRELOAD` and verifies passwd, group, uid/gid, and hostname substitution. |
| 3 | Upstream unit tests require `cmocka`, NSS helper fallbacks, and accurate shadow API detection. | Initial OHOS probes failed at `cmocka_DIR-NOTFOUND`, then at test-source assumptions after cmocka was available. | `with_upstream_tests=True` now uses local `cmocka/2.0.2`, applies the same NSS status fallback to the test helper, gates shadow tests on actual `setspent/getspent/endspent/getspnam` availability, and runs 9 registered CTest entries successfully. |

## Verification

Local preflight completed on the workspace branch:

```bash
python -m py_compile archives/n/nss-wrapper/1.1.16/conanfile.py archives/n/nss-wrapper/1.1.16/test_package/conanfile.py
conan inspect archives/n/nss-wrapper/1.1.16
conan export archives/n/nss-wrapper/1.1.16
git diff --check -- archives/n/nss-wrapper
```

OHOS verification:

- r7 old port `conan create` PASS:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-nss-wrapper-1.1.16-conan-r7-oldport-final-20260730-071122-59157`.
- Full ref:
  `nss-wrapper/1.1.16#a444794aaab80bf9e6e044488264cf69:01d92cf349a0dd98ff915f4bd99a04430171517f#d842d0879ede1a342f87e42504228f0f`.
- L0/L1/L4/L5/L1e pass; L2 skip because `nss_wrapper.pl` has no conventional `--help`/`--version` behavior.
- Official upstream CTest with `with_upstream_tests=True` PASS:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-upstream-r4-rerun1-20260730-204550-6012`.
- Upstream CTest result: 9/9 registered tests passed. `test_shadow` is not
  registered on OHOS because `shadow.h` exists but
  `setspent/getspent/endspent/getspnam` are unavailable.
- Full upstream-test package ref:
  `nss-wrapper/1.1.16#892c8c3c58712838a3ab20804f6c5334:e3efca24846c41be08e762f51b5ef2e4ee8008cd#79c3862b3f1b06501f5c0e758de8434b`.

## OHOS rounds

- r1 old port: runner harness error only; script path was missing, rc=127 before Conan started.
- r2 old port: true build failed in `src/nss_wrapper.c` because OHOS lacks `nss.h`/`nss_common.h`; added `0001-ohos-nss-status.patch`.
- r7 old port: build/test_package passed; cmocka upstream-test probe recorded separately.
- cmocka dependency probe new port:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-nss-wrapper-cmocka-upstream-r2-upstream-cmocka-r2-20260730-193826-36790`.
  `cmocka/2.0.2` built and test_package passed 2/2; `nss-wrapper` found `cmocka::cmocka` and completed configure/generate, then stopped in upstream test-source compilation.
- upstream r4 rerun1 new port: optional `with_upstream_tests=True` build passed
  all 9 registered CTest entries; shadow test correctly stayed unregistered on
  OHOS due to missing shadow functions.
