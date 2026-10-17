# Test Report — ncftp 3.3.0-r0

## Build Test
- configure: PASS (detected HarmonyOS, clang, ncursesw)
- make: PASS (all 7 binaries compiled)
- make install: PASS (with HMDFS hard link fix for ncftpspooler)

## Smoke Test
- ncftp --version: PASS (outputs "NcFTP 3.3.0-r0")
- ncftpget: installed
- ncftpput: installed
- ncftpls: installed
- ncftpbatch: installed
- ncftpbookmarks: installed (with ncurses support)
- ncftpspooler: installed (copy of ncftpbatch)

## Conan Verification
- G1 (recipe completeness): PASS
- G2 (conan create): PASS
- G3 (system lib isolation): PASS
- G4 (artifact completeness): PASS
- L2 (smoke test): PASS
- L4 (security scan): PASS
- L5 (artifact baseline): PASS
- W3 (local CI simulation): PASS
