# plocate 1.1.24 adaptation notes

- Upstream build is Meson + C++17; hard deps are libzstd and threads only.
  liburing is probed by upstream with `dependency(..., required:false)` and
  absent → `-DWITHOUT_URING` (complete-pread fallback I/O). The recipe keeps
  that switch as option `with_uring` and both configurations were really
  built and exercised on target (see B evidence below).
- `with_uring=True` (liburing/2.15 from the registry) links fine and the
  binaries run, but any real query dies: HongMeng Kernel 1.12.0's app-domain
  seccomp allows `io_uring_setup` (raw probe: fd=3) yet kills the process
  with uncatchable SIGSYS (exit 159) on `io_uring_register` — which liburing
  `io_uring_queue_init()` performs internally via the PROBE registration.
  A setup-only capability probe is therefore a false positive. Default is
  `with_uring=False`; the fallback path passes the full 10/10 end-to-end
  suite (db build → exact-match queries).
- Four portability patches (all `patch_type: portability`):
  1. `conf.cpp`: musl/OHOS has no glibc `program_invocation_name`; mapped to
     `__progname` under `#ifndef __GLIBC__` (libc-probe guard exception per
     R8 — it is a libc feature test, not a platform macro stub; it keeps the
     glibc path byte-identical on Linux).
  2. `plocate.cpp`: the query entry point bails out on
     `access("/", R_OK|X_OK)`; OHOS mounts `/` `drwx--x--x`, so every normal
     user fails R_OK and the whole database silently yielded zero matches
     (no error, exit 1). Locating a known name only needs X_OK — probe
     relaxed to X_OK, Linux semantics unchanged (there `/` is 755).
  3. `access_rx_cache.cpp`: same R_OK|X_OK bug per ancestor directory in the
     visibility cache; on OHOS the chain dies at `/` and every file is
     marked invisible. X_OK only.
  4. `meson.build`: the optional TurboPFor probe calls
     `run_command('[', '-r', ..., ']')`, so it needs a standalone `[`
     executable. On this device `[` exists only in `~/usr/local/bin`
     (`/bin/[` and `/usr/bin/[` are both absent), and the CI worker PATH
     (`/data/app/bin:/system/bin:...`) does not contain that dir, so
     `meson.configure()` aborted on CI with `Program or command '[' not
     found or not executable` while every on-device build passed — a
     PATH asymmetry, not a functional difference. Replaced by
     `fs.is_file(pfordir + '/libic.a')` through the `fs` module this file
     already imports (line 58), so no external program is looked up at
     all. `[ -r ]` vs `is_file` differ only for a present-but-unreadable
     archive, which the `find_library('ic', dirs: ...)` on the next line
     would fail on regardless.
- Packaging plumbing (no upstream change): MesonToolchain emits no
  `[binaries]` ar entry and conan's build PATH lacks the toolchain dir, so
  the recipe pins ar/ranlib/strip/pkgconfig absolute paths into
  `conan_meson_native.ini` (libapk precedent). Upstream also expects
  liburing.h in a distro system include and omits the uring dep on the
  updatedb target; the recipe injects the dep's include dir via
  `extra_cxxflags`. Packaged ELFs are signed with `binary-sign-tool
  -selfSign 1` in package() (abx/0.1 flow) — meson+lld leaves the
  `.codesign` placeholder empty and the OHOS kernel rejects execution
  ("Operation not permitted") until a valid signature exists.
- Upstream test ledger: the official release tarball registers **0** tests
  (`meson.build` has no `test()`; no `tests/` ships — independently checked
  on the 1.1.23 Debian `.orig`). Upstream git (git.sesse.net) was
  TLS-unreachable on 2026-09-24, so the in-tree state could not be
  re-verified (recorded as 无法核验, not as "tests exist"). Behavioral
  coverage is the end-to-end test_package suite (1 consumer program, 10
  assertions): version, `plocate-build -p` db build from a plaintext list,
  exact 2-file match, `-i`/`-c`/`-b`/`-r`/`-l` semantics, empty no-match,
  4-file regex sweep.
- Known limitations: `updatedb` (the periodic indexer) expects a system
  group named `plocate` and root cron/systemd deployment per upstream
  design; on a non-root OHOS device it reports "Unknown group plocate" —
  database creation on-device uses `plocate-build -p` (covered by the
  suite). systemd units are disabled via `-Dinstall_systemd=false`;
  `install_cron` is off upstream by default.
- CI-vs-device reproduction (isolated, configure-only, no compile): with
  PATH curated to exclude `~/usr/local/bin` — mirroring the worker — the
  pristine condition errors at configure (`ERROR: Program or command '['
  not found or not executable`) while the patched `fs.is_file()` condition
  configures successfully. Probe project: `~/tmp/uc2/hw-3/plocate/cibin/`.
  Full build after patch 4: `~/tmp/uc2/hw-3/plocate/verify-0004.log`
  (recipe rev `e10c0602ba6ebb2d870538f1c45fe65c`, `CREATE_RC=0`, end-to-end
  consumer suite 10/10, `MEMCAP[probe] peak=204MB`, meson 1.11.1).
- B evidence: DRAFT-plocate-1.1.24-io_uring-hongmeng-seccomp-sigsys.{kv,md}
  (draft-review verdict: create; nearest neighbors E051/E246 documented as
  different mechanisms). The `access("/"` R_OK silent-zero mechanism is
  generic and was also filed to the cross-package draft pool.
---

**编译结束**: 2026-09-25 12:43
**最终状态**: built
