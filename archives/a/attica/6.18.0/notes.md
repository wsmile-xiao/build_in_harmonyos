# attica 6.18.0 notes

## Scope

This package is part of the KF 6.18 baseline. It adds a mainline-ready
`attica/6.18.0` package directory without modifying other package recipes.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- `providertest` is excluded from the CTest invocation because it depends on
  live OCS network endpoints (`autoconfig.kde.org` and `invalid-url.org`);
  the current OHOS runner can hang while waiting on those external requests.
- Runtime/build dependencies use the current local baseline:
  `qtbase/6.11.1` and `ecm/6.26.0`.

## Verification

Local and OHOS checks:

- Upstream source SHA256 verified locally:
  `eb2b2be33cc83512c77af2559fcaf7fc58ad191abb82cf40b17b2e9e8400e336`.
- Local syntax and whitespace checks passed:
  `python -m py_compile conanfile.py test_package/conanfile.py`,
  and `git diff --check`.
- OHOS low-pressure run:
  `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/attica-r4.log`.
- Full package reference:
  `attica/6.18.0#a0e5aa50e3ff1722f82549dbddf39cfe:57ffd8c720a5bfee7e8827990cd6550a49181c1b#c9ee63499200cb73e0fed5b45cc3cef1`.
- Runner gates:
  L0 pass, L1 pass, L2 skip (`no bin/ dir`), L4 pass, L5 pass.
- Upstream CTest passed 2/2 executed tests:
  `configtest` and `persontest`.
- `test_package` passed 1/1 and printed
  `PASS: Attica value objects OK`.

## Upstream Tests Not Run

- `providertest` was not executed because its upstream test slots require live
  external OCS network access:
  `ProviderTest::testFetchValidProvider` and
  `ProviderTest::testSwitchSortOrder` use
  `https://autoconfig.kde.org/ocs/providers.xml`, while
  `ProviderTest::testFetchInvalidProvider` relies on DNS/network failure
  behavior for `https://invalid-url.org/ocs/providers.xml`. On the current
  OHOS runner these external requests can hang, as observed in the first
  remote attempt.
- `tests/projecttest` was built, but upstream marks it with
  `ecm_mark_as_test()` and does not register it as a CTest entry; it is a
  manual Qt Widgets helper executable.
- The ECM outbound SPDX license test was not executed because the current OHOS
  runner does not provide the `reuse` tool (`ReuseTool` was not found).
- API documentation generation was not executed because `Qt6Tools` /
  `Qt6ToolsTools` were not found by upstream CMake.
