# xtrans 1.4.0 adaptation notes

## Scope

- Path: B (knowledge innovation). Knowledge draft E234 governs the test design
  for source-distributed transport libraries: a compile matrix alone cannot
  prove runtime transport behavior, so the substantive proof is a target
  loopback transaction. The formal knowledge graph, document, and index remain
  unchanged.
- The points repository contains no xtrans task, so no contest-claim Issue was
  created.

## Source and package contract

The official X.Org archive matches SHA256
`377c4491593c417946efcd2c7600d1e62639f7a8bbca391887e2c4679807d773`.
Upstream explicitly states that xtrans is not a shared library. Its Makefile
installs seven implementation sources into `include/X11/Xtrans`, an Autoconf
macro, and a pkg-config module. The Conan package preserves that contract and
declares `xorgproto/2025.1`, whose public headers are directly included by
`Xtrans.h`.

The release tarball's Autotools path would require the `xorg-macros` /
`util-macros` m4 package. The recipe avoids Autotools entirely because no
binary or generated source is installed. It reproduces the only target probe
that affects installed metadata: whether libc exports `fchown`. The result is
stored in both Conan definitions and the relocatable `xtrans.pc`. Following the
direct-copy discipline of E231, the recipe manually installs the seven source
files, the `xtrans.m4` autoconf macro, the generated `xtrans.pc`, the
`xtrans-defines.txt` consumer definitions, the `COPYING` license, and the
documentation.

The packaged patch lets a caller-provided absolute UNIX endpoint bypass
creation of the conventional `UNIX_DIR`. This is necessary to test the actual
requested endpoint instead of failing earlier while creating an unrelated X11
socket directory. It does not restore the upstream-disabled abstract UNIX
client path or suppress target policy: HarmonyOS still returns `EPERM` from the
endpoint's `bind()`, which is retained as a precise E024 capability result.

The only runtime dependency is `xorgproto/2025.1`, which provides
`X11/Xfuncproto.h`, `X11/Xos.h`, and `X11/Xmd.h` included by `Xtrans.h`. Its
publication in `ohpcd` was verified (W0) before this build.

## Tests

Upstream has no test suite: `Makefile.am` contains no `TESTS`,
`check_PROGRAMS`, `check-local`, or test target, and `make check` is an empty
Automake target. This is reported as zero, not as a skipped or passing test.

One syntax-only configuration preflight reproduces four libc declaration
checks that real Autotools consumers receive from `xtrans.m4`: `socklen_t`,
`sockaddr_storage`, `getaddrinfo`, and `inet_ntop`. It neither includes nor
calls xtrans, so it is not a test. The adapted build matrix covers six
self-contained symbol namespaces (default, X11, XIM, font server protocol,
font, and ICE), four role profiles (client, server, server with reopen, and
full duplex with reopen), and the TCPv4, TCPv6, and UNIX implementations
supported on Linux-like targets. The generic default namespace is TCP-only
because upstream defines no `UNIX_PATH`; `XSERV_t` is excluded because it
requires the X Server's private `os.h`, which is not part of either xtrans or
xorgproto. Each of the 68 valid combinations compiles and links the installed
`transport.c` into a separate executable. Together they conditionally take the
addresses of all 32 non-Windows public functions declared by `Xtrans.h`; UNIX
combinations define `XTRANS_SEND_FDS=1`, matching the implementation guard for
`SendFd` and `RecvFd`. They do not call the transport APIs and are not executed,
so they remain useful build preflights but are not counted as tests.

The four substantive tests have independent behavior and failure boundaries.
Two runtime workflows exercise TCPv4 and TCPv6 loopback end to end: listener
creation, client connection, accept, bounded readable waits, scalar and vector
bidirectional transfer, hostname/peer/locality checks, disconnect, and checked
cleanup. A third target workflow reaches a caller-supplied filesystem UNIX
endpoint and accepts only the documented OHOS `EPERM` after listener-stage
failure. The negative result is accepted only when `fcntl(F_GETFD)` proves the
listener descriptor is already closed with `EBADF`, the requested endpoint is
absent with `ENOENT`, and the remaining connection metadata is released exactly
once; every other result remains a failure. The fourth workflow checks source
inventory and generated metadata. The 69 build preflights and 134 verification
observations are explicitly excluded from the test count; there is no repeated
shared/static build, duplicate runtime input, or external host.

The reusable test lesson is recorded in the E234 knowledge draft submitted
with this software. A compile/link macro matrix is valuable for a
source-included package, but it cannot prove that bind, listen, connect,
accept, read, write, and close work on the target. E234 pairs those two layers
and requires exact negative-capability handling instead of a broad skip. It is
not added to the formal index by this software PR.

The target PC has no `cmake`, so the test compiles consumers directly with the
C compiler from `tools.build:compiler_executables` (the E229 pattern reused
from xorgproto).
---

**编译结束**: 2026-08-01 01:23
**最终状态**: built
