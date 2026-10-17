# Aften 0.0.8 adaptation notes

The exact official SourceForge release has no independent upstream test suite.
Its 2007 CMake file detects the build machine with `uname`, which can select
x86 SIMD sources during an aarch64 cross build. The portability patch uses the
CMake target processor while cross compiling and restores the project module
path after the Conan toolchain is loaded. Upstream also omits the static target
from its install list, so the packaging patch installs it with the public
`aften` name. The generic architecture branch lacks the no-op SIMD restriction
hook called by the encoder, so a one-function portability patch supplies it.

The consumer test links to the packaged library, checks the exact version,
rejects an invalid encoder configuration, and encodes a deterministic silent
stereo AC-3 frame. It also executes the packaged CLI version command. Runtime
and invalid-input checks are required on the HarmonyOS PC emulator before
submission.
