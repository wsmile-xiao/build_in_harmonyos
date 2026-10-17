# debootstrap

https://salsa.debian.org/installer-team/debootstrap

debootstrap is a tool which will install a base Debian system into a
subdirectory of an already installed system. It doesn't require an
installation CD, just access to a Debian repository. The tool is a collection
of POSIX shell scripts (a main `debootstrap` script, a shared `functions`
library, and one script per Debian suite), so it requires no compilation.

## OHOS Adaptation

- Pure shell: nothing to compile; the only packaging step is substituting the
  `@VERSION@` placeholder (exactly what the upstream Makefile does).
- Data files (`functions`, `scripts/`) are installed under `share/debootstrap`
  and located at runtime through the `DEBOOTSTRAP_DIR` environment variable,
  which the Conan recipe injects automatically.

## Usage

```
debootstrap --version
debootstrap <suite> <target-dir> <mirror>
```

## Installation layout

- `bin/debootstrap` — main script (version number substituted)
- `share/debootstrap/functions` — shared function library
- `share/debootstrap/scripts/*` — per-suite bootstrap scripts
- `share/man/man8/debootstrap.8` — manual page
