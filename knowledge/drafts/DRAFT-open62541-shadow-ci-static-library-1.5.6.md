# DRAFT: open62541 static-library shadow CI must validate the consumer instead of the package binary

> Status: Draft | Updated: 2026-09-10
> Source event: `open62541/1.5.6` single-package HarmonyOS shadow CI

## Problem

`open62541` is packaged as a static library. The package itself has no
executable under `bin/`, so an executable-oriented smoke test cannot be used as
the primary package test. Treating this as a failed runtime test produces a
false negative.

## Verification Pattern

The `test_package` should build a small C consumer against the installed Conan
package and exercise a stable public API:

1. Include `open62541/server.h`.
2. Create a `UA_Server`.
3. Obtain the server configuration.
4. Apply a minimal configuration.
5. Delete the server and return success.

On a cross build, compile and link the consumer but skip host execution. On a
HarmonyOS shadow device, execute the consumer and retain the real output.

The CI classification is therefore:

- L1: consumer compile, link, and device execution pass.
- L2: package executable smoke check skipped because the package is static-only.
- L4: security/package scan pass.
- L5: `lib/` artifact presence and integrity pass.

## Negative Validation

Keep a destructive negative check that removes the package's library payload
from an isolated copy and reruns the consumer check. The test must fail in that
condition. This proves that the consumer really links against the packaged
artifact instead of a system or stale shared prefix.

## Scope

This pattern applies to static C/C++ libraries whose public API can be exercised
without starting a network service. It does not replace upstream unit tests;
for open62541, the Check-based unit suite remains a separate test-only
 dependency and was not enabled in the production recipe.
