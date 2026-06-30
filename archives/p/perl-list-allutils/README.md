# perl-list-allutils

List::AllUtils 0.19 - Combines List::Util, List::SomeUtils and List::UtilsBy in one bite-sized package

## Description

This is a pure Perl module that provides a unified interface to various list utility functions from List::Util, List::SomeUtils, and List::UtilsBy. It simplifies importing functions from these three modules by providing a single entry point.

## Platform Compatibility

✅ **OpenHarmony aarch64**: Full compatibility, all 27 tests passed

## Dependencies

- List::SomeUtils >= 0.58
- List::Util >= 1.56
- List::UtilsBy >= 0.11

## Installation

### From cmd-pkgs (Recommended)
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-list-allutils 0.19
```

### Manual Installation
```bash
tar xzf perl-list-allutils-0.19-ohos-aarch64.tar.gz
cp -r lib/* ~/usr/local/lib/
```

## Usage

```perl
# Set PERL5LIB or use -I parameter
use List::AllUtils qw(max min sum any all uniq sort_by);

# List::Util functions
my @arr = (1, 2, 3, 4, 5);
print max(@arr);    # 5
print min(@arr);    # 1
print sum(@arr);    # 15

# List::SomeUtils functions
print "Has >3: " . (any { $_ > 3 } @arr ? "yes" : "no");  # yes
print "All >0: " . (all { $_ > 0 } @arr ? "yes" : "no");  # yes

# List::UtilsBy functions
my @words = ('apple', 'pie', 'banana');
print join(",", sort_by { length($_) } @words);  # pie,apple,banana
```

## Test Results

| Test Suite | Status | Details |
|------------|--------|---------|
| Official Tests | ✅ PASS | Files=4, Tests=27 |
| Functional Tests | ✅ PASS | 16 manual tests |

## Notes

1. This is a pure Perl module with no XS code - no platform-specific compilation needed
2. Set `PERL5LIB=~/usr/local/lib/site_perl/5.42.0` before using
3. All dependencies must be installed first
