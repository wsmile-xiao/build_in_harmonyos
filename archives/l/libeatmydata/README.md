# libeatmydata

LibEatMyData is a LD_PRELOAD library that transparently disables fsync(), fdatasync(), sync(), syncfs(), msync() and O_SYNC/O_DSYNC flags. It is primarily used for testing to speed up I/O operations by eliminating disk sync waits.

## Functionality

- Intercepts fsync() → returns 0 immediately (no actual disk sync)
- Intercepts fdatasync() → returns 0 immediately
- Intercepts sync() → no-op
- Intercepts msync() → returns 0 immediately
- Intercepts syncfs() → returns 0 immediately
- Provides `eatmydata` wrapper command to run any command with LD_PRELOAD
- Provides `eatmydata.sh` shell integration script

## OHOS Adaptation

### Key Issues

1. **pthread_testcancel unavailable** — OHOS/musl does not provide `pthread_testcancel()`. All calls to this function are guarded with `#ifdef __OHOS__` to skip them on OHOS.

2. **pthread_cancel unavailable** — The tst-cancel4 test uses `pthread_cancel()` which is not available on musl/OHOS. This test is skipped via `#ifdef __OHOS__` stub.

3. **LD_PRELOAD works** — The LD_PRELOAD mechanism works on OHOS, allowing the library to intercept sync calls as intended. Verified: fsync, fdatasync, msync, syncfs, sync_file_range interception all functional; open() O_SYNC/O_DSYNC flag stripping works correctly.

4. **config.status HMDFS issue** — The autoconf-generated `config.status` fails to create temp directories on HMDFS filesystem. Fixed by bootstrap.sh patching config.status to use $TMPDIR instead of current directory.

### Known Limitations

- tst-key4 test fails (musl PTHREAD_KEYS_MAX=128 vs glibc 1024+, platform limit not library bug)
- tst-cancel4 test cannot be compiled (pthread_cancel unavailable, stubbed via #ifdef __OHOS__)
- test_run.sh wrapper unavailable on OHOS (requires /bin/bash + strace)

### Verified Test Results (2026-06-03)

| Test | Result | Description |
|------|--------|-------------|
| eatmydatatest | ✅ PASS | O_SYNC/O_DSYNC stripping + sync interception |
| eatmydatatest_largefile | ✅ PASS | Large file O_SYNC/O_DSYNC stripping |
| fsynctest | ✅ PASS | fsync/fdatasync/sync/msync interception |
| syncfstest | ✅ PASS | syncfs interception |
| fcntltest | ✅ PASS | fcntl handling |
| tst-invalidfd | ✅ PASS | Invalid fd handling |
| tst-cancel4 | ⏭️ SKIP | pthread_cancel unavailable (OHOS stub) |
| tst-key4 | ❌ FAIL | musl PTHREAD_KEYS_MAX limit (not library defect) |
| eatmydata wrapper | ✅ PASS | LD_PRELOAD wrapper command works |
| open() O_SYNC stripping | ✅ PASS | O_SYNC/O_DSYNC flags correctly stripped |
| msync() interception | ✅ PASS | Returns 0 immediately with LD_PRELOAD |

## Dependencies

- None (standalone library)

## References

- Source: https://github.com/stewartsmith/libeatmydata
- Releases: https://download.savannah.nongnu.org/releases/libeatmydata/