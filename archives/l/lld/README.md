# LLD

LLD is the LLVM project's high-performance linker. This package builds the
LLVM 20 linker drivers for OpenHarmony PC on AArch64.

## Features

- ELF linker exposed as `ld.lld`
- Generic driver exposed as `lld`
- COFF driver exposed as `lld-link`
- Mach-O driver exposed as `ld64.lld`
- WebAssembly driver exposed as `wasm-ld`

## OpenHarmony Adaptation

The recipe builds `lld` from the official `llvm-project` monorepo with only the LLD project and AArch64 code-generation backend enabled. The default target triple is `aarch64-linux-ohos`. The complete upstream `check-lld` entry point remains enabled; tests requiring other LLVM backends are discovered and reported as unsupported.

Optional zlib, zstd, libxml2, libedit, terminfo, and curl integrations are disabled so the recipe has no unpublished Conan dependencies. Command aliases are packaged as regular files because HMDFS symbolic links are unreliable.

LLVM `config.guess` is patched for native AArch64 HarmonyOS, CMake treats HarmonyOS as Unix-compatible, and lit uses a pre-created `$HOME/tmp` directory. Exact OHOS filesystem limitations are marked through `LIT_XFAIL`. The target-neutral ELF reproduction archive is independently validated with Python `tarfile`, and the dead-strip PAGEZERO assertion uses FileCheck to avoid an early-closing pipeline.

The clean OHOS AArch64 W3 build passed Conan packaging, the signed consumer test, and the complete `check-lld` entry point. It discovered 3042 tests: 444 passed, 2597 were unsupported, one expectedly failed, and none failed.

## References

- Project: https://lld.llvm.org/
- Source: https://github.com/llvm/llvm-project
- Release: https://github.com/llvm/llvm-project/releases/tag/llvmorg-20.1.8
