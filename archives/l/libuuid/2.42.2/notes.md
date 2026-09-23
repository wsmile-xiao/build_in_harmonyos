# libuuid 2.42.2 adaptation notes

## Scope

- Package: libuuid/2.42.2 (universally unique identifier library from util-linux)
- Upstream source: util-linux 2.42.2 tarball (libuuid is a sub-library of the util-linux suite, same tarball as archives/l/libblkid/2.42.2 and archives/u/util-linux-login/2.42.2)
- Task: #13727 (fdisk → blkid → uuid dependency chain, version aligned with libblkid 2.42.2)
- Reference recipes: archives/l/libuuid/2.40.4 (previous version of the same software, junshi_liu), archives/l/libblkid/2.42.2 (same 2.42.2 tarball + config.guess OHOS patch + E011 in-recipe sed), archives/u/util-linux-login/2.42.2

## Adaptation

- Conan Autotools recipe, static library only (shared option rejected in validate).
- Builds only `libuuid` from util-linux 2.42.2: `--disable-all-programs --enable-libuuid --disable-libblkid --disable-libmount --disable-libsmartcols --disable-libfdisk`.
- libuuid has no external library dependencies (uuid.pc.in has no Requires line) — the recipe has no `requires`.
- Version 2.42.2 keeps the util-linux chain on one version (libblkid 2.42.2 #10920 in review, libfdisk #13690 queued by j669539).

### OHOS specifics

- config/config.guess HarmonyOS detection patch 0001 (identical to the one merged with util-linux-login 2.42.2 and libblkid 2.42.2; config.sub already knows ohos* upstream).
- E011 (configure umask 077 → 0700 temp dirs unwritable on HMDFS): in-recipe sed of `configure` (`umask 077` → `umask 022`), libblkid 2.42.2 pattern. This supersedes the 2.40.4 approach (patching configure's ac_tmp to TMPDIR): the sed keeps the pristine configure flow, and TMPDIR is additionally pointed at `<build_folder>/tmp` via the build environment (both belts).
- AWK located explicitly (toolchain bindir first, then `which gawk/awk`) — util-linux configure fails without awk (2.40.4 pattern).
- host/build triplets derived from Conan settings: host=aarch64-unknown-linux-gnu (build machine is also aarch64 HarmonyOS PC).

## Upstream tests

Upstream registers the libuuid-related test programs as check_PROGRAMS:

1. `test_uuid_parser` (libuuid/src/Makemodule.am, libuuid/src/test_uuid.c) — 14 uuid_parse assertions: 5 valid + 9 invalid UUID strings (uppercase, trailing char, wrong separators, all-zero, boundary patterns).
2. `test_uuid_namespace` (tests/helpers/Makemodule.am, tests/helpers/test_uuid_namespace.c) — 7 uuid_get_template calls: dns/url/oid/x500 RFC 4122 namespace templates + NULL/""/unknown (all must return the documented UUID or NULL); output compared against tests/expected/uuid/namespace.
3. `test_uuid_time` (libuuid/src/Makemodule.am, gen_uuid.c compiled with -DTEST_PROGRAM) — prints time fields of a generated v1 UUID; validates the v1 generation path.

The ts script suite tests/ts/uuid/{uuid_parser,namespace} wraps exactly these three helpers (uuid_parser runs $TS_HELPER_UUID_PARSER, namespace runs $TS_HELPER_UUID_NAMESPACE) — running the helpers directly is the same coverage without the ts framework's root/dependency requirements. Other ts tests under uuidgen/uuidparse/uuidd test the uuidgen/uuidparse/uuidd *programs* which are not built in single-library mode (--disable-all-programs).

### Local run (real run, executed natively on the HarmonyOS PC build host, aarch64)

All three check_PROGRAMS built by the recipe (`make test_uuid_parser test_uuid_time test_uuid_namespace`) and executed natively:

| # | program | how run | result |
|---|---------|---------|--------|
| 1 | test_uuid_parser | direct run (14 assertions, exit code checked) | PASS (0 failures, 14/14 lines "OK") |
| 2 | test_uuid_namespace | direct run, output diffed against tests/expected/uuid/namespace | PASS (7/7 template lines byte-identical) |
| 3 | test_uuid_time | direct run (v1 UUID generation + time extraction, exit 0) | PASS |

## test_package

CMake CONFIG-mode consumer test (libblkid 2.42.2 pattern): verifies installed uuid.h + libuuid.a + uuid.pc layout, then builds and runs test_uuid_pkg.c — 19 assertions covering generate/parse/compare/is_null/clear, type+variant nibbles of v4/v1/v3/v5 UUIDs, namespace templates (dns RFC 4122 value, unknown/NULL), uuid_time sanity (within last year) and md5/sha1 namespace generation. All offline (no root, no uuidd daemon, no block devices).

## Local Validation

- `python3 -m py_compile` passed for conanfile.py + test_package/conanfile.py.
- Patch 0001 verified with `git apply --check` on the pristine util-linux-2.42.2 tarball (byte-identical to the libblkid 2.42.2 / util-linux-login 2.42.2 merged patch).
- `conan create archives/l/libuuid/2.42.2 -pr:h/-pr:b=ohos-aarch64 --build=missing`: PASS — static lib built, three upstream test programs ran natively, test_package built and ran (19/19 assertions OK).

## 依赖版本

无外部依赖（uuid.pc.in 无 Requires 行——与 2.40.4 同样零依赖）。
