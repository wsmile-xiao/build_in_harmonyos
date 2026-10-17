# perl-sereal-encoder

**Sereal::Encoder** — XS-based Sereal binary serialization encoder for Perl.

High-performance binary encoder that serializes Perl data structures into the
Sereal binary format. Implemented in C/XS with bundled compression libraries
(zstd, miniz, csnappy) compiled statically into the shared library.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 5.004 | published | 2026-06-30 |

## Build System

Perl ExtUtils::MakeMaker (Makefile.PL) — XS module with C code, produces a
shared library (.so) loaded by Perl's XSLoader/DynaLoader.

## Dependencies

- **Perl 5.42.0** — system pre-installed
- **Bundled libraries** — zstd, miniz, csnappy (compiled statically, no external deps)

## Usage

```bash
# Install via Conan
conan install --requires=perl-sereal-encoder/5.004@ohpcd/stable

# Use in Perl
perl -e 'use Sereal::Encoder; my $enc = Sereal::Encoder->new(); my $out = $enc->encode({key => "value"});'
```

## OHOS Adaptations

- ELF signing: `.so` files signed with `binary-sign-tool -selfSign` for HarmonyOS dlopen
- Build env vars: `CPAN_COMPAT=1`, `SEREAL_USE_BUNDLED_LIBS=1`, `USE_UNALIGNED=1`, `NO_ASM=1`
- `.so` runtime loading on HMDFS limited by SELinux (E046) — install to system Perl path for runtime use
- test_package uses file-based verification (not runtime .so loading)

## Notes

- See `5.004/notes.md` for detailed adaptation notes
- Functional test results are documented in `5.004/notes.md`
