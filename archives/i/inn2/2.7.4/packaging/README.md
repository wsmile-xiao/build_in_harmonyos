# packaging — inn 2.7.4

This package is built and consumed as a Conan recipe; no standalone release
tarball is produced.

The recipe installs the three static libraries (`libinn.a`, `libinnhist.a`,
`libinnstorage.a`), the 44 public headers under `include/inn/`, and roughly 80
command line tools under `bin/`. Because it ships executables it is declared
`package_type = "application"` and the software-level `commands.json` marks it
as a `tool` package (R38).
