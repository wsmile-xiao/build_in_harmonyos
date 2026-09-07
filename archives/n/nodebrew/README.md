# nodebrew

Node.js version manager.

## Description

nodebrew is a lightweight Node.js version manager written in Perl. It allows
you to easily install, switch and manage multiple Node.js versions, including
`iojs` and nightly builds. It is a pure script tool: the whole program is one
self-contained perl script (`bin/nodebrew`), no C/C++ compilation required.

## Homepage

https://github.com/hokaccha/nodebrew

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nodebrew 1.2.0
```

## Usage

Add `PATH` setting to your shell config (the brew root defaults to
`$HOME/.nodebrew`, override with `NODEBREW_ROOT`):

```bash
export PATH=$HOME/.nodebrew/current/bin:$PATH
```

Then manage Node.js versions:

```bash
# Install a Node.js version (from binary)
nodebrew install v18.0.0

# Use a specific version
nodebrew use v18.0.0

# List installed versions
nodebrew ls

# Show version of nodebrew itself
nodebrew version
```

## Available Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 1.2.0 | built | 2026-09-04 |

## Notes

- This is a pure perl script project, no compilation required
- Runtime dependency: perl (interpreter), plus `curl`/network when actually
  installing Node.js versions
- nodebrew keeps its data under `NODEBREW_ROOT` (default `$HOME/.nodebrew`)
