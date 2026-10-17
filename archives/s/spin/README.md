# spin

Efficient verification tool for multi-threaded software (model checker for Promela).

Spin is a popular open-source model checking tool for the formal verification of distributed systems. It supports the analysis of multi-threaded software systems, with particular emphasis on proving the correctness of concurrent and distributed protocols.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 6.5.2 | built | 2026-06-08 |

## Notes

- Build system: custom Makefile (no configure script)
- Requires `bison -y` for yacc-compatible output
- Requires `ld.bfd` linker (`-fuse-ld=bfd`) to avoid OHOS SDK lld libxml2 dependency issue