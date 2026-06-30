# libdiscid

Libdiscid is a C library for creating MusicBrainz DiscIDs from audio CDs.
It reads the TOC (Table of Contents) of a CD and can calculate a DiscID
used by the MusicBrainz project for identifying CDs.

Additionally, the library can extract MCN/EAN/UPC and ISRCs from a disc.

## Available Versions

| Version | Status | Build System | Notes |
|---------|--------|--------------|-------|
| 0.6.5-r0 | published | cmake | HarmonyOS generic platform (no disc reading) |

## Description

libdiscid provides:
- MusicBrainz DiscID calculation from CD TOC
- FreeDB DiscID calculation
- MCN/EAN/UPC extraction from disc
- ISRC extraction per track
- pkg-config interface for easy integration

On HarmonyOS (generic platform), disc reading is not available, but
DiscID calculation via `discid_put()` and library functions are fully functional.

## Functional Test Results (2026-06-02)

| Test Group | Items | Result | Key Finding |
|------------|-------|--------|-------------|
| Object lifecycle | 5 | PASS | discid_new/free safe, NULL safe |
| Version & features | 7 | PASS | v0.6.5, generic has no disc reading |
| Default device | 1 | PASS | Returns /dev/null |
| discid_put (DiscID calc) | 16 | PASS | All core API functions work |
| discid_read | 3 | PASS | Expected failure (no disc reading) |
| pkg-config integration | 3 | PASS | Compile/link/run all successful |
| Concurrent objects | 3 | PASS | Same TOC → same ID (deterministic) |
| Edge cases | 2 | PASS | 10-track put, empty query safe |
| **Total** | **40** | **PASS** | **All functional tests passed** |

Full report: `0.6.5-r0/reports/functional-test-report.md`

## Repository Readiness

| Requirement | Status |
|-------------|--------|
| published status | ✅ |
| Quality gates G0-G4 | ✅ PASS |
| Pre-built package | ✅ 99KB tar.gz + debug |
| ELF signature (.note.ohos.ident) | ✅ |
| pkg-config integration | ✅ |
| Functional test (40/40) | ✅ PASS |
| Minimal runtime deps (libc.so only) | ✅ |
| **Overall** | **🟢 Ready for repository** |