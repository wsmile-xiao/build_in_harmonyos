# perl-power-tools

Pure Perl implementation of BSD utilities.

## Description

Perl Power Tools (also known as PPP or ppt) is a collection of BSD utilities
reimplemented in pure Perl. It provides over 100 command-line tools including
cat, echo, grep, sort, wc, seq, factor, and many more.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.053 | published | 2026-06-25 |

## Build System

- **Type**: ExtUtils::MakeMaker (Makefile.PL)
- **Configure**: `perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX`
- **Note**: Uses INSTALL_BASE instead of PREFIX (ExtUtils::MakeMaker convention)
- **No C compilation**: Pure Perl, no XS, no ELF binaries

## Dependencies

- Perl 5.42.0+ (runtime)
- No external C library dependencies (pure Perl)
- Test-only dependencies (not required at runtime):
  - Test::Warnings 0.038
  - Test::Pod 1.52
  - IPC::Run3 0.049

## Homepage

- CPAN: https://metacpan.org/dist/PerlPowerTools
- GitHub: https://github.com/briandfoy/PerlPowerTools

## Installation Notes

- Install via: `perl Makefile.PL INSTALL_BASE=$PREFIX && make && make install`
- Installs 100+ BSD utility scripts to `$PREFIX/bin/`
- **Warning**: Installed utilities (cat, grep, sort, tar, etc.) will shadow system
  commands if `$PREFIX/bin` is early in PATH. Set `PATH=/system/bin:$PATH` if
  system tools are needed during testing.
- uudecode file permissions may differ from expected (660 vs 664) due to
  OpenHarmony SELinux/chmod limitations (E046). Decoding functionality is unaffected.

## Quality Gates

| Gate | Description | Result |
|------|-------------|--------|
| G0 | Clean build verification | PASS |
| G1 | Binary integrity | PASS (0 ELF binaries) |
| G2 | Functional availability | PASS |
| G3 | Portability (RPATH/signing) | PASS (N/A - pure Perl) |
| G4 | Archive integrity | PASS |
