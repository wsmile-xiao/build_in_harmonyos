# ALSA library

ALSA lib provides the public `libasound` API, configuration engine, PCM and
control plug-ins, UCM support, and the optional `libatopology` API.

## Versions

- `1.2.12`: historical non-Conan archive.
- `1.2.16.1`: local dependency adaptation in progress for the OpenJ9 and
  GraalVM task dependency closure.
- `1.2.16`: local Conan adaptation (Autotools, shared/static, upstream
  `make check` + 11 independent consumer entries verified on OHOS).

The 1.2.16.1 work uses the official ALSA release archive. It has no required
third-party Conan dependency; libc/POSIX, math, dynamic loading, threading, and
clock support are target-system capabilities.

The package also retains upstream `aserver`; its command metadata is declared
at software level in `commands.json`.

## Upstream

- Project: https://www.alsa-project.org/
- Source: https://www.alsa-project.org/files/pub/lib/
- License: LGPL-2.1-or-later
