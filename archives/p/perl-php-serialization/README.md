# perl-php-serialization (PHP::Serialization)

## Description

PHP::Serialization is a simple, flexible means of converting the output of PHP's `serialize()` into the equivalent Perl memory structure, and vice versa. It provides bidirectional conversion between PHP serialized format and Perl data structures.

## Versions

- **0.34** (2026-06-24) — built
  - Build system: Perl ExtUtils::MakeMaker
  - Pure Perl module, no C compilation required
  - Platform: HarmonyOS (aarch64)
  - Perl: 5.42.0
  - Tests: 10/10 PASS (17 official tests) + 32/32 functional tests
  - Quality gates: G0-G4 all PASS
  - Submit self-check: 6/6 PASS
  - Precompiled package: `perl-php-serialization-0.34-ohos-aarch64.tar.gz` (21KB)
  - No patches required (source unmodified)
  - Upload requirements: ✅ Met

## Installation

```bash
# Install from precompiled package
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-php-serialization 0.34

# Or manual install from source
perl Makefile.PL INSTALL_BASE=$HOME/usr/local
make && make test && make install
```

## Usage

```perl
use PHP::Serialization;

# Serialize Perl data to PHP format
my $data = { name => "test", value => 42, items => [1, 2, 3] };
my $php_string = PHP::Serialization::serialize($data);
# Result: a:3:{s:4:"name";s:4:"test";s:5:"value";i:42;s:5:"items";a:3:{i:0;i:1;i:1;i:2;i:2;i:3;}}

# Deserialize PHP format back to Perl
my $perl_data = PHP::Serialization::unserialize($php_string);
```

## Test Results

| Test Category | Tests | Pass | Notes |
|---------------|-------|------|-------|
| Official test suite (make test) | 17 | 17 | All PASS |
| Custom functional tests | 32 | 32 | All PASS |
| Precompiled package | 5 | 5 | All PASS |
| Submit self-check | 6 | 6 | All PASS |

## Quality Gates

| Gate | Result |
|------|--------|
| G0 Clean build verify | PASS |
| G1 Binary integrity | PASS (N/A - pure Perl) |
| G2 Functional availability | PASS |
| G3 Portability | PASS (N/A - pure Perl) |
| G4 Archive integrity | PASS |
