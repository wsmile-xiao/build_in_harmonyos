# ell 0.71 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device (B 机), musl sysroot
- Clang 15.0.4 (ohos-sdk_26.0.0.18)
- Conan 2.29.1
- Profile: `ci/conan/profiles/ohos-aarch64`
- Source: `https://kernel.org/pub/linux/libs/ell/ell-0.71.tar.xz`
  (`574408` bytes, `sha256=850f79cc993791f00232fd31cbaf3e8212edcef25ca0515f98c6d48dfb5952d7`)

## Verification

- `conan-verify ell 0.71`: exit 0 — G0/G1/G2/G3/G4 + L2/L4/L5 all PASS
- `finish` W3 local CI simulation: **PASS** — `.ci-result.json` `exit_code=0`,
  `timestamp=2026-10-06T04:14:10.158425`, `integrity_hash=5c502248e4524f32` (independently recomputed as
  `sha256("2026-10-06T04:14:10.158425:ell:0.71:0")[:16]` → identical), `log_sha256=9c13e72c25a35e2c57bdf5d913cb65e674a11c078a2594084b0da1a20bbc6e08`
  (recomputed over `reports/w3-local-ci.log` → identical)
- `junk_check.sh` with `JUNK_PR_DIFF` (prdiff mode, 44 files): `JC_RESULT=pass`,
  `Junk Files: 0`, `涉及软件数: 1（合规）`
- Staging install (`make install DESTDIR=...`): exit 0 — 54 files installed
  (`libell.so.0.0.2` 543296 B + symlinks, `ell.pc`, 51 public headers,
  **0 executables** ⇒ pure library, no `commands.json` required per R38/PF8)

## Upstream tests (§12.72 four-category static count, measured 2026-10-06)

| Category | Count |
|---|---|
| ① `test*/` framework sources (`unit/test-*.c`) | 46 |
| ② `*/res` corpora | 0 |
| ③ `**/*RUNTEST*` scripts | 0 |
| ④ `examples/*.c` demos | 10 |
| **Four-category strict subtotal** | **56** |
| + `unit/` data files (`dbus.conf`, `gencerts.cnf`, `plaintext.txt`, `settings.test`) | 4 |
| **Reported (conservative, round-high)** | **60** |

Assertions in `unit/test-*.c`: **2355** (`grep -c 'assert('`).

automake registers `TESTS = 46` (`unit_tests` 33 + `dbus_tests` 10 + `cert_tests` 3).

## Adapted result (executable-assertion count)

```
$ make -j1 check
# TOTAL: 46
# PASS:  39
# FAIL:  7
# SKIP:  0
```

- Test cases: 46 executed
- Passed: 39
- Failed: 7
- Skipped: 0

### Failure attribution (all environment / platform limits, none introduced by this adaptation)

| Test | Cause |
|---|---|
| `test-dir-watch` | `/tmp` is read-only erofs (`mkdir /tmp/x` → `Read-only file system`); the test hard-codes `DIR_1="/tmp/ell-test-dir-1"` so the inotify event never arrives (blocked in `EVENTPOLL`, terminated per SKILL "超时可 Ctrl+C 跳过并记录原因") |
| `test-path` | same `/tmp` read-only root cause; `mkstemp` on `/tmp/foobarXXXXXX.tmp` fails → `Assertion failed: fd > 0` |
| `test-dbus` | no DBus runtime: all three sockets (`/run/dbus`, `/var/run/dbus`, `/dev/socket/dbus`) MISSING, `dbus-daemon` NOT FOUND (W0 measured) |
| `test-dbus-message-fds` | same, no DBus runtime |
| `test-dbus-properties` | same, no DBus runtime |
| `test-pem` | `Signal 31 (SIGSYS)`, `exit 159` — syscall blocked by seccomp (**hit E051/E246**) |
| `test-key` | `Signal 31 (SIGSYS)`, `exit 159` — `syscall(__NR_keyctl, KEYCTL_DH_COMPUTE, ...)` blocked by seccomp (**hit E051/E246**) |

> `test-tls` reports `Needed checksum missing, skipping...` then **PASS** (upstream's own
> conditional skip, counted as PASS by automake).
>
> **AF_ALG note**: `socket(PF_ALG, ...)` succeeds but `bind()` is denied with
> `Permission denied` for `hash/sha256`, `hash/sha1`, `hash/md5`, `skcipher/ecb(aes)`,
> `aead/gcm(aes)` (5/5). ell's checksum backend is AF_ALG, so `l_checksum_new()`
> returns NULL and `unit/test-checksum.log` only contains `TEST: unsupported` — its
> automake PASS is a silent skip, not real coverage. The consumer test therefore uses
> base64 / `l_strdup_printf` only, and was verified in both directions (correct vector
> → exit 0; corrupted expected value → exit 1).

## test_package

The consumer test links `libell` and really calls `l_base64_encode()`,
`l_base64_decode()` (round trip) and `l_strdup_printf()`, asserting byte-exact
results against known vectors.

- Test cases: 3 assertions (encode, round-trip decode, formatted string)
- Passed: 3
- Failed: 0

Negative control (expected value deliberately corrupted) exits 1 with
`FAIL: base64 mismatch`, proving the test is not a pass-only shell (R34/PF3).

## Report currency

`test-report.md` is regenerated **after** `finish`/W3 completed, so its mtime is later
than `conanfile.py`, `conandata.yml` and `manifest.yaml`; the `integrity_hash` above is
read from the `.ci-result.json` produced by that same W3 run (not typed by hand).

## Result

The recipe was verified on an OpenHarmony aarch64 device (conan create from clean
source with all 31 patches applied, plus the consumer test) and is eligible for
`built` status.
