# Test Report — ex-vi 050325

## Build Environment

| Item | Value |
|------|-------|
| Platform | HarmonyOS PC (arm64) |
| Compiler | clang 15.0.0 |
| Build System | Plain Makefile |
| CFLAGS | -fPIC -O2 |
| Dependencies | None (self-contained: libterm, libuxre, mapmalloc) |

## Build Result

| Target | Status |
|--------|--------|
| make (compile) | ✅ PASS |
| make install (DESTDIR staging) | ✅ PASS |

## Produced Binaries

| Binary | Type | Description |
|--------|------|-------------|
| ex | executable | Main ex/vi editor |
| vi | symlink → ex | vi visual mode entry |
| edit | symlink → ex | edit alias |
| vedit | symlink → ex | vedit alias |
| view | symlink → ex | read-only view |
| exrecover | executable | Crash recovery tool |
| expreserve | executable | Preserve editor state |

## Patches Applied

| # | File | Purpose |
|---|------|---------|
| 0001 | Makefile | OHOS: fix INSTALL path, remove `size ex`, clear STRIP, skip interactive install check, fix symlinks |
| 0002 | ex.c | OHOS: replace sbrk()-based line arena with mmap() (musl sbrk(>0) returns ENOMEM); add --version / --help |
| 0003 | ex_subr.c | OHOS: morelines() uses mmap arena instead of sbrk() |
| 0004 | libterm/Makefile | OHOS: use `override CFLAGS +=` to preserve -D defines |
| 0005 | libuxre/Makefile | OHOS: use `override CFLAGS +=` to preserve -I. and RPMCFLAGS |

## Smoke Tests (L2)

| Test | Command | Expected | Result |
|------|---------|----------|--------|
| Version | `ex --version` | exit 0, print version | ✅ PASS |
| Help | `ex --help` | exit 0, print usage | ✅ PASS |
| Basic edit | `echo "test" \| ex -s -c 'p' -c 'q'` | print "test", exit 0 | ✅ PASS |
| File read | `printf "line1\nline2\n" > /tmp/t.txt && ex -s /tmp/t.txt -c '1,$p' -c 'q'` | print both lines | ✅ PASS |

## Conan Verify (G0-G4, L2/L4/L5)

| Gate | Check | Result |
|------|-------|--------|
| G0 | Pre-build risk assessment | ✅ PASS |
| G1 | Recipe completeness | ✅ PASS |
| G2 | conan create (clean build) | ✅ PASS |
| G3 | System library isolation (R26) | ✅ PASS |
| G4 | Artifact completeness | ✅ PASS |
| L2 | Platform smoke test | ✅ PASS |
| L4 | checksec security scan | ✅ PASS |
| L5 | Artifact baseline comparison | ✅ PASS |

## Known Limitations

- `sbrk()` replaced with `mmap()` for line arena allocation (musl sbrk(>0) returns ENOMEM on OHOS)
- Interactive install check (`echo q | ex`) skipped in Makefile (not suitable for batch/CI)
- PRESERVEDIR set to PREFIX/var/preserve (not /var/preserve) for DESTDIR staging compatibility

## Conclusion

ex-vi 050325 builds and runs successfully on HarmonyOS PC (arm64). All smoke tests pass. Conan recipe verified (G0-G4, L2/L4/L5 all PASS). Ready for publish.
