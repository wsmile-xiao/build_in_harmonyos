# Test Report: jpdfbookmarks 2.5.4

## Build Information
- **Software**: jpdfbookmarks
- **Version**: 2.5.4
- **Build System**: Java (pre-compiled binary distribution)
- **Platform**: HarmonyOS (OpenHarmony, musl libc, aarch64)
- **Date**: 2026-05-29

## Build Type
jpdfbookmarks is a pre-compiled Java binary distribution. No compilation was needed.
The release tarball contains pre-built jar files, launcher scripts, and dependencies.

## Installation
- Files installed to `/usr/local/bin/` (launcher scripts)
- Application data in `/usr/local/lib/jpdfbookmarks/`
- Documentation in `/usr/local/share/jpdfbookmarks/`

## Modifications
- Modified `jpdfbookmarks` launcher script to support installed layout (APP_DIR detection)
- Modified `jpdfbookmarks_cli` launcher script with same changes
- Key change: scripts now detect whether running from source directory or installed location

## G1: Binary Integrity ✅
- `jpdfbookmarks` launcher script: executable ✅
- `jpdfbookmarks_cli` launcher script: executable ✅

## G2: Functionality ✅
- `jpdfbookmarks_cli --version` → 2.5.4 ✅
- `jpdfbookmarks_cli --help` → shows usage ✅
- Requires JAVA_HOME or java in PATH to run

## G3: File Structure ✅
- Main jar: `jpdfbookmarks.jar` ✅
- Config: `conf/jpdfbookmarks.logging.properties` ✅
- CJK font config: `conf/jpdfbookmarks.cjk.font.properties` ✅
- Locales: multi-language support ✅
- 17 dependency jars ✅

## G4: Portability ✅
- Shell scripts use relative paths (SCRIPT_DIR/../lib/jpdfbookmarks)
- No hardcoded absolute paths (except /usr/local fallback which doesn't exist)
- Works with JAVA_HOME environment variable

## Notes
- This is a Java application requiring JDK/JRE 16+
- BiSheng JDK 17.0.13 is available on this platform
- Java requires proper library setup (libz.so) - works in clean environment
- The application includes CJK (Chinese/Japanese/Korean) font support
- Windows .exe files are not needed on HarmonyOS
