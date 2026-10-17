# acme

ACME is a multi-platform cross assembler for 6502, 6510, 65c02, and
65816-family CPUs.

## Version

- 0.97-svn20251213: Debian 1:0.97~svn20251213+ds-2 source snapshot,
  adapted for OHOS aarch64.

## Verification

The package installs the acme executable. The recipe runs the upstream
testing/ Makefile suite, and the consumer test assembles a small 6502 source
file with the packaged binary.

## References

- Homepage: https://sourceforge.net/projects/acme-crossass/
- Debian source: https://packages.debian.org/source/sid/acme
