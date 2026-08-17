# W0 dependency report

- Package: `avr-libc/2.2.1`
- Issue: 2240
- Checked: 2026-08-17
- Remote: `ohpcd` (`https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`)
- Client: OHOS-adapted Conan 2.29.1 in an isolated local `CONAN_HOME`

## Queries

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

## Decision

Blocked. Upstream requires GNU Binutils and GCC built for target `avr`. The
published `gcc/9.5.0` recipe is a native AArch64 OHOS compiler and cannot
replace an AVR cross-compiler.

Required dependency work must remain outside issue 2240 and follow this order:

1. `avr-binutils/2.43.1`
2. `avr-gcc-bootstrap/14.2.0` (C frontend plus target libgcc, no avr-libc cycle)
3. Resume `avr-libc/2.2.1`

Full upstream execution tests additionally need a separately packaged
`avrtest` or `simulavr`; this optional gap does not belong in the avr-libc PR.
