# perl-parallel-prefork

A simple prefork server framework for Perl.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.18 | built | 2026-07-03 |

## Description

Parallel::Prefork is a simple prefork server framework. It provides a
minimalistic interface for creating preforking server processes with
support for graceful shutdown, signal handling, and spare worker
management.

## Build System

Pure Perl module using ExtUtils::MakeMaker (Makefile.PL).

## Dependencies

- Class::Accessor::Lite
- List::MoreUtils
- Proc::Wait3
- Scope::Guard
- Signal::Mask
