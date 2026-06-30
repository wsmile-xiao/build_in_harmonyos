# Simon Tatham's Portable Puzzle Collection

Simon Tatham's puzzle collection contains about 40 small computer programs
which implement one-player puzzle games. All run natively on Unix (GTK) and
Windows, with web-based versions available as JavaScript applets.

## OpenHarmony Build Notes

This is a **headless/CLI build** for OpenHarmony. Since GTK is not available
on HarmonyOS, the puzzle game binaries use a minimal frontend (ohos_fe.c) that:

- Supports `--version` flag (outputs "Version YYYYMMDD.COMMITHASH")
- Supports `--help` flag
- Provides stub implementations for all drawing functions (via drawing_api vtable)
- Does NOT support interactive gameplay (requires GUI frontend like GTK)

### Available Programs
40 puzzle game binaries + solver programs + fuzzpuzz testing tool.

### Build Configuration
- Build system: CMake with custom `PUZZLES_PLATFORM=ohos` option
- Platform file: `cmake/platforms/ohos.cmake` (disables GUI, uses ohos_fe.c)
- Frontend: `ohos_fe.c` (minimal headless frontend with vtable-based drawing_api)
