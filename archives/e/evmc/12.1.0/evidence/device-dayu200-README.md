# Real-device (DAYU200-RK3568) evidence for evmc 12.1.0

Device  : DAYU200-RK3568, serial `450100445634303332018f3e7d2dba00`
System  : OpenHarmony 6.0.0.47 (API20, aarch64, 64-bit)
Command : mkdir -p upstream_example_vm && cp libexample-vm.so upstream_example_vm/ \
          && LD_LIBRARY_PATH=/lib64:. ./evmc_consumer_case ./upstream_example_vm/libexample-vm.so
Result  : exit_code=0, CONSUMER_RESULT checks=16 passed=16 failed=0, CONSUMER_VERDICT PASS

## Artefacts (sha256)

| file | sha256 |
|---|---|
| `evmc_consumer_case.cpp` (PR test_package source, unmodified) | `0c228c4deba33be2c557621ca0a71566ca2a345bdddf50ec1017749aea8d00bc` |
| `evmc_consumer_case` (aarch64 ELF, device build)            | `3ebb6806d3931a4854ff8718edad8e4f46e1a745cde07eaba86b8f6ae27b58ec` |
| `libexample-vm.so` (upstream example VM, device build)      | `a67b7e0b8b9f06ad55c3de5d4e82a510cfb86b7aa7d77f816061c16991d2088f` |
| `consumer-e2e-device-dayu200.txt` (transcript below)        | `8d758b37af7e03b28b006feeef2894fba819bd40538b357648df0de513eec3d7` |

## Why the device binary is built this way (measured, not assumed)

1. **A statically linked executable cannot `dlopen()` on this image.**
   A fully static probe reports `dlopen(...) -> FAIL: Dynamic loading not supported`
   for *every* path (including `/lib64/libc++_shared.so` and
   `/lib/ld-musl-aarch64.so.1`), while the *dynamically* linked build of the very
   same probe returns `OK` for all of them. A static executable has no dynamic
   loader, so musl's `dlopen` is a stub that fails.
   ⇒ the consumer is built **dynamically linked** on purpose: the loader leg
   (`evmc_load_and_configure` → `dlopen`) is the whole point of this case.

2. The device only ships `/lib/ld-musl-aarch64.so.1` as a real file;
   `/lib64/libc.so` is a symlink to it and `/lib64/libc++_shared.so` is present,
   so `LD_LIBRARY_PATH=/lib64:.` covers both `NEEDED` entries.

3. `vm version : 0.0.0` on device. This is the *device* build of the example VM,
   compiled straight from the upstream v12.1.0 tree without the version define
   that the recipe's own build injects; it is **not** the packaged library and
   says nothing about the package under test. The ABI check
   (`loaded VM reports an ABI version matching EVMC_ABI_VERSION`, ABI 12) and all
   16 content checks pass regardless. The recipe's own evidence
   (`consumer-e2e-output.txt`) is produced from the packaged build and reports
   `vm version : 12.1.0`.

## Reproduction

The exact transcript is `consumer-e2e-device-dayu200.txt`; the machine-readable
per-job record is `device-evidence-dayu200.json`. The run was executed twice on
2026-10-09 (jobs `evmc1210b` and `evmcdev1210`) with byte-identical stdout and
`exit_code=0` both times.
