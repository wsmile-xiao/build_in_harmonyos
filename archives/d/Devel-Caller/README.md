# Devel-Caller

Devel::Caller is a Perl module that provides utilities for accessing the call stack and caller information in Perl programs.

## Description

This module provides enhanced access to caller information beyond what Perl's built-in `caller()` function provides. It can extract lexical variables from outer scopes and provides debugging utilities.

## Build Status

| Version | Status | Date |
|---------|--------|------|
| 2.07 | built | 2026-06-11 |

## Dependencies

- Perl 5.42.0
- PadWalker 2.5
- musl 1.2.5

## Known Limitations

1. **XS Module Loading**: The XS module (Caller.so) cannot be loaded from HMDFS due to SELinux restrictions. Requires administrator installation to system directory `/data/service/hnp/`.

2. **Compilation Requirements**: Requires special linker flags (`-nostartfiles -nodefaultlibs -lc`) and environment variables (`CPATH`, `LIBRARY_PATH`) for musl compatibility.

## Usage

```perl
use Devel::Caller qw(caller_cv caller_vars);

# Get code reference from caller
my $cv = caller_cv(0);

# Access lexical variables from caller's scope
my $vars = caller_vars(1);
```

## Links

- CPAN: https://metacpan.org/pod/Devel::Caller
- Repository: https://github.com/richardc/perl-devel-caller