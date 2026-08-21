# W0 dependency report

- Package: `avr-libc/2.2.1`
- Issue: 2240
- Initial check: 2026-08-17
- Resolved: 2026-08-21
- Remote: `ohpcd` (`https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`)
- Client: OHOS-adapted Conan 2.29.1 in an isolated local `CONAN_HOME`

## Initial queries

```text
conan list "avr*/*" -r=ohpcd
  avrdude/8.1
  avro-tools/1.12.1

conan list "binutils/*" -r=ohpcd
  0 matching recipes

conan list "gcc/*" -r=ohpcd
  gcc/9.5.0

conan list "autoconf/*" -r=ohpcd
  autoconf/2.72

conan list "automake/*" -r=ohpcd
  automake/1.18
```

The published `gcc/9.5.0` recipe is a native AArch64 OHOS compiler and cannot
replace an AVR cross-compiler. The required dependency work therefore remained
outside issue #2240 and was completed in this order:

1. `avr-binutils/2.43.1`: issue #2244, PR #5709, true-device CI pass.
2. `avr-gcc-bootstrap/14.2.0`: issue #2245, PR #5682, true-device CI pass.
3. `avr-libc/2.2.1`: issue #2240, true-device Shadow CI pass.

## Resolution

The exact AVR Binutils and bootstrap GCC packages were available in the device
dependency cache for the final run. The full Conan graph resolved and the package
completed with `Total: 1`, `Success: 1`, `Failed: 0`.

Full upstream execution additionally needs a separately packaged `avrtest` or
`simulavr`. This optional gap does not block the compile/link validation and does
not belong in the avr-libc PR.
