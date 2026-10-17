# DRAFT: open62541 raw Ethernet support needs a paired CMake capability boundary

> Status: Draft | Updated: 2026-09-10
> Source event: `open62541/1.5.6` HarmonyOS PC shadow CI link failure

## Symptom

When the OHOS sysroot lacks the Linux raw-socket headers required by the raw
Ethernet implementation, the consumer link can fail with:

```text
undefined symbol: UA_ConnectionManager_new_POSIX_Ethernet
```

The error is easy to misdiagnose as a missing library or a bad Conan
`package_info()` declaration.

## Root Cause

`eventloop_posix_eth.c` includes Linux kernel networking headers that conflict
with the OHOS musl socket headers. The source therefore cannot be compiled on
the target. The default CMake source list and
`plugins/ua_config_default.c` must make the same capability decision; otherwise
the registration can reference `UA_ConnectionManager_new_POSIX_Ethernet` even
when its implementation is not compiled.

## Adaptation

Use a build-system capability boundary shared by both locations:

1. Add `UA_ENABLE_POSIX_ETHERNET`, defaulting to `ON` so ordinary POSIX/Linux
   builds retain upstream behavior.
2. Let the Conan OHOS configuration set the option to `OFF`, which removes
   `eventloop_posix_eth.c` from `plugin_sources`.
3. Define `UA_ENABLE_POSIX_ETHERNET` for `open62541-plugins` only when the
   option is enabled, and use that capability definition for the matching
   default registration.

The two changes are a pair. Guarding only the source file leaves a link-time
failure; guarding only the registration leaves header conflicts in the source.

Raw Ethernet support should not be replaced with a fake implementation. Keep
the normal TCP/UDP POSIX event loop available and document the disabled
capability. Do not introduce platform macros into source patches when a
feature option expresses the actual build capability.

## Verification

The `open62541/1.5.6` recipe applies:

- `0002-cmake-posix-ethernet-option.patch`
- `0003-plugins-ua_config_default.c.patch`

The final OHOS shadow CI run built and linked the consumer, created a minimal
`UA_Server`, executed the test binary on the device, and passed the destructive
negative package-content check.

## Scope

Use this pattern for open62541's raw Ethernet capability boundary. It should
not be generalized to disable all Linux networking or all POSIX event-loop
code.
