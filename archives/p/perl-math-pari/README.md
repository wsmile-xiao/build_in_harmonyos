# perl-math-pari

Perl interface to PARI/GP mathematical library for advanced number theory computations.

## Overview

Math::Pari provides Perl access to the PARI/GP library, enabling sophisticated mathematical operations including:

- Integer factorization and primality testing
- Elliptic curve computations
- Galois theory and field extensions
- Polynomial operations
- Algebraic number field calculations
- Transcendental functions with arbitrary precision

## Version Information

- **Current Version**: 2.030528-r1
- **PARI Library**: 2.3.5 (embedded)
- **Status**: Built (OpenHarmony platform)

## Installation

### OpenHarmony Platform

XS modules on OpenHarmony require HNP package installation due to SELinux restrictions.

```bash
# Download HNP package
curl -O https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/perl-math-pari-2.030528-r1-ohos-aarch64.tar.gz

# Install (requires admin privileges)
# Contact system administrator for HNP installation
```

**Note**: This module cannot be loaded from `~/usr/local/lib` due to SELinux HMDFS domain restrictions.

## Dependencies

- Perl >= 5.42.0

## Usage Examples

```perl
use Math::Pari;

# Factorization
my $f = Math::Pari::factorint(123456789);

# Primality testing
my $is_prime = Math::Pari::isprime(17);

# Elliptic curves
my $E = Math::Pari::ellinit([0, 0, 0, -4, 0]);

# Polynomial operations
my $p = Math::Pari::Pol([1, 2, 3]);
```

## OpenHarmony Build Notes

### CRT Files Issue

OpenHarmony uses musl libc which does not provide standard CRT startup files (crti.o, crtbeginS.o, etc.). This causes link failures for XS modules.

**Solution**: Modify Makefile LDDLFLAGS:
```makefile
LDDLFLAGS = -shared -nostartfiles -L/storage/Users/currentUser/usr/local/lib -lc -O2 -fstack-protector-strong
```

### SELinux HMDFS Restrictions

XS modules cannot be dynamically loaded from HMDFS-mounted directories (`~/usr/local`). They must be installed in HNP system directories with `hnp_file:s0` SELinux context.

## Documentation

- [PARI/GP User Manual](https://pari.math.u-bordeaux.fr/doc.html)
- [Math::Pari POD](https://metacpan.org/pod/Math::Pari)

## License

GPL-2.0-or-later AND Artistic-1.0-Perl (Perl dual license)

## Links

- [CPAN Distribution](https://metacpan.org/release/Math-Pari)
- [PARI/GP Homepage](https://pari.math.u-bordeaux.fr/)
- [OpenHarmony Build Archive](./2.030528-r1/)