# csh

csh is the Berkeley C shell command interpreter, providing C-shell syntax, job control, history, aliases, and interactive command execution.

## Features

- C-shell scripting and interactive command interpretation
- Job control, command history, aliases, redirection, pipelines, and globbing
- Standalone `csh` executable with its upstream manual page

## HarmonyOS adaptation

The upstream source uses BSD make and several OpenBSD libc interfaces that are not exposed by the HarmonyOS SDK. The version recipe therefore generates the upstream `error.h` and `const.h` headers portably, compiles the original C sources with clang, and supplies only the missing libc helpers in a package-local compatibility layer. The OHOS artifact is statically linked and signed; the terminal status command is unavailable when `TIOCSTAT` is not provided by the target headers.

## Dependencies

There are no declared Conan build or runtime dependencies. The package provides the `csh` command under `bin/` and its manual page under `share/man/man1/`.

## References

- Upstream source: <https://www.openbsd.org/cgi-bin/cvsweb/src/bin/csh/>
- Source archive: <https://deb.debian.org/debian/pool/main/c/csh/csh_20240808.orig.tar.xz>
