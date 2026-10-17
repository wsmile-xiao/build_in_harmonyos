# agedu 20211129.8cd63c5

## Source

The package uses the Debian copy of the upstream original archive. It corresponds
to upstream commit `8cd63c5778d2e2872d951b775292ee8025bdcca4`, which introduced
the CMake build system.

## Build

The upstream CMake project builds the `agedu` executable on Unix-like platforms.
No upstream test target or test suite is provided, so the recipe does not claim
that upstream tests ran.

## Consumer test

The test package scans a fixture directory, checks that the index database is
created, then dumps that index and checks that it contains the scanned path.

## Platform constraint

The initial HarmonyOS adaptation is restricted to armv8. True-device validation
on ohos-aarch64 passed on 2026-08-06.
