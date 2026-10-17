# Hermes

Hermes is a JavaScript engine optimized for fast start-up and performance on React Native.

- Homepage: https://github.com/facebook/hermes
- License: MIT

## OpenHarmony Build Notes

- Source: tag `hermes-v260318099.0.1` (CMake VERSION 1.0.0)
- Build system: CMake
- Uses `HERMES_UNICODE_LITE=ON` to skip ICU dependency (same as Android/Emscripten)
- Patches: OHOS platform detection in LLVM host triple + LLVM_ON_UNIX
- Boost.Context: forced arm64/aapcs (CMAKE_SYSTEM_PROCESSOR empty on OHOS)
- Output: hermes, hermesc, hdb, hbcdump, hvm, hcdp binaries + JSI headers
