# Notes — perl-module-pluggable 6.3

## Overview

Pure Perl module (Module::Pluggable) — provides plugin ability for Perl modules.
Build system: ExtUtils::MakeMaker (Makefile.PL)

## Build Process

1. `perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site`
2. `make` — copies .pm files to blib/
3. `make test` — 45 test files, 192 tests
4. `make install DESTDIR=$TEST_PREFIX` — staging install
5. `make install` — local install to ~/usr/local

## Key Environment

```
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0:/storage/Users/currentUser/usr/local/lib/perl5
```

## Test Results

- 44/45 test files passed
- 190/192 subtests passed
- 1 failure: t/29unreadable.t (platform limitation — chmod not enforced)
- 1 skipped: t/27app_fatpacker.t (App::FatPacker not available)

## Functional Test Results (2026-06-23)

Comprehensive functional testing performed on OpenHarmony platform:

| Test | Description | Result |
|------|-------------|--------|
| 1 | Module loading & version | ✅ PASS |
| 2 | Basic plugin discovery (3 plugins) | ✅ PASS |
| 3 | Module::Pluggable::Object interface | ✅ PASS |
| 4 | require => 1 and instantiation | ✅ PASS |
| 5 | Inner package detection | ✅ PASS |
| 6 | Plugin exclusion (except =>) | ✅ PASS |
| 7 | Multiple search paths | ✅ PASS |
| 8 | Subroutine export verification | ✅ PASS |
| 9 | Devel::InnerPackage module | ✅ PASS |
| 10 | Installed file path verification | ✅ PASS |
| 11 | Object interface (inner option) | ✅ PASS |
| 12 | All .pm files present (3 files) | ✅ PASS |
| 13 | Platform compatibility (pure Perl, no binary) | ✅ PASS |

All 13 functional tests passed. Module::Pluggable is fully functional on OpenHarmony.

## Issues and Solutions

### SSL Certificate Download Failure
- **Problem**: init-build failed with SSL certificate verify error downloading from cpan.metacpan.org
- **Solution**: Manually downloaded with `curl --insecure`, then used `--no-download` flag
- **Knowledge**: Platform SSL issue, affects CPAN downloads. Documented in knowledge_gained.

### t/29unreadable.t Test Failure
- **Problem**: Test expects chmod(0200) to make file unreadable, but OpenHarmony doesn't enforce POSIX file permissions
- **Impact**: None — pure Perl module, no binary code. All core functionality tests pass.
- **Resolution**: Known platform limitation, documented in knowledge_gained and Gotchas (E046 chmod not enforced)
- **Reference**: perl-dbd-pg compilation also encountered SELinux/HMDFS permission issues on OpenHarmony

### Comparison with perl-dbd-pg Experience
- **perl-dbd-pg**: Required complex patches for SELinux HMDFS restriction (DBI::DBD loading, CRT files missing, HNP packages)
- **perl-module-pluggable**: No patches needed — pure Perl module avoids all platform binary restrictions
- **Key insight**: Pure Perl modules are ideal candidates for OpenHarmony porting — no compilation, no signing, no SELinux issues

## Knowledge Gained

1. Pure Perl modules compile cleanly on OpenHarmony with MakeMaker, no source modifications needed
2. OpenHarmony doesn't enforce POSIX file permissions (chmod), affecting tests that rely on permission checks
3. SSL certificate verification may fail for CPAN downloads — use `curl --insecure` or `--no-download` flag
4. PERL5LIB must include site_perl path for proper module resolution

---
