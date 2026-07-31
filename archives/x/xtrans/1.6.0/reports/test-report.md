# xtrans 1.6.0 test report

## Final status

- Run: `xtrans-1.6.0-fresh-w3-r15`.
- Target: HarmonyOS HongMeng Kernel 1.12.0 AArch64.
- Toolchain: Python 3.12.9, Conan 2.29.1, Clang 15.0.4.
- Source: official X.Org `xtrans-1.6.0.tar.xz`.
- Source SHA256:
  `faafea166bf2451a173d9d593352940ec6404145c5d1da5c213423ce4d359e92`.
- Upstream registered tests: `0/0` (not applicable).
- Adapted substantive tests: `4/4 PASS (100%)`.
- Uncounted build preflights: 1 target declaration probe and 68 compile/link macro consumers.
- Unexpected terminals: `0`.

## Test counts

| Scope | Classification | Independent cases | Final result |
|---|---|---:|---|
| Upstream unit tests | Unit | 0 | No registered upstream unit target |
| Upstream integration tests | Integration | 0 | Generated `make check` target is empty |
| Upstream other tests | Other | 0 | No other test directory or declaration |
| Target capability probe | Build preflight | 0 | 1 compiled; not a test |
| Compile/link macro matrix | Build preflight | 0 | 68 compiled/linked; not tests |
| TCPv4/TCPv6 runtime | Integration | 2 | 2/2 PASS |
| Filesystem UNIX runtime | HarmonyOS-specific | 1 | 1/1 PASS |
| Package metadata | Integration | 1 | 1/1 PASS |
| Adapted workflows | Total | 4 | 4/4 PASS (100%) |

Upstream `Makefile.am` has no `TESTS`, `check_PROGRAMS`, `check-local`, or other
registered test target. The empty upstream total is reported as `0/0`, not as
a passing upstream suite. The four adapted tests have separate execution
boundaries. The 69 compile-only preflights and 134 internal checks are not
counted as tests.

The 68 consumers cover unique namespace, role, and transport macro inputs.
They conditionally reference all 32 non-Windows public functions declared by
`Xtrans.h`; UNIX inputs enable `XTRANS_SEND_FDS` under the same guard as the
implementation. Each consumer compiles the installed source distribution into
its own target executable. These probes take function addresses but do not
call the transport APIs, so independent W4 correctly classified them as
compile/link preflights rather than test PASS results.

The TCP runtime entries create a listener, connect and accept a client, wait
for readable data with a bound, transfer different payloads through scalar and
vector APIs in both directions, validate hostname, peer address, locality and
descriptor state, and require disconnect and all close calls to succeed. The
UNIX entry uses a caller-owned absolute endpoint. It accepts the HarmonyOS
capability result only when `OpenCOTSServer` succeeds and `CreateListener`
fails with exactly `EPERM`. It then requires `fcntl(F_GETFD)` to report
`EBADF`, requires the requested endpoint to be absent with `ENOENT`, and frees
only the remaining connection metadata. Other stages, error values, descriptor
states, endpoint states, and cleanup results remain fatal. Every runtime entry
is local-only and contacts no external host.

The package workflow checks the seven installed implementation sources,
license, documentation, Autoconf macro, definitions, and relocatable pkg-config
metadata. The resulting package has exactly 15 paths, including Conan's two
metadata files. The selected consumer and runtime executables were independently
confirmed as AArch64 ELF files.

## Dependency evidence

The run downloaded the released `xorgproto/2025.1` recipe and binary directly
from `ohpcd` before xtrans was built:

- Recipe revision: `f5274e33759da898a6e8d87d7708d47c`.
- Package ID: `283a988d63e011a731408b6abe0950de49e6171d`.
- Binary revision: `b7dc443b533634631c412ae235a57198`.

`Install finished successfully` is present in the frozen W0 binary log. No
source-build fallback was used for this prerequisite.

## Patch validation

The target-generated patch executed by r15 has SHA256
`4a8690a5dca13ff8631e67d4af35efe1443d8b46edd2de753cbf64e9466bf79b`.
It lets a caller-supplied absolute UNIX endpoint bypass creation of the
conventional X11 socket directory, so the test reaches the requested `bind()`.
It does not suppress the target result or restore the upstream-disabled
abstract UNIX client path.

After r15 completed, the patch representation was narrowed without changing
the applied source tree; the supplemental patch has SHA256
`f84176fb5ba558135e39d6178abd4b22ceb144d85623447ca811db088f991364`.
The immutable r15 patch and supplemental patch were replayed independently with
patch-ng, Git, GNU patch 2.7.6, and patch-ng. Their four complete 28-file source
trees are byte-identical, with sorted tree-manifest SHA256
`b38e09c192527c4a104ba01bdf63926c06e9d40b199ff20bc1aecbcf30ef1632`.
The manifest format is `SHA256`, two ASCII spaces, POSIX relative path, and LF,
sorted by relative path.
This is post-r15 packaging evidence and does not alter the frozen r15 inputs.

Current test-source SHA256 values:

- `consumer.c`:
  `2cdd141be17b1736264d94e8c09c40d682e9687c27284d10d80271fe25d222c9`.
- `runtime_smoke.c`:
  `82c1ab103a8543c902705f6bd2a48816d08c62345ccfefae99157830e23dcf3f`.

## Evidence integrity

- Frozen input manifest SHA256:
  `68d268625b82793adc4af543df3003fc800ed5b9f56fd485007291aab2635f63`.
- Original and deterministic replay archive SHA256:
  `e3dc5651a12572f52f581476fb9d56935a893199cb2a38446a1f340ce0e5c582`.
- Executed runner SHA256:
  `39d58b646dd7bc3715385af38bef68927c2b82756f033f753e5ce857fef0bd25`.
- Conan log SHA256:
  `8d47f264caf3821cafc7283fdb78bd8c34a03b097bc24db0590246a6955d6897`.
- Legacy r15 73-row terminal ledger SHA256:
  `4b78525942c279afef613f27cec1bf44f8923292e62ffc8a4895ee2c16b0d70f`.
- Evidence manifest SHA256:
  `6646aa80a9d01068e67d980bbdcc5837a966cd13aa1b1809a87084b5d4179048`.
- Returned evidence archive SHA256:
  `8e7830e5ac620d1f7d945f586aa1148fbea43bf14766bef4d4d0858455e40196`.
- Atomic `COMPLETE` SHA256:
  `e94f8c13eda7451b4262c87a9fcad508cc29b97dd88139de59c6e5f32aca79d6`.

The immutable r15 `COMPLETE` records the original 73 terminal rows and zero
unexpected outcomes. Independent W4 later determined that 69 rows represented
compile-only preflights, so the accepted substantive result is the four rows
`runtime_tcp4`, `runtime_tcp6`, `runtime_local`, and `package_metadata`.
`state.tsv` records zero fail, error, timeout, unexecuted, and unknown states.
The device and Windows readback validators both passed, the validator regression
suite passed 20/20, and the device lock was released before completion was
accepted.

## Knowledge submission boundary

The paired E234 draft documents the reusable compile-matrix plus target-runtime
method. It remains a `draft:true` KV/Markdown pair under `knowledge/drafts/`
and is submitted with xtrans. The formal graph, document index, and
`SUMMARY.md` remain unchanged.
