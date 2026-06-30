# perl-perlio-utf8_strict

Fast and correct UTF-8 IO - PerlIO layer C implementation for fast UTF-8 encode/decode.

## Description

PerlIO::utf8_strict provides a PerlIO layer that implements fast and correct UTF-8 encoding and decoding. Unlike the built-in `:utf8` layer which is lenient, this module strictly validates UTF-8 according to the Unicode standard, rejecting invalid sequences.

## Technical Details

- **Type**: XS(C) module (requires C compilation)
- **Build System**: Perl ExtUtils::MakeMaker (Makefile.PL)
- **Author**: Leon Timmermans, Christian Hansen
- **License**: Perl 5 (Artistic/GPL dual)
- **CPAN**: PerlIO-utf8_strict

## Versions

| Version | Status | Date | Test Result |
|---------|--------|------|-------------|
| 0.010 | built | 2026-06-24 | 19/20 PASS (95%) |

## HarmonyOS Platform Notes

- **Compilation**: ✅ Clean build, no patches required, clang compiles XS code directly
- **ELF Signing**: ✅ .so signed with binary-sign-tool (.codesign section present)
- **G0-G4 Quality Gates**: ✅ All PASS
- **Functional Testing**: ✅ 19/20 tests pass via embedded Perl + dlopen method
- **SELinux Note**: System Perl (hnp_file:s0) cannot dlopen .so from HMDFS paths (hmdfs:s0). This is a platform-wide limitation for all XS modules. The module functions correctly when the Perl interpreter runs from an HMDFS-context path.
