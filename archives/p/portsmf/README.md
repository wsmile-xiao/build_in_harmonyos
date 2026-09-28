# PortSMF

PortSMF is a cross-platform C++ library for reading, writing and editing Standard MIDI Files and Allegro text music sequences.

## Features

- Standard MIDI File input and output
- Multi-track note and control-event data structures
- Tempo maps and time-signature conversion
- Allegro text-format input and output
- Sequence editing and binary serialization

## HarmonyOS adaptation

The `0.1-svn20101010` snapshot builds as an AArch64 shared or static library with the HarmonyOS SDK clang toolchain. The recipe uses a minimal CMake build description because the historical source archive contains CRLF Autotools helper scripts that are not portable to the HarmonyOS shell. Library sources remain unpatched; one test-fixture correction is applied as described below.

All 33 upstream test functions are compiled and executed individually. A one-line fix, later made upstream, initializes the intended fixture duration so the cut/copy/paste tests execute instead of dereferencing a null result. The Conan consumer suite adds API, MIDI round-trip, serialization and HarmonyOS PC AArch64 ABI coverage.

## Dependencies

PortSMF has no third-party dependencies. It uses only the C++ standard library.

## References

- [Upstream repository](https://github.com/rbdannenberg/portsmf)
- [PortMedia project](https://sourceforge.net/projects/portmedia/)
