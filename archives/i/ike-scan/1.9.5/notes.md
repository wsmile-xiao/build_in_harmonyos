# ike-scan 1.9.5 OpenHarmony PC adaptation notes

## Summary

`ike-scan` is a C command-line utility for discovering and fingerprinting IKE hosts. The upstream tag archive does not include generated Autotools files, but the actual build products are two small programs: `ike-scan` and `psk-crack`.

The recipe compiles the upstream C sources directly instead of committing Autotools generated output. It writes the minimal `config.h` values required by the source code, sets the package data directory for runtime dictionaries, and packages the upstream data files and man pages.

## Build and test

- Build system: direct C compilation via the Conan-provided C compiler
- Upstream source: `https://github.com/royhills/ike-scan/archive/refs/tags/1.9.5.tar.gz`
- SHA256: `5152bf06ac82d0cadffb93a010ffb6bca7efd35ea169ca7539cf2860ce2b263f`
- Upstream checks executed when runnable: `check-sizes` and `check-hash`
- Conan smoke test: `ike-scan --version` and `psk-crack --help`

## OpenHarmony notes

OpenSSL acceleration remains disabled; the bundled MD5/SHA1 implementation is compiled to keep the package dependency-free. The package installs `ike-backoff-patterns`, `ike-vendor-ids`, and `psk-crack-dictionary` under the package share directory. The installed command launchers resolve the package `bin` directory before executing the real binaries, so the upstream `../share/ike-scan` data lookup remains tied to the installed package layout instead of the caller's working directory.

The previous branch revision included a full `files/autotools-generated/` tree to avoid missing `aclocal` in CI. That made the PR unusually large. Direct compilation keeps the real adaptation files while removing generated build-system output.
