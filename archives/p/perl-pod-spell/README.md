# perl-pod-spell

Pod::Spell - Format POD for spell-checking

## Description

Pod::Spell is a Perl module that converts POD (Plain Old Documentation) into
plain text suitable for spell-checking. It strips POD markup, removes Perl
jargon stopwords, and handles code expressions, abbreviations, and hyphenated
words. It provides both an object-oriented API and a command-line tool
(podspell) for processing POD files.

## Versions
- 1.27 (2026-06-25) — published

## Build System
- Perl ExtUtils::MakeMaker (Makefile.PL)
- Pure Perl module, no C compilation required

## Dependencies
- Class::Tiny (>= 1.008)
- File::ShareDir (>= 1.118)
- File::ShareDir::Install (>= 0.14)
- Lingua::EN::Inflect (>= 1.905)
- Pod::Simple (>= 3.27, core in Perl 5.42.0)
- Text::Wrap (core)
- Pod::Escapes (core)
- Test::More (for testing only)

## HarmonyOS Compatibility
- ✅ All 54 official tests pass (8 test files)
- ✅ All 22 custom functional tests pass
- ✅ CLI tool (podspell) works correctly from installed location
- ✅ Stopword list loaded from shared file (2431 entries)
- ✅ Custom stopwords via `=for stopwords` directive works
- ✅ UTF-8/wide character handling with `no_wide_chars` option works
- ✅ G1-G4 quality gates all PASS
- ✅ Submit check 6/6 PASS (manifest, progress, patches, packaging, temp files, test report)
- ✅ No platform-specific patches needed (pure Perl, no ELF binaries)
- ✅ No E078 (musl BIND_NOW) issues (unlike XS modules like perl-dbd-pg)

## Comparison with perl-dbd-pg (XS Module)
| Issue | perl-dbd-pg (XS) | perl-pod-spell (Pure Perl) |
|-------|------------------|----------------------------|
| CRT files missing | ✅ Fixed with OTHERLDFLAGS | ❌ N/A (no C compilation) |
| E078 musl BIND_NOW | ✅ Fixed with -lperl linking | ❌ N/A (no .so files) |
| ELF signing | ✅ Required for Pg.so | ❌ N/A (no ELF binaries) |
| File::ShareDir | ❌ N/A | ✅ Required for wordlist |
| PERL5LIB deps | ✅ Required | ✅ Required |

## Installation
```bash
# Set PERL5LIB for dependencies
export PERL5LIB=$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/5.42.0

# Use the module
perl -MPod::Spell -e 'print "Pod::Spell v$Pod::Spell::VERSION\n"'

# Convert POD to spell-checkable text
echo "=head1 NAME\n\nMyModule - A module" | podspell

# Programmatic API
perl -MPod::Spell -e '
my $ps = Pod::Spell->new;
$ps->parse_from_file("Module.pm", \*STDOUT);
'
```

## Key Features
- **Stopword filtering**: 2431 built-in Perl jargon words (undef, autovivify, etc.)
- **Custom stopwords**: Add via `=for stopwords word1 word2` in POD
- **Stopword negation**: `=for :stopwords !word` to unlearn a stopword
- **Code expression filtering**: $var, @array, Foo::Bar, method() filtered out
- **Abbreviation preservation**: Ph.D., WinX32 kept intact
- **Hyphenated word splitting**: hyphenated-foo → checks "hyphenated" and "foo" separately
- **UTF-8 support**: Wide characters handled; `no_wide_chars` option for Latin-1 only spellcheckers
- **Debug mode**: Via constructor `debug => 1` or `PERL_POD_SPELL_DEBUG=1` env var

## Quality Reports
- `1.27/reports/test-report.md` — Official test suite results (54/54 PASS)
- `1.27/reports/functional-test-report.md` — Custom functional tests (22/22 PASS)
- `1.27/reports/quality-report.md` — Quality gate G1-G4 results
