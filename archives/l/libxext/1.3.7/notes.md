# libxext 1.3.7 adaptation notes

## Evidence status

- Source version: 1.3.7, the highest stable release listed by X.Org on
  2026-08-19.
- Source SHA256: `6c643c7035cdacf67afd68f25d01b90ef889d546c9fcd7c0adf7c2cf91e3a32d`.
- The final candidate HEAD, tree, and current-main base are recorded in the
  external W0/W3/W4 evidence rather than duplicated in this tracked file.
- Historical r16 W0 candidate tree:
  `25b2413007dc629dfd7011aa2bce458289c38cb9`.
- Formal W0: passed from a fresh isolated Conan home with `--build=never`.
- `libx11/1.8.13`: RREV `e3ce69008a37ca95d1f0918c47709057`,
  package ID `cae7d429fb6839b6840b7602f11bf20c76efecdf`, PREV
  `701e81816807aea0ad862a324557f4e9`, downloaded from `ohpcd`.
- `xorgproto/2025.1`: RREV `f5274e33759da898a6e8d87d7708d47c`,
  package ID `283a988d63e011a731408b6abe0950de49e6171d`, PREV
  `b7dc443b533634631c412ae235a57198`, downloaded from `ohpcd`.
- The official X.Org archive index returned HTTP 200 on 2026-08-20 and lists
  `1.3.7` as the highest stable libXext source release. It does not list
  `1.7.0`. The software-level `1.7.0` row is retained as a historical
  publication fact, but its upstream identity is marked invalid and it is not
  eligible to supersede stable upstream releases: the old ref used a moving
  master snapshot without a source SHA256 or version directory. The authority
  evidence is under
  `E:\HarmonyPC\validation\libxext-1.3.7\upstream-authority-20260820-r1`.
- W3 r20 reached a real target-side `conan create` after setup and dependency
  resolution, then failed before compilation because upstream `config.guess`
  created `$TMPDIR/cg*` with `umask 077`; HMDFS made the directory unwritable
  and `dummy.c` creation returned `Permission denied`. No upstream or consumer
  test ran, no `.ci-result.json` was generated, and W4 is not yet valid.
- The immutable r20 result is under
  `E:\HarmonyPC\validation\libxext-1.3.7\w3-current-main-20260819-r20-device`.
  The collected 33,308-byte result has SHA256
  `ca9cefbeb2a09503522c4b35e4edd9c73439557ff3284207e72332028ecb9fe1`;
  its unique remote root was deleted after collection and an independent SSH
  readback confirmed absence.
- W3 r21 proved that the r20 HMDFS permission failure was fixed: the generated
  `config.guess` helper created and used its compiler probe successfully. It
  then failed at the next boundary because the copied upstream classifier has
  no platform case for the device kernel. The compiler itself reports
  `aarch64-unknown-linux-ohos`; upstream `config.sub` accepts that exact tuple
  unchanged when invoked through the verified Bash interpreter with the
  task-private temporary environment. r21 produced no `.ci-result.json` and
  was collected and cleaned as a truthful FAIL.
- W3 r22 proved the compiler-derived tuple and Bash configure path: configure
  completed, generated all build files, and compiled every libXext object. The
  final shared-library link then consumed the published `libX11.la`, whose
  `dependency_libs` still contained obsolete `.conan2` and `.cache/conan2`
  paths, and failed on a missing historical `libxcb.la`. r22 produced no
  `.ci-result.json` and was collected and cleaned as a truthful FAIL.
- W3 r23 prepared 29 Libtool shadows with 132 path replacements, then built,
  ran the zero-entry upstream `make check`, installed, and packaged libXext
  successfully. The test package failed at compile time because both consumers
  included extension headers before `<X11/Xlib.h>`, leaving public Xlib types
  such as `Display`, `Bool`, `Time`, and `XID` undeclared. r23 produced no
  `.ci-result.json` and was collected and cleaned as a truthful FAIL.
