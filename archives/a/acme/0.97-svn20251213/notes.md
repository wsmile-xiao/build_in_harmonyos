# acme 0.97-svn20251213 OHOS Notes

This package adapts the Debian 1:0.97~svn20251213+ds-2 source snapshot of
ACME, a cross assembler for 6502/6510/65c02/65816-family CPUs.

The upstream project is a plain Makefile build rooted in src/. It has no
third-party library dependencies beyond libc and libm. The Makefile hardcodes
gcc and strips the binary after linking; the OHOS recipe passes CC=clang and
patches out the unconditional strip so the generated executable can be signed
before it is run.

The recipe runs the upstream testing/ suite after building and signing the
fresh src/acme binary. The suite covers the upstream auto, bugfixes, cliargs,
cpus, errors, and warnings test groups.

The consumer test assembles a small 6502 program with the packaged acme binary,
checks the generated file is non-empty, and verifies the exact output bytes.
