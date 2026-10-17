# libblkid 2.42.2 adaptation notes

## Scope

- Package: libblkid/2.42.2 (block device identification library from util-linux)
- Upstream source: util-linux 2.42.2 tarball (libblkid is a sub-library of the util-linux suite, same tarball as archives/u/util-linux-login/2.42.2)
- Task: #8131 (fdisk → blkid → uuid dependency chain)
- Reference recipes: archives/u/uuid/2.40.1 (libuuid "single sub-library" pattern), archives/u/util-linux-login/2.42.2 (same 2.42.2 tarball + config.guess OHOS patch)

## Adaptation

- Conan Autotools recipe, static library only (shared option rejected in validate).
- Builds only `libblkid` from util-linux 2.42.2: `--disable-all-programs --enable-libblkid --disable-libuuid --disable-libmount --disable-libsmartcols --disable-libfdisk`.
- libblkid has no external library dependencies (links only the internal libcommon) — the recipe has no `requires` (verified: blkid.pc.in has no Requires line).
- util-linux 2.42.2 `config/config.sub` already recognizes `ohos*` / `linux-ohos*-`; `config/config.guess` needed the HarmonyOS detection patch (0001, identical to util-linux-login 2.42.2).

### OHOS specifics

- E011 (configure umask 077 → 0700 temp dirs unwritable on HMDFS): in-recipe sed of `configure` (`umask 077` → `umask 022`), util-linux-login pattern.
- TMPDIR pointed at `<build_folder>/tmp` (writable) — /tmp is read-only on OHOS.
- AWK located explicitly (toolchain bindir first, then `which gawk/awk`) — util-linux configure fails without awk (uuid 2.40.1 pattern).
- host/build triplets derived from Conan settings (uuid 2.40.1 pattern): host=aarch64-unknown-linux-gnu (build machine is also aarch64 HarmonyOS PC).

## Upstream tests

Upstream registers **12 check_PROGRAMS** under `BUILD_LIBBLKID_TESTS` (= build_libblkid && enable_static; see libblkid/src/Makemodule.am):

test_blkid_cache, test_blkid_config, test_blkid_dev, test_blkid_devname, test_blkid_devno, test_blkid_evaluate, test_blkid_read, test_blkid_resolve, test_blkid_save, test_blkid_tag, test_blkid_verify + test_blkid_fuzz_sample (FUZZING_ENGINE's libFuzzer-independent sample target).

### Local run (real run, all 12 programs executed on the HarmonyOS PC build host, aarch64 native)

All 12 check_PROGRAMS built by the recipe (`make test_blkid_*`) and executed natively:

| # | program | how run | result |
|---|---|---|---|
| 1 | test_blkid_cache | `test_blkid_cache /dev/null` (cache round-trip, empty probe) | PASS (exit 0) |
| 2 | test_blkid_config | default config read/dump (EVALUATE/UEVENT/CACHE_FILE) | PASS (exit 0) |
| 3 | test_blkid_dev | `-f /dev/null` empty cache device iteration | PASS (exit 0) |
| 4 | test_blkid_devname | probe_all over empty /dev (no block devices on build host) | PASS (exit 0) |
| 5 | test_blkid_devno | `test_blkid_devno 1 0` devno→name resolution path | PASS (exit 0) |
| 6 | test_blkid_evaluate | negative: `LABEL=x` (no match → EXIT_FAILURE by design, verified); positive: `UUID=<real>` via cache file → resolves to real image path, exit 0 | PASS (both semantics) |
| 7 | test_blkid_read | `test_blkid_read /dev/null` cache file parsing | PASS (exit 0) |
| 8 | test_blkid_resolve | negative: `LABEL=x` (no device → rc 1 by design); positive: `UUID=<real>` → rc 0; `TYPE <devname>` → prints ext2, rc 0 | PASS (both semantics) |
| 9 | test_blkid_save | `test_blkid_save <file>` (load /dev/null cache → probe → flush) | PASS (exit 0) |
| 10 | test_blkid_tag | cache file with real image path: iterate form (TYPE/LABEL/UUID all listed) + search form `(TYPE, ext2) FOUND` | PASS (exit 0) |
| 11 | test_blkid_verify | `test_blkid_verify <ext2.img>` (real upstream superblock image) → TYPE='ext2' LABEL='test-ext2' UUID='22f0eac3-...' | PASS (exit 0) |
| 12 | test_blkid_fuzz_sample | **all 128 upstream images** from tests/ts/blkid/images-fs/ probed OK | PASS (128/128) |

Note: test_blkid_tag/evaluate/resolve need a cache containing a real device path (BLKID_DEV_CREATE checks access(F_OK)); using a cache file that references the real ext2.img path from the upstream test images satisfies this without root.

The full upstream script suite tests/ts/blkid/ (11 cases: cache, dm-err, images-fs, images-pt, low-probe, lowprobe-pt, md-raid0-whole, md-raid1-part, md-raid1-whole, offset, options, output, topology) requires root + real block devices + md-raid + device-mapper and the ts framework (`make check` needs root) — not runnable in the CI/dev container; per-case rationale in the PR body (upstream test case modification notes). Their probe coverage is however exercised through test_blkid_fuzz_sample over the same images-fs corpus (128/128 OK) and test_blkid_verify on real superblocks.

## test_package

CMake-based test (uuid 2.40.1 pattern): checks installed blkid.h + libblkid.a + blkid.pc, then builds and runs test_blkid.c which exercises blkid_get_library_version, blkid_encode_string, blkid_parse_tag_string and a /dev/null cache round-trip — 8 assertions, all offline (no root/block device needed).

## Local Validation

- `python3 -m py_compile` passed for conanfile.py + test_package/conanfile.py.
- `git diff --check` passed (patch-file whitespace warnings are upstream config.guess context lines, required for clean apply — verified with `git apply --check` on the pristine tarball).
- Patch 0001 verified byte-identical in intent to the merged util-linux-login 2.42.2 patch and applies cleanly to the pristine tarball.
- `conan create archives/l/libblkid/2.42.2 -pr:h/-pr:b=ohos-aarch64 --build=missing`: PASS — static lib built, test_package built and ran (8/8 assertions OK: version 2.42.2 (16-Jun-2026), udev-safe encoding sp\x20ace+plus, LABEL=myroot parsing, /dev/null cache round-trip).
- Upstream 12/12 check_PROGRAMS executed natively on this aarch64 HarmonyOS host (see table above); fuzz_sample probed the full upstream images-fs corpus 128/128 OK.
