# SDL2_ttf

SDL2_ttf is a library that provides support for TrueType fonts in SDL2 applications.

## Dependencies

- SDL2 2.30.0 (required)
- FreeType (bundled)
- HarfBuzz (bundled)

## Available Versions

| Version | Status | Notes |
|---------|--------|-------|
| 2.22.0 | built | Uses bundled FreeType and HarfBuzz |

## Installation

```bash
# Install SDL2 first
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- SDL2 2.30.0

# Build SDL2_ttf
cd ~/builds/SDL2_ttf-2.22.0.work
./configure --prefix=$HOME/usr/local
make -j4
make install
```

## Notes

- Uses bundled FreeType and HarfBuzz (no external dependency needed)
- Requires config.guess/config.sub patches for HarmonyOS support