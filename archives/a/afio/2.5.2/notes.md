# afio 2.5.2 adaptation notes

The upstream build is a plain Makefile that compiles four C sources. Its
Makefile hard-codes `gcc`, so the Conan recipe invokes the toolchain compiler
directly while preserving the upstream portability definitions and 64-bit file
support.

The exact tag provides two regression programs: `regtest` and `regtest2gb`.
Both must pass on Linux for Path A; the second uses sparse-file support while
checking offsets above 2 GiB. The consumer test separately creates and extracts
a deterministic archive and verifies rejection of corrupt input.

Upstream uses a project-specific historical license combined with LGPL-covered
code. The full notices from `afio.c` and `afio_license_issues_v5.txt` are shipped
inside the package.
