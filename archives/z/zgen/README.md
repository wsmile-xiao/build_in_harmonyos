# zgen

zgen is a lightweight Zsh plugin manager inspired by Antigen. It keeps shell startup fast by
generating a static `init.zsh` that merely sources the configured plugins and appends them to
`fpath`; the init file is refreshed manually with `zgen reset` / `zgen save`.

The project is pure Zsh — a sourced script (`zgen.zsh`) plus a `_zgen` completion function.

## Requirements

- zsh (interpreter, provided by the host)
- git — only for the networked subcommands (`zgen load`, `zgen update`, `zgen selfupdate`, ...)

## Installation

Source the installed script from `.zshrc`:

```zsh
source $HOME/usr/local/share/zgen/zgen.zsh

zgen load zsh-users/zsh-syntax-highlighting
zgen save
```

The package also installs `share/zsh/site-functions/_zgen`, so `zgen` subcommand completion
becomes available once `compinit` has run.

## OpenHarmony adaptation

`zgen.zsh` shipped a `#!/bin/zsh` shebang. OpenHarmony has no `/bin/zsh`, so the recipe applies
`patches/0001-zgen.zsh.patch` to use `#!/usr/bin/env zsh`. No other change is needed:
the payload is interpreted, architecture independent Zsh code.

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0-20150919 | built | 2026-09-21 | 2015-09-19 snapshot (upstream commit `6ac1bf1b`); upstream has no release tags |

## Upstream

- Homepage: https://github.com/tarjoilija/zgen
- License: MIT
