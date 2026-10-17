# metamath

Metamath is a command-line proof verifier and proof assistant for the
Metamath language.

## Upstream

- Version: 0.198
- Source: https://github.com/metamath/metamath-exe
- License: GPL-2.0-or-later
- Build: direct C compilation from the official README command

## HarmonyOS adaptation

The upstream v0.198 archive contains the 16 C translation units, headers,
license, README, and man page. It does not contain a database or automated
test suite. The Conan recipe therefore builds the standalone `metamath`
executable with the active Conan C compiler and packages the executable,
man page, and license only.

The consumer test uses an offline six-statement `.mm` database to verify
version output, source parsing, and proof verification. Device execution is
required for the final HarmonyOS PC runtime check because the local Windows
host can only cross-compile the AArch64 OHOS executable.
