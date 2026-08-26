# Validation: avr-gcc-bootstrap 14.2.0

Date: 2026-08-19
Issue: #2245

## Local preflight

- Python AST parsing passed for the recipe and test_package.
- YAML parsing passed for conandata.yml, manifest.yaml, and MANIFEST.yml.
- `git diff --check` passed.
- GCC 14.2.0 and the official GMP 6.2.1, MPFR 4.1.0, and MPC 1.2.1
  archives were checksum-verified.
- All four source patches applied in the shadow build.
- avr-binutils/2.43.1 from issue #2244 passed its independent device CI.
- A cached-package Conan test validated the target-tool dispatcher before the
  final full rebuild.

## True-device shadow CI

- Runner mode: `heavy --lock`, global single-package lock acquired.
- Run ID:
  `codex-avr-gcc-bootstrap-shadow-ci-r18-2245-20260819-181549-8619`.
- Tested commit: `19bb09c0ce7c7c45a78d08c89f2e9e27b8d1d7d7`.
- Runner exit code: 0.
- Duration: 3155 seconds, including 26 seconds waiting for the lock.
- G0 and L0 passed.
- L1 passed: full Conan create, GCC selftest target, 16 official torture
  compiles, and test_package executed.
- The release build reports internal self-tests are not enabled; this is not
  counted as an assertion pass.
- L2 passed. `avr-gcc-ar`, `avr-gcc-nm`, and `avr-gcc-ranlib` report failure
  because plugin support is intentionally disabled; the compiler and gcov
  command set passed.
- L4 emitted a non-blocking patch scanner warning for
  `0002-build-hmdfs-shell-scripts.patch`.
- L5 passed with packaged `bin/` content.
- The post-build recipe change in `conandata.yml` was CI mirror injection and
  has been adopted into the final recipe input.
- The test output is now directed to runner `TMPDIR` so future snapshots do not
  leave `smoke.elf` in the source tree; dispatcher behavior is covered by the
  cached Conan test.

## Functional evidence

- Generated libgcc Makefile: `fixed_point = no`.
- Compiler multilib output contains only `.` and `avr5`.
- Eight official no-header torture sources compiled at both `-O0` and `-O2`
  (16 compile checks).
- The package test selected package-owned `avr5/libgcc.a`.
- Consumer output is `elf32-avr`, architecture `avr:5`, 102 bytes.
- `main` and `__udivmodhi4` are present in the linked image.

Package reference produced by r18:

```text
avr-gcc-bootstrap/14.2.0#fff11bfdc0f6b1e14afcd080fa5a2a32:6b129b068851896169fae42d399fa922d239ce8a#30d8784bca435eeb9bcfdcc73e0fbe2b
```