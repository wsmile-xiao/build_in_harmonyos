# gnu-getopt

GNU getopt compatibility library for musl-based systems.

## Description
This package provides a GNU getopt implementation compatible with musl libc.
It includes getopt, getopt_long, and getopt_long_only functions.

## Usage
After installation, compile your programs with:
```bash
CFLAGS="-Dgetopt=gnu_getopt -Dgetopt_long=gnu_getopt_long -Dgetopt_long_only=gnu_getopt_long_only"
LDFLAGS="-lgnu_getopt"
```

## License
GNU General Public License
