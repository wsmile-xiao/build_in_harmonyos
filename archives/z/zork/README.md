# zork

The Dungeon (Zork I) - classic text adventure game, C implementation.

**Upstream**: https://github.com/devshane/zork  
**License**: MIT

## OHOS Adaptation

- **Build system**: Make (upstream)
- **TEXTFILE injection**: `-DTEXTFILE="<package>/share/zork/dtextc.dat"` via Makefile DATADIR patch
- **TERMFLAG**: `-DMORE_NONE` (no termcap dependency)
- **Dependencies**: none (pure C, no external libraries)
- **Build**: `conan create archives/z/zork/1.1.0 --build="zork/*"`

## Files

- `commands.json` — R38 CLI tool metadata
- `manifest.yaml` — software-level metadata
- `1.1.0/` — version-specific recipe and test files
