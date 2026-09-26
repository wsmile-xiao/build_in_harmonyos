# netsurf-buildsystem

NetSurf's shared GNU Make build system for downstream libraries such as
libcss, libhubbub, libdom, and libnsbmp. The package contains makefile
fragments and helper scripts rather than compiled libraries.

Consumers use the `NSSHARED` environment variable to locate the installed
`share/netsurf-buildsystem` directory. The Conan recipes preserve that
layout, export `NSSHARED`, and validate the installed fragments with a small
consumer project because upstream's `make test` target has no assertions.

Packaged versions:

- 1.1: the original contest adaptation retained for the corresponding task.
- 1.10: the newer upstream release already present on `main`.
