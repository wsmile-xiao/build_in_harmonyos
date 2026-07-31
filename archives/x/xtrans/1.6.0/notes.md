# xtrans 1.6.0 adaptation notes

## Scope

- Dependency Issue: #1291.
- Path: A (basic adaptation) + B (knowledge innovation). Existing formal
  knowledge covers the observed platform failures, while the E234 knowledge
  draft submitted with this software generalizes the reusable testing pattern
  developed here for source-distributed transport implementations. The formal
  graph, document, and index remain unchanged.
- The points repository contains no xtrans task, so no contest-claim Issue was
  created.

## Source and package contract

The official X.Org archive matches SHA256
`faafea166bf2451a173d9d593352940ec6404145c5d1da5c213423ce4d359e92`.
Upstream explicitly states that xtrans is not a shared library. Its Makefile
installs seven implementation sources into `include/X11/Xtrans`, an Autoconf
macro, and a pkg-config module. The Conan package preserves that contract and
declares `xorgproto/2025.1`, whose public headers are directly included by
`Xtrans.h`.

The release tarball's Autotools path first hit HarmonyOS platform recognition
and HMDFS temporary-directory permissions. Those signatures are already
covered by E007 and E129. The first exploratory Conan run also confirmed E002:
Clang could not create its default temporary file on the read-only `/tmp`
mount. Both recipe and test package now bind `TMPDIR` to a writable directory
inside their Conan build folder. The final recipe does not run Autotools
because no binary or generated source is installed. It reproduces the only
target probe that affects installed metadata: whether libc exports `fchown`.
The result is stored in both Conan definitions and the relocatable `xtrans.pc`.

The packaged patch lets a caller-provided absolute UNIX endpoint bypass
creation of the conventional `UNIX_DIR`. This is necessary to test the actual
requested endpoint instead of failing earlier while creating an unrelated X11
socket directory. It does not restore the upstream-disabled abstract UNIX
client path or suppress target policy: HarmonyOS still returns `EPERM` from the
endpoint's `bind()`, which is retained as a precise E024 capability result. The
patch executed by fresh target W3 r15 was generated on the target with the
standard POSIX `refresh-patch --auto` flow and has SHA256
`4a8690a5dca13ff8631e67d4af35efe1443d8b46edd2de753cbf64e9466bf79b`.
After r15 completed, only the patch representation was narrowed to remove blank
and Tab-only context; that supplemental patch has SHA256
`f84176fb5ba558135e39d6178abd4b22ceb144d85623447ca811db088f991364`.
Fresh replay used the immutable r15 patch as a patch-ng baseline and the
supplemental narrowed patch with Git, GNU patch 2.7.6 `--fuzz=0`, and patch-ng
1.19.1. All four trees contain the same 28 files and have the common sorted
tree-manifest SHA256
`b38e09c192527c4a104ba01bdf63926c06e9d40b199ff20bc1aecbcf30ef1632`.
Each manifest row is the file SHA256, two ASCII spaces, its POSIX relative
path, and LF, with rows sorted by relative path.
This replay supplements r15 packaging evidence; it does not replace or rewrite
any r15 execution input.

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
Searches of `origin/main` knowledge graph, documents, and operations at
`8c5703f967b606bc454831e265005d440d26dce5` found no equivalent entry, so this
software PR claims path B under the reusable-test rule.

The formal fresh target W3 r15 completed on HarmonyOS HongMeng Kernel 1.12.0
AArch64 with Python 3.12.9, Conan 2.29.1, and Clang 15.0.4. Before the xtrans
build, Conan downloaded the released `xorgproto/2025.1` recipe revision
`f5274e33759da898a6e8d87d7708d47c` and binary revision
`b7dc443b533634631c412ae235a57198` for package ID
`283a988d63e011a731408b6abe0950de49e6171d`; no `--build=missing` fallback was
used for the prerequisite.

The frozen r15 input contains the then-current recipe, patch, profile, tests,
validator, and official source. It predates the later W4 count correction and
is retained as immutable historical execution evidence. Its manifest SHA256 is
`68d268625b82793adc4af543df3003fc800ed5b9f56fd485007291aab2635f63`;
the original and deterministic replay archives both have SHA256
`e3dc5651a12572f52f581476fb9d56935a893199cb2a38446a1f340ce0e5c582`.
The current `consumer.c` SHA256 is
`2cdd141be17b1736264d94e8c09c40d682e9687c27284d10d80271fe25d222c9`,
and the current `runtime_smoke.c` SHA256 is
`82c1ab103a8543c902705f6bd2a48816d08c62345ccfefae99157830e23dcf3f`.

r15 emitted exactly 73 unique `PASS` terminal rows: one target declaration
probe, 68 macro consumers, two TCP runtime transactions, one OHOS UNIX
capability workflow, and one package/metadata workflow. Independent W4 later
classified the first 69 rows as build preflights because they do not call
xtrans behavior. The truthful adapted test result is therefore `4/4 (100%)`,
while the original 73-row ledger and hashes remain unchanged as historical
evidence. `FAIL`, `ERROR`, `TIMEOUT`, `UNEXECUTED`, `UNKNOWN`, and other
unexpected terminals are all zero. Both selected package consumers are AArch64
ELF files, the installed package contains the exact 15 expected paths, and the
device lock was released before the atomic `COMPLETE` marker was accepted. The
current orchestration no longer executes the 69 preflights; this classification
correction did not change `runtime_smoke.c` or `verify_package.py`, and no new
device run is claimed.

The Conan log SHA256 is
`8d47f264caf3821cafc7283fdb78bd8c34a03b097bc24db0590246a6955d6897`;
the executed runner SHA256 is
`39d58b646dd7bc3715385af38bef68927c2b82756f033f753e5ce857fef0bd25`;
the legacy 73-row terminal ledger SHA256 is
`4b78525942c279afef613f27cec1bf44f8923292e62ffc8a4895ee2c16b0d70f`;
the evidence manifest SHA256 is
`6646aa80a9d01068e67d980bbdcc5837a966cd13aa1b1809a87084b5d4179048`;
the returned evidence archive SHA256 is
`8e7830e5ac620d1f7d945f586aa1148fbea43bf14766bef4d4d0858455e40196`;
and the atomic `COMPLETE` SHA256 is
`e94f8c13eda7451b4262c87a9fcad508cc29b97dd88139de59c6e5f32aca79d6`.
The device validator and Windows readback validator both passed. The validator
regression suite passed 20/20, including rejection of package-count drift and
all failed-listener cleanup-contract drift.
