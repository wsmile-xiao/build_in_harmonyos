# libunistring 1.0 handoff

## Identity
- Issue: #1436, https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1436
- AgentID: windrel
- Worktree: `D:\Huawei\worktrees\libunistring`
- Branch: `feat/libunistring-1.0-windrel`

## Scope
- Only `archives/l/libunistring/1.0` is changed in this branch.
- This dependency unblocks `boxes/2.3.1`.

## Validation plan
```powershell
$env:CI_PACKAGES="archives/l/libunistring/1.0"
# Run project single-package shadow CI on device when lock is available.
```

## Current status
- Conan recipe and direct-compile consumer test package prepared.
- Real-device shadow CI passed on 2026-07-25.
- Passing run: `windrel-libunistring-1.0-ci-20260725-191118-40585`.
- Result: `L0_RESULT=pass`, `L1_RESULT=pass`, `L5_RESULT=pass`, build summary `Success: 1, Failed: 0`.

## Upstream test check
- Local upstream source: `https://ftp.gnu.org/gnu/libunistring/libunistring-1.0.tar.xz`, sha256 `5bab55b49f75d77ed26b257997e919b693f29fd4a1bc22e0e6e024c246c72741`.
- Local command: `CFLAGS='-g -O2 -Wno-incompatible-pointer-types' ./configure --disable-shared --enable-static --disable-rpath --disable-dependency-tracking && make -j4 && make check`.
- Local environment: MSYS2 MinGW64, GCC 14.2.0, GNU Make 4.4.1, GNU diffutils 3.12, run date 2026-07-26.
- Result: `TOTAL=580`, `PASS=525`, `SKIP=30`, `FAIL=25`, `ERROR=0`; pass rate is `525/550 = 95.45%` excluding skips (`525/580 = 90.52%` overall).
- Non-100% reason: failures are local Windows/MSYS environment differences, mainly missing POSIX locale/codepage coverage, chmod/tempdir permission semantics, POSIX `stat`/`lstat`/`ftruncate`/`select`/signal/thread behavior differences, and related runtime crashes in gnulib platform tests. These are not introduced by the OHOS Conan recipe; the OHOS smoke test and real-device shadow CI remain passing.
