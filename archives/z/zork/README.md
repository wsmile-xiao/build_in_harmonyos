# zork

Dungeon adventure game modified from FORTRAN to C. This is the classic Infocom Zork text adventure, ported from the original FORTRAN Dungeon source code to C.

## Categories
- Utility / Games

## Links
- Homepage: https://github.com/devshane/zork
- Source: https://github.com/devshane/zork/archive/refs/tags/v1.0.3.tar.gz

## License
LicenseRef-Homebrew-public-domain

## Build System
- Plain Makefile (no autotools/configure)

## Dependencies
- None (standalone C project)

## Notes
- Uses MORE_NONE (-DMORE_NONE) on OpenHarmony to avoid termcap dependency
- void main → int main fix required for modern C compilers
- dtextc.dat game data file is included in the source tarball
