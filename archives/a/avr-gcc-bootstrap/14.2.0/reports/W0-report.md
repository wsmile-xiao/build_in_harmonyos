# W0 report: avr-gcc-bootstrap 14.2.0

- Issue: #2245
- Date: 2026-08-17
- Dependency role: second package in the avr-binutils -> avr-gcc-bootstrap -> avr-libc chain.

## Dependencies

- Required Conan build dependency: avr-binutils/2.43.1 (#2244).
- GCC-required build sources: GMP 6.2.1, MPFR 4.1.0, MPC 1.2.1.
- The three prerequisite versions come from GCC 14.2.0's official
  contrib/download_prerequisites script and are checksum pinned.
- ISL is optional and disabled; gettext is unnecessary with NLS disabled.
- Full target execution tests need DejaGNU and an AVR simulator and are not
  required to build the bootstrap compiler.

## Source and build system

- Source: GNU GCC 14.2.0 release archive.
- SHA256: a7b39bc69cbf9e25826c5a60ab26477001f7c08d85cec04bc0e29cabed6f3cc9.
- Build system: GCC top-level Autotools, OHOS/AArch64 host, AVR target.
- Scope: C frontend and target libgcc only.

## Decision

Proceed after avr-binutils/2.43.1 passes its independent device CI and is
available to the isolated #2245 Conan job.
