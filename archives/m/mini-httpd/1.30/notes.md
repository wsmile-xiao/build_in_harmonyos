# mini-httpd/1.30 adaptation notes (GLM-67, 2026-09-21)

- Platform task: 13916 (activity 6, dependency activity); registry row
  `mini-httpd-1.30` -> GLM-67.
- Branch: `feat/mini-httpd-1.30`; worktree `~/qzy/GLM-67-mini-httpd-1.30`
  (base 42a8cc8fd8).
- Upstream: https://www.acme.com/software/mini_httpd/ version 1.30.
- Source pin: `mini_httpd-1.30.tar.gz` sha256
  `9c4481802af8dde2e164062185c279e9274525c3af93d014fdc0b80cf30bca6e`.

## W0 dependency check

mini_httpd 1.30 has no mandatory external dependencies: SSL support is
opt-in (`USE_SSL`, left off) and `CRYPT_LIB=-lcrypt` is kept at the upstream
default (musl/OHOS ships libcrypt; gnuchess precedent, experience §12.40).
`ci/scripts/preflight_check.sh mini-httpd/1.30` passed on the HarmonyOS PC
("no dependencies need to be checked").

## W0b history and environment

- The archive tree has no mini-httpd entry (`archives/m/` checked via the
  GitCode API on 2026-09-21); the platform has a done task for a *different*
  version (mini-httpd/1.3 by junshi_liu), no same-version conflict.
- No open PR touching mini-httpd; `recipe-search` found no similar recipe,
  so the recipe follows the Makefile-project pattern of
  `archives/c/connect-proxy/1.105` (R33 compiler resolution + manual
  package()).

## Build system analysis

- Bare upstream Makefile: no configure, no test target, `all` builds
  `mini_httpd` and `htpasswd`; `mime_encodings.h`/`mime_types.h` are
  generated from the shipped `.txt` tables by sed during the build.
- The recipe overrides `CC` (R33: taken from
  `tools.build:compiler_executables`, never `${CC}`), `CFLAGS`
  (-O2 -fPIE -D_GNU_SOURCE) and `LDFLAGS` (-pie -Wl,-z,relro,-z,now).
- Upstream `LDFLAGS=-s` (strip) is deliberately dropped: stripping removes
  the linker-embedded `.codesign` section and the binary then fails OHOS
  XPM execution (E077).
- `package()` installs `bin/mini_httpd`, `bin/htpasswd`, the two man pages,
  the README under `licenses/`, then E077-signs both ELF binaries in place
  (LD_LIBRARY_PATH stripped from the signer environment).

## Upstream test ledger (five dimensions)

| Dimension | Value | Basis |
|---|---|---|
| N_static | 0 | Upstream ships no test suite: no test/ directory, no check target (Makefile targets are all/mini_httpd/htpasswd/cert/install/clean/tar only) |
| N_registered | 0 | — |
| N_executed | 0 | — |
| Skipped | 0 | — |
| N_consumer | 1 | `test_package/smoke.sh` (see below) |

Upstream has no automated tests (recorded honestly); the consumer smoke test
provides real behavioral coverage of both packaged binaries and is never
presented as upstream coverage.

## Consumer test (test_package)

`smoke.sh` (POSIX sh, runs against the *packaged* binaries):

1. `htpasswd -c file alice` with the password on stdin — ACME htpasswd 1.30
   has no `-b` flag (that is the Apache variant); non-tty stdin goes through
   the upstream `add_password` fgets branch. Asserts rc=0 and an
   `alice:<hash>` line (2 assertions, exec-gate retry up to 3x).
2. `mini_httpd -p 18099 -d docroot -i pidfile` then a raw-socket HTTP GET
   via `http_check.py`: asserts HTTP 200, the `Server: mini_httpd/1.30`
   header and the served body, then terminates the server via the pidfile
   (4 assertions, connection retried up to 6x for exec-gate/daemon startup).

Device result: `mini-httpd consumer OK: htpasswd + HTTP round-trip`.

## Path A/B judgment

Path B does NOT trigger; verdict: pure Path A. Basis: the single patch
(patches/0001-musl-getpass.patch) applies the *already-documented* musl
lacks-getpass() knowledge (experience §12.40, gnuchess) to this package —
no new cross-repository behavior or knowledge was discovered, and the KB
dedup test would hit the existing entry. No knowledge-graph draft is filed.

## Patches

- `patches/0001-musl-getpass.patch` (`portability`, strip 1): htpasswd.c's
  getpass() fallback branch `#ifdef MPE` becomes
  `#if defined(MPE) || !defined(__GLIBC__)` with a termios-based
  implementation for musl targets (the historic gets()-based MPE fallback
  is kept). musl has no getpass(), so the non-MPE build failed to link
  (`undefined symbol: getpass`).

## OHOS-specific handling

- Package-time E077 signing for both binaries; exec-gate retries in the
  consumer test.
- No other platform patches needed: musl keeps resolver/sockets in libc, so
  the recipe does not link -lresolv/-lsocket/-lnsl.

## Source acquisition note

www.acme.com rejects the device conan/Python TLS handshake
(SSLV3_ALERT_HANDSHAKE_FAILURE) while curl succeeds; the verified tarball
was pre-seeded into the shared download cache
(`~/tmp/ch/dlcache/s/<sha256>` + single-URL sidecar, experience §12.39) and
conan reports "retrieved from local download cache" during the clean build.

## Verification record

- 2026-09-21, device worktree `~/qzy/GLM-67-mini-httpd-1.30`, CONAN_HOME
  `~/tmp/ch/home-glm67-minihttpd` (isolated), profile
  `ci/conan/profiles/ohos-aarch64`.
- `ohc-run.py conan-verify mini-httpd 1.30` after 7 iterations: Verdict
  PASS; G1 PASS (incl. test_package/MANIFEST.yml), G2 PASS (clean conan
  create from cached official tarball, patch applied, both binaries built
  and signed), G3 PASS (smoke test consumer round-trip).
- Drafting hygiene lesson recorded: shell scripts drafted on Windows were
  CRLF; busybox ash failed on them (`unmatched '{'`) until converted to LF.

### 对话记录

- 2026-09-21 GLM-67 夜跑实例：领坑（平台任务 13916，依赖活动）→ W0/W0b →
  connect-proxy 范式配方 → conan-verify 七轮迭代（G1 补 MANIFEST.yml；
  acme.com TLS 握手失败用共享 dlcache 预置绕过；musl 缺 getpass() 按 §12.40
  方案打 termios 补丁；htpasswd 1.30 无 -b 改用 stdin 喂密码；Windows 起草
  的 shell 脚本 CRLF 导致 ash 语法错，转 LF 后通过）→ Verdict PASS → finish
  → W4 → submit。
---

**编译结束**: 2026-09-21 00:03
**最终状态**: built
