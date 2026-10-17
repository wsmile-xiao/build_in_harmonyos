# libdill 2.14 adaptation notes

## Source
- Official HTTPS: `https://github.com/sustrik/libdill/archive/refs/tags/2.14.tar.gz`
- SHA256: `ebba0e5b433ec123b74a57d49b89dfa673aa258e03e6a452959e556b4c4529b9`
- Tag: `2.14` (commit d958f29, confirmed via GitHub tags API)
- License: MPL-2.0

## Build system: Autotools
The GitHub tag archive ships no pre-generated `configure`/`Makefile.in` — only
`configure.ac` + `Makefile.am` + `autogen.sh` (which runs `autoreconf -ifv`).
Therefore `tool_requires` must provide the full autotools toolchain:

    tool_requires = m4/1.4.19, autoconf/2.72, automake/1.18, libtool/2.5.4, pkgconf/3.0.5

These are pulled from the OHPCD registry as prebuilt binaries. The conan
`automake` package's wrapper scripts use the system perl with `PERL5LIB` pointed
at the conan automake share dir (the conan-bundled perl has a mismatched `Cwd.so`).

## Patches
1. **0001-hardcode-package-version-2.14.patch** — `package_version.sh` uses
   `git describe` to produce the version string. A git tag archive has no `.git`
   directory, so the fallback returns a bogus default. This patch replaces the
   script body with `echo "2.14"` so `AC_INIT` resolves correctly.

2. **0002-skip-man-subdir.patch** — `SUBDIRS=man` triggers `help2man` to generate
   man pages, but `help2man` is not available in the OHOS build environment.
   Man pages are not needed for library packaging. This patch sets `SUBDIRS=`
   (empty), skipping the `man/` subdirectory entirely.

No POSIX compatibility layer or platform-specific shims were added preemptively.
Per the task rules, platform differences are addressed only from real compile/test
errors — and none required source-level fixes (see OHOS findings below).

## OHOS POSIX findings (from real build + test run)
`make check` on OHOS aarch64: **28/29 tests pass, 1 failure**.

| API area | Status | Notes |
|----------|--------|-------|
| socket (AF_INET/AF_INET6) | ✅ pass | tcp/udp/http/ws tests pass |
| socketpair | ✅ pass | used by ipc_pair internally |
| poll/select | ✅ pass | libdill's fd polling works |
| nonblocking IO | ✅ pass | O_NONBLOCK + EAGAIN/EWOULDBLOCK |
| errno | ✅ pass | all errno values correct |
| clock/time | ✅ pass | now()/msleep() work |
| signal | ✅ pass | signal tests pass |
| AF_UNIX bind (path) | ❌ EPERM | HMDFS MAC sandbox (`hmmac=use_task`) blocks `bind()` of AF_UNIX socket on a filesystem path. This is an **environment restriction**, not a libdill defect or missing OHOS POSIX API. Abstract-namespace AF_UNIX bind works. `tests/ipc` is the only failure. |

No code patches were needed for any of these — the single failure is a sandbox
permission issue that would not affect consumers using libdill's tcp/udp/coroutine
/channel APIs (which is the primary use case).

## Test inventory
- **check_PROGRAMS (formal tests)**: 29 — registered via `TESTS = $(check_PROGRAMS)`
  - 13 core tests (coroutine, channel, bundle, fd, go, etc.)
  - 2 thread tests (conditionally built with `if THREADS`)
  - 12 socket tests (tcp, udp, http, ws, dns, etc.)
  - 1 TLS test (conditionally built with `if TLS`)
  - 1 ipc test (the single failure)
- **noinst_PROGRAMS (not formal tests)**:
  - 7 perf benchmarks (`perf/latency`, `perf/throughput`, etc.)
  - 14 tutorial programs (`tutorial/protocol/step1`–`step3`, etc.)
  - 2 examples (`examples/hello`, `examples/hello2`)

## test_package
A stable, self-contained consumer that:
- Links against `libdill::libdill`
- Exercises: `coroutine` macro, `chmake`/`chsend`/`chrecv`/`chdone`/`hclose` (channels), `now`/`msleep` (clock/time API)
- Does NOT access the internet or any external service
- Does NOT use random ports
- Prints `CHECK N: ...` for each assertion and a final `All checks passed.` / `RESULT: All checks passed.`

## Installed artifacts
- `include/libdill.h`, `include/libdillimpl.h`
- `lib/libdill.a` (static) or `lib/libdill.so*` (shared)
- `pkg-config` name: `libdill`
- System libs: `pthread`
- Soname: `libdill.so.31` (libtool -version-info 31:5:1 from `abi_version.sh`)