- W3 r24 transferred and verified the complete payload, but the first result
  readback connection ended before any launch was committed. Its durable
  `launch_count=0` evidence therefore remains `NOT_RUN`; the unique staging
  root was removed and the attempt was not reused.
- W3 r25 built, ran the zero-entry upstream `make check`, installed, and
  packaged libXext again. `sync_value_contract.c` compiled and linked, while
  `registry_contract.c` failed because the installed `extutil.h` exposes the
  protocol types `xEvent` and `xError` without including their defining
  header. Upstream sources obtain those declarations through private
  `Xlibint.h`; the installed-package consumer now includes the public
  `<X11/Xproto.h>` explicitly before `extutil.h`. r25 produced no
  `.ci-result.json`; its 68,129-byte result SHA256 is
  `b55b0ba553fa62fa1b49f33cd5d39e967eed2dfd111f40ac59e1851ec37d1e55`.
  The unique remote root was deleted only after matching that result identity
  and finding zero root-bound processes, and an independent SSH readback
  confirmed absence. r25 is a consumed truthful FAIL and must not be rerun.
- W3 r26 proved the public `Xproto.h` include fix: both installed-package
  consumers compiled and linked. The first consumer then returned RC 8 because
  its final check required the subtraction overflow flag to be false for
  `1 - 2`. X.Org's public documentation describes that result as non-overflow,
  but the historical `_XSyncValueSubtract` macro sets the flag on this sign
  transition. The consumer still calls `XSyncValueSubtract` and verifies the
  exact `-1` result; it no longer turns the historical overflow-bit behavior
  into a package rejection. r26 produced no `.ci-result.json`; its 66,593-byte
  result SHA256 is
  `94fe7396dbd10283e2107746724fb53908e2499d21e6275f11faeca8f82079e1`.
  The result-bound cleanup found no process attached to the unique root,
  removed it, and an independent SSH readback confirmed absence. r26 is a
  consumed truthful FAIL and must not be rerun.
- W3 r27 proved the recipe-level W3 substep and both consumer variants. The
  official `finish` invocation generated a valid `.ci-result.json` with
  `exit_code=0`; its normal build and forced-static replay each emitted exactly
  one `sync_value_contract PASS` and one `registry_contract PASS` marker.
  The aggregate r27 wrapper remains a truthful FAIL because the full `finish`
  command returned RC 1 after W3: repository-wide knowledge validation reported
  pre-existing formal-entry gaps, and the legacy submit-readiness check required
  local packaging/staging files that are not the Conan W3 result. The collected
  146,987-byte result SHA256 is
  `241df4176abb0cc468376e61a4bd9c1c39c6b183db5168c2ab04c9cdb2b618f7`.
  Its unique remote root was removed after a result-bound zero-process check,
  and an independent SSH readback confirmed absence. r27 is consumed and must
  not be rerun or relabeled as an aggregate PASS.
- Exact final-candidate W0 evidence: `reports/W0-report.md` and the create-new
  durable run at
  `E:\HarmonyPC\validation\libxext-1.3.7\w0-current-main-20260820-r30`.
- Exact lowercase `libxext/1.3.7` is not already published. Fresh registry
  evidence is under
  `E:\HarmonyPC\validation\libxext-1.3.7\publication-check-20260819-r1`,
  and the 2490-build release scan is under
  `E:\HarmonyPC\validation\libxext-1.3.7\release-scan-20260819-r1`.

## Build design

The recipe uses the release Autotools files and preserves the upstream source
and library ABI. The native OHOS path uses the verified
`/data/service/hnp/bin/bash`, a package-local
temporary directory, a build-local `configure-ohos` copy for the HMDFS umask
workaround, and a build-local `config.guess-compiler` helper. The helper emits
only the tuple returned by the active Conan compiler's `-dumpmachine`; it has
no platform-name branch or conditional macro. The release `configure` and
`config.guess` in `source_folder` remain byte-identical. Generation requires
exactly two `umask 077` sites and two configure-to-config.guess call sites,
then fails closed on drift. Configure and `config.sub` run through the verified
`/data/service/hnp/bin/bash`, so their temporary files stay in the writable
task root.

