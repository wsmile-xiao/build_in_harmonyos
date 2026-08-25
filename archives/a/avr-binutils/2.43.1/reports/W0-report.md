# W0 report: avr-binutils 2.43.1

- Issue: #2244
- Date: 2026-08-17
- Dependency role: first package in the avr-binutils -> avr-gcc-bootstrap -> avr-libc chain.

## Dependencies

- Runtime: OHOS base system only.
- Required build tools supplied by the CI image: sh, GNU make, Clang/LLVM,
  binary-sign-tool, GNU as, and GNU ld.
- Optional test tool: DejaGNU/runtest. No matching recipe is published in
  the ohpcd Conan remote, so the DejaGNU target matrix is conditional.

## Source and build system

- Source: GNU binutils 2.43.1 release archive.
- SHA256: 13f74202a3c4c51118b797a39ea4200d3f6cfbe224da6d1d95bb938480132dfd.
- Build system: Autotools, native OHOS/AArch64 host, AVR target.
- Upstream tests: 25,185 testsuite files, including 372 DejaGNU drivers.
- Always-run official subset: six libiberty checks.

## Decision

No separately packaged required library is missing. Proceed with the
single-package OHOS build and test for issue #2244.
