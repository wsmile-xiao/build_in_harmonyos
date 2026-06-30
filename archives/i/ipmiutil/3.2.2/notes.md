# ipmiutil 3.2.2 Build Notes

## Build Environment
- Platform: HarmonyOS aarch64 (HongMeng Kernel)
- Compiler: clang (OHOS SDK)
- Build system: autotools

## Key Modifications
1. **config.guess**: Added `HarmonyOS` to UNAME_SYSTEM case (line 136); added `aarch64:HarmonyOS:*:*)` pattern
2. **config.sub**: Added `linux-ohos*` to maybe_os; added `ohos-linux` OS case; added `-linux-ohos*` to valid OS list
3. **configure**: Extended OS detection to accept `HarmonyOS` alongside `Linux`; replaced hardcoded `/tmp` paths with `${TMPDIR:-/tmp}`; replaced `mktemp` calls with `mkdir` in TMPDIR for HMDFS compatibility; changed `umask 077` to `umask 022` in generated config.status for HMDFS directory write permission fix

## Build Configuration
- `--prefix=/usr --enable-lanplus=no` (lanplus disabled due to missing OpenSSL headers)
- HMDFS compatibility: TMPDIR=$HOME/tmp, umask 022 for config.status temp dir creation

## Known Issues
- Runtime hardcoded `/tmp` paths in source code (not patched, application-level concern)
- HMDFS: mktemp creates directories with restrictive permissions (umask 077 → drwx--S---) preventing file writes; workaround: use mkdir with umask 022 in TMPDIR
- HMDFS: config.guess creates temp files in $TMPDIR with permission issues (warning only, not fatal)
---

**编译结束**: 2026-06-12 16:19
**最终状态**: published
