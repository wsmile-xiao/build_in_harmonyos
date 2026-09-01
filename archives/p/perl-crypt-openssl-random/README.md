# perl-crypt-openssl-random

Crypt::OpenSSL::Random — OpenSSL/LibreSSL pseudo-random number generation Perl XS module.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.17-r1 | built | 2026-07-03 |

## Description

This module provides Perl bindings to the OpenSSL pseudo-random number generation functions (RAND_bytes, RAND_pseudo_bytes, etc.).

## Build System

Perl ExtUtils::MakeMaker (Makefile.PL + make)

## Dependencies

- OpenSSL 3.5.6 (system)
- Crypt::OpenSSL::Guess 0.15 (Conan @ohpcd/stable)
- Perl 5.42.0
