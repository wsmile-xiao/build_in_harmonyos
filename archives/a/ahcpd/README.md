# ahcpd

ahcpd is a daemon for configuring IPv6 mesh networks with the Ad-Hoc
Configuration Protocol (AHCP). It is distributed by Juliusz Chroboczek and
uses a small plain Makefile build.

## Version

| Version | Status | Build date | Patches |
| --- | --- | --- | --- |
| 0.53 | built | 2026-08-06 | 0 |

## Build Notes

- Source: https://www.irif.fr/~jch/software/files/ahcpd-0.53.tar.gz
- Upstream repository: https://github.com/jech/ahcpd
- Build system: Makefile
- Runtime artifacts: `usr/local/bin/ahcpd`, `etc/ahcp/ahcp-config.sh`, `usr/local/man/man8/ahcpd.8`
- Third-party Conan dependencies: none

The recipe builds with the compiler from the Conan profile and installs through
the upstream `TARGET` + `PREFIX` variables. No source patches are required.
