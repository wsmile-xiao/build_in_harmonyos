# macifrename 0.1.2 adaptation notes

`macifrename` is a small C command-line tool for stable NIC renaming based on
MAC addresses. The upstream release uses a plain Makefile and produces one
executable, `macifrename`.

The canonical release archive is the sourcehut tag archive. The local
environment receives an anti-bot response for that archive URL, so the recipe
falls back to Alpine's distfile cache for the same `macifrename-0.1.2.tar.gz`.
The SHA-256 in `conandata.yml` is computed from that tarball, and the SHA-512
matches Alpine's APKBUILD entry for the sourcehut archive.

The upstream Makefile sets warning and language flags directly. The recipe
passes `CFLAGS` on the make command line to preserve upstream
`-Werror -Wall -Wextra -pedantic -std=gnu99` while adding Conan
`build_type` flags so Release and Debug builds are distinguishable.
For OHOS, the recipe replaces `<linux/if.h>` with `<net/if.h>` and adds
`-D_GNU_SOURCE`; this avoids a duplicate `sockaddr_storage` definition while
keeping `struct ifreq` visible through the C library header.

The upstream release does not provide a test target. The added consumer test
verifies the packaged executable, checks the documented `-h` usage path, and
exercises a missing configuration file failure without attempting to rename
network interfaces.

COMPLETED
