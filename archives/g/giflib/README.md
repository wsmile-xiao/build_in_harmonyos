# giflib

## Overview

giflib is a C library for reading and writing GIF images. The Conan packages
export `gif_lib.h`, the selected shared or static library, and the MIT license.
Upstream command-line tools are built for regression testing but are not
published as package commands.

## HarmonyOS adaptation

- Drive the upstream Makefile with the compiler and archiver selected by
  Conan; no generated configure files are modified.
- Invoke upstream helper scripts through the selected POSIX shell, replace a
  GNU-only truncation command, and keep regression temporary files under
  `TMPDIR`.
- Sign target utilities, the shared library, and the installed consumer before
  executing them on HarmonyOS.
- Support both shared and static packaging. Shared mode stores three real,
  byte-identical library files and preserves SONAME `libgif.so.7` without
  relying on HMDFS symlinks.

## Dependencies

giflib has no third-party Conan dependency.

## Versions

### 5.2.2

```bash
conan create archives/g/giflib/5.2.2 -o 'giflib/*:shared=True'
conan create archives/g/giflib/5.2.2 -o 'giflib/*:shared=False'
```

### 6.1.3

```bash
conan create archives/g/giflib/6.1.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -o 'giflib/*:shared=True' --build='giflib/*'
```

The HarmonyOS suite contains 51 upstream regression entries and three
installed public-API consumers. Shared/static reruns are not double-counted.
The 6.1.3 adaptation carries the `draft: true` E242 knowledge pair for
testing distinct error channels in stateful C APIs.

## References

- https://sourceforge.net/projects/giflib/
