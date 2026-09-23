# libaudit 2.7.4 — OHOS PC (AArch64) Conan 2 archive

## What this is

`libaudit` is the Linux Audit System client library: it opens a
`NETLINK_AUDIT` socket to the kernel audit subsystem (`audit_open` /
`audit_send` / `audit_get_reply`), builds audit rules
(`audit_rule_fieldpair_data` & friends), and hosts the
syscall/machine/field/message lookup tables.  The same source tree also
builds `libauparse` (audit-log parsing) and the admin tools (auditctl,
auditd, ausearch, aureport, autrace, ausyscall, ...).  This package is
the **library-oriented packaging** of the
[linux-audit/audit-userspace](https://github.com/linux-audit/audit-userspace)
monorepo at tag `audit-2.7.4` (2.7.x tags carry **no "v" prefix**);
the sibling whole-project packaging `audit/4.1.2` is already archived.

Deliverables: `libaudit.a` + `libauparse.a` (static-only, R26 — the
system-same-name .so must not shadow anything), headers, and the CLI
tools (declared in the software-level `commands.json`).

## Upstream source & license

- Source: `https://github.com/linux-audit/audit-userspace/archive/refs/tags/audit-2.7.4.tar.gz`
- SHA256: `6e5e302476b4625c71d65e39032b3d2827f43c9e21bdd9072607080e523f4d89`
- License: LGPL-2.1-or-later (libraries), GPL-2.0-or-later (tools)
- Build system: Autotools (`configure.ac` + `Makefile.am`, no
  pre-generated `configure` in the tag archive → `autoreconf -f -i`
  bootstrap with tool_requires automake/1.18 + libtool/2.5.4).

## W0 dependency check

- `libcap-ng/0.8.5` is published in the ohpcd registry — but it is
  **optional** for libaudit (used only by auditctl's capability-dropping
  codepaths).  The recipe builds `--without-libcap-ng`, keeping the
  dependency surface empty for this port (W0 "可关则关").
- No other third-party dependencies (python/go bindings disabled).

## OHOS netlink reality (W0 deep-dive, tested on-device)

`socket(PF_NETLINK, SOCK_RAW, NETLINK_AUDIT)`:

- The kernel uapi constants (`NETLINK_AUDIT=9`, the full `linux/audit.h`
  message/type surface) are present in the OHOS SDK sysroot.
- At runtime, the OHOS kernel/SELinux policy **denies the audit netlink
  socket to the app sandbox** (`errno=13 EACCES`), while
  `NETLINK_KOBJECT_UEVENT` and `NETLINK_ROUTE` sockets open fine.
- Consequence: `audit_open()` fails gracefully with a negative fd —
  exactly the error surface the API documents for "audit support not
  in kernel".  The netlink-mediated control plane therefore cannot be
  exercised by tests; the pure-library surface (lookup tables, rule
  construction, ausearch/auparse parsing) is fully functional.
- Declared as such in the PR body (testing exemption wording) — no
  stub was needed in the source: upstream code already handles the
  failure path.

## Upstream tests audit (make check, run in build())

| Suite | Test | Result |
|---|---|---|
| lib/test | lookup_test | PASS |
| src/test | ilist_test | PASS |
| src/test | slist_test | PASS |
| audisp/plugins/remote | test-queue | PASS |
| auparse/test | auparse_test + auparselol_test (custom check target, 10 sections, diffed against .ref) | PASS ("Auparse Test Passes") |

Local run (this worker, 2026-09-15): `make -j1 && make check` →
TOTAL 1+2+1 automake tests PASS + the auparse custom check target
passes; exit 0.  Note the audit 4.1.2 archive had `lookup_test` FAIL on
aarch64 (i386 table assumptions) — 2.7.4 passes after the header fixes.

The task prompt mentions `audit-testsuite`: that is a separate
repository (linux-audit/audit-testsuite) and is **not** part of the
2.7.4 release tarball — the in-tree tests above are the release's own
suite.

## OHOS adaptations (17 patches)

Guard style (R8): platform branches use libc-feature checks
(`#if !defined(__GLIBC__)`) rather than `#ifdef __OHOS__`, so the
fallbacks cover every musl-family libc and glibc behaviour is
untouched; a few guards are plain unconditional/`#ifndef` where the
POSIX replacement is equivalent for all platforms (see patches).

- **sockaddr_storage redefinition** (lib/libaudit.h,
  lib/gen_tables.c, src/ausearch-lookup.c, src/autrace.c): OHOS bionic
  declares `struct sockaddr_storage` in `sys/socket.h` *without* an
  include guard, and the uapi `linux/socket.h` (pulled via
  linux/netlink.h / linux/net.h) declares it again.  Fix: define the
  uapi header's own guard `_UAPI_LINUX_SOCKET_H` before either header
  can be included, and re-supply the `__kernel_sa_family_t` typedef
  that linux/netlink.h needs.  (Same conflict family as audit/4.1.2's
  0069-lib-libaudit.h.patch, generalized to every TU that includes
  `<linux/net.h>` before libaudit.h.)
- **AUDIT_FILTER_EXCLUDE redefinition** (lib/libaudit.h): upstream
  2.7.4 assumed pre-2.6.30 kernels without `AUDIT_FILTER_EXCLUDE` in
  the uapi; OHOS's linux/audit.h already defines it (0x05).  Guarded.
- **rawmemchr** (auparse/interpret.c): glibc extension missing in
  OHOS libc → `memchr(ptr, '\0', (size_t)-1)`.
- **strndupa** (auparse/auparse.c, src/ausearch-lol.c, src/auditd.c):
  glibc extension missing.  Implemented as a **macro** (statement
  expression + `__builtin_alloca`) — NOT a `static inline` function:
  clang's inliner emits `llvm.lifetime` markers for the alloca of an
  inlined function that invalidate the returned buffer immediately
  after the call, which corrupted the tokens `audit_strsplit` returned
  (root-caused with a standalone reproducer; the inline version made
  auparse_test fail while the macro version passes).
- **pthread_cancel** (src/auditd-reconfig.c, audisp/audispd.c,
  audisp/plugins/zos-remote/zos-remote-plugin.c): OHOS pthreads do not
  implement cancellation → `#define pthread_cancel(t)
  pthread_kill((t), 0)` (same approach as the audit 4.1.2 OHOS port).
- **fd_set / select** (src/auditctl.c, src/auditd.c, src/autrace.c,
  src/delete_all.c): glibc pulls sys/select.h implicitly; OHOS does
  not → explicit include.
- **PATH_MAX** (audisp/audispd.c, audisp/plugins/prelude/…): explicit
  `<limits.h>` include.
- **event_node_list tentative definition** (src/ausearch-common.h):
  a header-file tentative definition becomes a duplicate symbol under
  lld's default `-fno-common` → `extern` under `__OHOS__` (the real
  definitions live in ausearch-options.c / aureport-options.c, one per
  binary).
