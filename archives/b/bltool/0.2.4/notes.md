# bltool 0.2.4 Adaptation Notes

## Build Environment
- **System**: OpenHarmony (OHOS)
- **Build System**: Custom (Haskell/Cabal)
- **Compiler**: N/A (no Haskell runtime on OHOS)
- **Target**: CLI executable (package_type = "application")

## Build Steps
1. Download source tarball from GitHub release v0.2.4
2. Extract to source folder (strip_root=True)
3. Build: **placeholder** — Haskell/Cabal toolchain not available on OHOS
4. Package: copy all `.hs` source files to `package_folder/src` as documentation

## Problems Encountered
- Haskell/Cabal is not available for the OHOS toolchain; no binary can be produced.
- `build()` is a no-op; only source files are packaged.
- `package_info()` does not declare `bindirs` since no binaries are produced.

## Knowledge Gained
- bltool requires a Haskell runtime (GHC/Cabal) which is unsupported on OHOS.
- The adaptation is marked `status: failed` to truthfully reflect that no build can occur on OHOS.
- `commands.json` marks `binary: false` since no binary artifact exists.
- test_package verifies packaged Haskell sources instead of a nonexistent binary.
- Future work would require a Haskell cross-compiler for OHOS or a native port.
