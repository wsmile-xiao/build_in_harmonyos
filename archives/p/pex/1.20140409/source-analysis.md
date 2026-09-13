# Source and Build Analysis

## W0 Dependency Check

- Upstream project: `petere/pex`
- Version: `1.20140409`
- Source archive: GitHub codeload tarball
- SHA-256: `5047946A2F83E00DE4096CD2C3B1546BC07BE431D758F97764A36B32B8F0AE57`
- Package dependencies: none in Conan
- Runtime prerequisites: POSIX shell, `curl`, `git`
- PostgreSQL prerequisites: `pg_config` and `psql` for extension-management commands
- Optional audit prerequisites: Perl, `prove`, and the Perl `YAML` module

The current Windows host does not provide Conan, Perl, `prove`, `make`, or a
POSIX shell on `PATH`. WSL is installed but has no Linux distribution. These
are host validation limitations, not missing Conan library dependencies.

## W1 Source Review

The upstream archive is a small shell project with:

- `pex`: the executable script
- `pex.1`: the manual page
- `Makefile`: install and upstream test entry points
- `t/*.t`: 17 official TAP shell tests
- `pex.spec` and `debian/`: native package metadata

There is no C/C++ compilation, generated code, or platform-specific binary.
The install target copies the script and manual page into a conventional
prefix.

Important runtime behavior:

- `pex init` clones a package metadata repository into the XDG data directory.
- `fetch`, `install`, and related commands use `curl`, `git`, `tar`, and
  PostgreSQL's `pg_config`.
- `audit` additionally uses Perl and YAML.
- The upstream script uses `#!/bin/sh`; the OHOS package copy is changed to
  `#!/system/bin/sh`.

## W2 Adaptation Decisions

The recipe uses Conan's `application` package type and `basic_layout`.
`package_info()` exposes `bin` through `bindirs` and `PATH`. The source archive
is fetched with its verified SHA-256 and no source patch is required.

The official tests are run from `build()` so missing test tools fail visibly
in target CI. On OHOS, `prove --exec /system/bin/sh t/*.t` avoids relying on a
nonexistent `/bin/sh`, and the temporary test copy of `pex` receives the same
shebang adjustment before execution.

## W3/W4 Scope

The consumer test exercises help output, Conan package layout, XDG path
resolution, local package-repository initialization, package search and
display, and invalid-command diagnostics. It does not start PostgreSQL or
download/install an extension, so those flows remain shadow-CI or device
validation work.
