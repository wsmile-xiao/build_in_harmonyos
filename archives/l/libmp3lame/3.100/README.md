# libmp3lame 3.100

LAME MP3 encoder library, adapted for HarmonyOS (OHOS) aarch64 platform.

## Build System
- autotools (configure + make)
- No external library dependencies

## Patches
1. `0001-config.guess.patch` — Add HarmonyOS detection to bundled config.guess
2. `0002-config.sub.patch` — Accept linux-ohos* host triples in bundled config.sub
3. `replace_in_file` in `build()` — Fix umask 077→022 (setgid hmdfs issue)

## Build Status
- ✅ conan-verify passed (G1/G2/G3/G4)
- ✅ W3 local CI simulation passed
- ✅ W2 PR atomicity check passed