- **posix_fallocate return-code semantics**
  (audisp/plugins/remote/queue.c): POSIX specifies posix_fallocate
  *returns* the error number and does **not** guarantee errno (glibc
  merely happens to set it).  OHOS HMDFS does not implement
  allocation: it returns `EACCES` with errno untouched, so the
  upstream `if (posix_fallocate(...) != 0) return -1` mis-read stale
  errno (observed ERANGE 34 from earlier strtoul residue).  Fix:
  inspect the return code, fall back to `ftruncate` for
  "not supported" errors (same file-size guarantee).
- **test-queue /tmp template** (audisp/plugins/remote/test-queue.c):
  OHOS mounts /tmp read-only (E002) → template honours `$TMPDIR`
  (fallback /data/local/tmp).

Build-time adaptations (no source patch): autoreconf bootstrap
(E443-style), umask-077 removal from the generated configure (E114),
`make -j1` (E074 HMDFS jobserver fifo), ohos triplet pinning (E007/
E514-class: `--build/--host=aarch64-unknown-linux-ohos` so the probe
never runs), `TMPDIR` must be writable for make check.

## Local verification (2026-09-15, this worker)

1. `autoreconf -f -i` (conan automake/1.18 + libtool/2.5.4 + SDK
   autoconf 2.72; GNU sed needed on PATH for libtoolize).
2. out-of-tree `configure --build/--host=aarch64-unknown-linux-ohos
   --without-python --without-python3 --without-golang
   --without-libcap-ng --disable-zos-remote --disable-listener` —
   clean.
3. `make -j1` → libaudit.a/.so, libauparse.a/.so, auditd, auditctl,
   aureport, ausearch, autrace, audispd, audisp plugins, ausyscall,
   aulast, aulastlog, auvirt — clean.
4. `make check` → all PASS (see table above).
5. `make install DESTDIR=...` staging → libs + headers + sbin tools +
   pkgconfig (audit.pc, auparse.pc).
6. Smoke: `aureport --version` → 2.7.4; `ausearch --version` → 2.7.4;
   `auditctl --version` → "You must be root to run this program."
   (expected: needs audit netlink + root); `ausyscall x86_64 open` → 2.
7. Consumer smoke (test_package contract): 23 CHECKs, all PASS.

## Layout

```
2.7.4/
├── conanfile.py             # Conan 2 recipe (autotools, static-only R26)
├── conandata.yml            # source URL + SHA256 + 17 patches
├── manifest.yaml            # version manifest
├── notes.md                 # this file
├── patches/                 # 0001..0017 OHOS portability patches
├── reports/
│   └── quality-report.md    # conan-verify result
└── test_package/            # offline consumer contract test
    ├── conanfile.py         #   CMake + direct run under conanrun
    ├── CMakeLists.txt       #   find_package + target link
    ├── consumer_tests.c     #   23 CHECKs over the public API
    └── MANIFEST.yml         # upstream/test audit + counting
```

---

**编译结束**: 2026-09-15
**最终状态**: built
