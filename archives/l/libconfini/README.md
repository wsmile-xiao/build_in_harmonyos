# libconfini

**Yet another INI parser** — a C99 library for parsing INI/.conf files.

libconfini focuses on standardization and parsing exactness. Rather than storing
the parsed data, it dispatches each parsed node (section / key / value / comment)
to a user-supplied callback, formatted according to a configurable `IniFormat`.

- Upstream: https://github.com/madmurphy/libconfini
- License: GPL-3.0-or-later
- Dependencies: none (pure C99, only C standard headers)
- Build system: GNU autotools

## Installed artifacts

- `lib/libconfini.so*`, `lib/libconfini.a`
- `include/confini.h`
- `lib/pkgconfig/libconfini.pc` (pkg-config name: `libconfini`)

## Versions

| Version | Status |
|---------|--------|
| 1.16.4  | built  |