Before configure, the recipe also creates a task-local Libtool shadow from the
complete dependency `.la` closure. It copies every referenced real library,
rewrites transitive `.la` paths and stale Conan `-L` entries into the shadow,
binds each shadow `libdir`, and redirects the generated `x11.pc` there. The
original dependency packages are read-only and unchanged. This follows
`conan-libtool-transitive-la-shadow-closure`. No source patch is declared.

The corrected focused validator passed 4/4, including original-file hash
preservation and negative cases for configure call-site drift, a missing
`config.guess`, and an unsafe whitespace-bearing build path. Evidence is
`E:\HarmonyPC\validation\libxext-1.3.7\config-guess-copy-focused-20260819-r2.log`
with SHA256
`be7ef3a4678adade9f3673730e72997ae58c336f4238481d331c68709f9257a4`.

The Libtool shadow fixture passed 5/5, including the full
`libX11.la -> libxcb.la -> libXau.la/libXdmcp.la` closure and negative cases
for ambiguous basenames, missing real libraries, missing transitive archives,
and a missing generated `x11.pc`. Evidence is
`E:\HarmonyPC\validation\libxext-1.3.7\libtool-shadow-focused-20260820-r1.log`
with SHA256
`adabe07d6279e2fe719e4f957bbbe8c0c5679ae23192dc5eaeffd45f8d113d12`.

Independent W4 r1 rejected the earlier in-place configure rewrite as an R6
violation. The focused correction validator now covers the successful copy,
replacement-count drift, a missing upstream configure, and generate/build
wiring, plus the exact official 1.3.7 configure input; all five cases pass or
fail closed as intended. A fresh independent W4 is required for the corrected
commit.

## Dependency boundary

- `libx11/1.8.13`: direct linked dependency.
- `xorgproto/2025.1`: direct public protocol-header dependency.

libxcb and xtrans remain transitive dependencies of libX11.

## Test inventory

The release registers no Automake `TESTS`, `check_PROGRAMS`, `check-local`, or
Meson `test()` entry. The truthful upstream count is therefore 0/0.

Two installed-package consumers are present:

1. `libxext_sync_value_contract` exercises all 16 public display-independent
   XSync value operations.
2. `libxext_registry_contract` validates extension registry allocation and
   destruction plus the public error-handler round-trip.

Both consumers emit one unique `LIBXEXT_TEST ... PASS` terminal only after
all internal assertions succeed, so W3 can mechanically prove the `2/2`
denominator without counting compiler output or repeated build variants.

The historical r27 snapshot completed both consumers in the normal recipe
build and the forced-static replay (`2/2` in each variant). Successors r28,
r29, and r37 also passed both variants; later metadata and mainline merges made
their trees historical, so none can be reused as final-candidate W3. The r37
device verifier recorded FAIL only because a BOM-less PowerShell generator
corrupted its Chinese Python sentinel literals before transfer. A create-new
local readback consumed the immutable 148,011-byte collected archive directly,
verified SHA256
`55c92e7f6a0015044b8debdf0bcc7c21b641d1de05f53c84c3fee0f3a2f9be8d`,
and classified the official W3 substep as PASS while preserving aggregate
`finish_rc=1`, `PARTIAL_POST_W3`, and the exact later set `step5b,step8`.
That readback is under
`E:\HarmonyPC\validation\libxext-1.3.7\w3-current-main-20260820-r38-readback`
and explicitly does not satisfy a later candidate tree.

## Evidence boundary

The committed `built` status means the recipe build and substantive consumers
have been validated; it does not mean the package is published, the aggregate
finish command is fully successful, or the PR is submitted. The authoritative
W0, W3, W4, Pre-PR, CI, review, and publication results remain external
immutable evidence and must all bind the final candidate tree. W3 must be
classified separately from later full-finish readiness stages without
rewriting their status. r20 through r23, r25 through r29, and r33 through r37
are consumed; r24 remains a distinct zero-launch transport attempt.
