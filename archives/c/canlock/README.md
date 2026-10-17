# canlock

canlock is a standalone C implementation of the RFC 8315 Netnews Cancel-Lock authentication scheme.

## Features

- Generates and verifies Cancel-Key and Cancel-Lock values with SHA-1 through SHA-512.
- Supports verification across multiple key and lock values.
- Provides complete-message and Cancel-Key/Cancel-Lock field parsers.
- Installs the `canlock`, `canlock-mhp`, and `canlock-hfp` command-line tools.

## HarmonyOS adaptation

The recipe supports native armv8 and x86_64 HarmonyOS PC builds with Clang and the platform POSIX interfaces. No platform macro is injected. Portability patches add `linux-ohos` triplet recognition and make the header-parser helpers discoverable through the Conan runtime `PATH`, avoiding absolute paths from the build machine. Local verification covered complete Linux Conan builds plus shared and static OHOS x86_64 Conan cross-builds whose consumer programs and CLI tools executed on an OpenHarmony 6.0 PC virtual machine; native aarch64 OHOS CI remains the publication gate.

## Dependencies

- Runtime: none.
- Build only: Bison and Flex for the header parsers.

## References

- Homepage: https://micha.freeshell.org/libcanlock/
- Official source: https://micha.freeshell.org/libcanlock/src/info.html
- Standard: https://www.rfc-editor.org/rfc/rfc8315.html
