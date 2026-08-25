# AT&T Software Technology (AST)

AT&T Software Technology toolkit for HarmonyOS PC.

Includes:
- **ksh** (KornShell 93) — a POSIX-compatible shell
- **shcomp** — shell script compiler
- **libast** — AT&T Software Toolkit library
- **libdll** — dynamic linking library

## Version 2020.0.0

- Source: https://github.com/att/ast (tag 2020.0.0)
- License: EPL-1.0
- Build system: Meson
- Package type: application (CLI tools)
- Dependencies: None (self-contained)

## Installation

```bash
conan install --requires=ast/2020.0.0 -r=ohpcd
```

## Key binaries

| Binary | Description |
|--------|-------------|
| `ksh` | KornShell 93 — POSIX-compatible interactive shell |
| `shcomp` | Shell script compiler |
