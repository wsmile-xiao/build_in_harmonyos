# perl-meta

Perl XS module providing a meta-programming API for Perl.

## Description

The `meta` module provides a meta-programming API that allows Perl code to
inspect and manipulate the symbol table, packages, subroutines, and variables
of a running Perl program. It is authored by Paul Evans (PEVANS) and hosted
on CPAN.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.015-r0 | published | 2026-06-17 |

## Build System

- **Type**: Module::Build (Perl XS module with C code)
- **Build command**: `perl Build.PL --prefix=$PREFIX && ./Build && ./Build install`
- **Compiler**: `cc` (clang 15.0.4 with OpenHarmony SDK sysroot)
- **Key note**: Perl XS modules require `CC=cc LD=cc` for compilation (to use the correct sysroot), but `LD` must be unset at runtime to avoid interfering with dynamic library loading.

## Dependencies

- **Runtime**: Perl >= 5.14
- **Build**: Perl, Module::Build >= 0.4004, ExtUtils::CBuilder

## Known Issues

1. **`LD` env var interference**: The `LD` environment variable (used for compiler override) interferes with musl's dynamic linker at runtime. Unset `LD` before running Perl scripts that load XS modules.
2. **SELinux HMDFS restriction**: XS .so files installed to `~/usr/local/lib` (HMDFS) may be blocked by SELinux. The `hishell_hap` domain can only load `hnp_file` type files.
