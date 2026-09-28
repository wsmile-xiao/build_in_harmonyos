# jdupes

jdupes is a fast command-line tool for finding duplicate files. It scans
specified directories, compares file contents safely, and can report matching
sets for further action.

## Package

- **Version:** 1.31.1
- **License:** MIT
- **Upstream:** https://codeberg.org/jbruchon/jdupes
- **Build system:** portable Makefile
- **Runtime dependency:** `libjodycode/4.1.2`
- **Installed executable:** `bin/jdupes`
- **Manual page:** `share/man/man1/jdupes.1`

The package keeps the upstream feature set, including recursive scanning,
JSON output, hash-database support, and link/deduplication actions. The Conan
consumer test checks the installed executable, version output, recursive
duplicate detection, and exclusion of a unique file.

## HarmonyOS notes

The recipe uses the clang toolchain from the Conan profile and serial `make
-j1`. The upstream source has one clang-invalid switch block; the portable
patch adds explicit `break` statements without platform-specific preprocessor
macros. The OHOS image does not provide the GNU `install` utility, so the
recipe uses the Makefile's configurable copy commands during packaging.
