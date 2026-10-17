# libSM 1.2.6 validation report

Upstream tests: **0/0**. Upstream registers no test cases; the mandatory
`make -j1 check` target completed successfully for both shared and static builds.

Adapted consumers: **2/2**. Both independent installed-package consumers passed;
their repeated execution against shared and static variants is counted once.

## Consumer results

| Consumer | Result | Contract |
| --- | --- | --- |
| Error-handler contract | PASS | Round-trips client and manager error-handler registration and validates public protocol constants. |
| Memory-lifecycle contract | PASS | Allocates and releases a multi-value `SmProp` and a reason-message vector through public APIs. |

The consumers contain 16 internal checks. Those checks and the repeated package
variants are evidence within two flows, not additional test cases.

## Package results

- Shared package: AArch64 `libSM.so.6.0.1`, SONAME `libSM.so.6`, NEEDED `libICE.so.6`, three public headers, relocatable `sm.pc`, and required public symbols.
- Static package: `libSM.a` with six unique members, three public headers, relocatable `sm.pc`, and no shared-library payload.
- Both packages contain the upstream license and omit `libSM.la`.
- W0 downloaded the exact xorgproto and xtrans package revisions from `ohpcd`; libICE was built locally from the exact recipe merged into `origin/main`.

## Evidence

- Run: `libsm-1.2.6-fresh-w3-r6`
- Device: HarmonyOS HongMeng Kernel 1.12.0, AArch64
- Toolchain: Conan 2.29.1, clang 15.0.4
- Independent validator: `LIBSM_R6_RESULT_VALID=1 upstream=0/0 adapted=2/2`
- Input archive SHA-256: `da9101320dc8bb777aeacd93d5bac51d088ed8e0934eeea3baacddc6d5cd10b3`
- Result archive SHA-256: `bae69fe0c58b0c231f6f7d4672f99e877d44e845e0430a3db565b075936a46f3`
