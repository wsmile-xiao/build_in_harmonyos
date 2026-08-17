# MPICH 5.0.1.2 adaptation notes

## Scope

`mpich/5.0.1.2` is an OpenHarmony PC recipe revision of the official stable
MPICH 5.0.1 source. The merged `mpich/5.0.1` package proves two-rank C MPI on
the target but was configured with `--disable-fortran`. This revision keeps
the proven `ch3:sock` transport while using Hydra's complete local process
manager and adding one coherent C and LLVM Flang Fortran ABI for ScaLAPACK and
other HPC consumers.

The contributor dependency row is assigned to account `2301_80739235`, branch
`feat/mpich-5.0.1.2`, activity `开源鸿蒙PC专项积分赛-依赖`, with automatic release
time `08/23 05:02`.

## Official source and version

- Official release: `v5.0.1`, published as a non-prerelease GitHub Release.
- Release asset size: `37,688,810` bytes.
- SHA-256: `8c1832a13ddacf071685069f5fadfd1f2877a29e1a628652892c65211b1f3327`.
- The initial local download was truncated at `32,728,896` bytes and rejected
  after full archive traversal returned nonzero. It was replaced only after
  the official asset size and digest matched and full traversal returned zero.

## W0 dependency closure

Historical 5.0.1.1 Conan home, retained for provenance only and not reused by
this revision:
`E:/HarmonyPC/conan-homes/mpich-5.0.1.1-w0-r2-post-rebase`.

Both host and build profiles are the repository OHOS 6.0/armv8 profile. The
commands used `--build=never`, `tools.build:jobs=1`, and remote `ohpcd`; no
`conan list` or source fallback was used.

- `flang-ohos/20.1.0` resolved recipe
  `ef1e4e5bb35d3d6055bdc9ed6b26479c`, package
  `fc3eeb021243959114a0318489539cad6d087e28`, revision
  `a8a56b86e272e0f0232a2cd9a747e349`.
- `perl/5.42.2` resolved recipe
  `13c4f5bde5668df0b7268c4d0c01073c`, package
  `6b129b068851896169fae42d399fa922d239ce8a`, revision
  `ec97109d67c453b723126b261da3fd9e`.

## ABI design

- Flang is a `tool_requires` dependency with `package_id_mode="full_mode"`, so
  changing the compiler recipe or binary changes the MPICH package identity.
- A consumer that compiles Fortran must select the same
  `flang-ohos/20.1.0` tool requirement with `full_mode`; the compiler executable
  is intentionally not bundled as a host library. The test package models that
  downstream contract explicitly. C-only consumers do not acquire a compiler
  they never invoke, while `mpifort` fails closed if the declared compiler is
  absent from the build environment.
- MPICH builds `mpif.h`, `mpi.mod`, `libmpifort`, `mpifort`, `mpif77`, and
  `mpif90` together with `libmpi`, `mpicc`, and `mpiexec`.
- Hydra is required rather than `gforker`: the official abort and dynamic
  process tests require `-disable-auto-cleanup` plus PMI publish, lookup, and
  unpublish commands. The package includes `mpiexec.hydra` and
  `hydra_pmi_proxy`, and relocation tests exercise the Hydra option from both
  prefixes.
- HMDFS rejects install-time symbolic-link aliases. The recipe verifies and
  replaces exactly 11 top-level MPICH aliases and Hydra's 2 nested
  `mpiexec`/`mpirun` aliases with byte copies before either install. The r13
  fresh run proved the nested Hydra aliases are a separate build-system path:
  leaving them unchanged fails with `Permission denied` before upstream tests.
- The upstream test configure must select the installed `mpicc` and `mpifort`
  wrappers. An earlier fresh run proved that forwarding the main build's
  command-line `CC`/`FC`/`F77` variables through `make testing` overrides those
  wrapper choices: `util/run_mpitests.c` then cannot find `mpi.h`, and Fortran
  tests would likewise bypass the packaged module and runtime contract. Build
  and install keep explicit compiler variables; the test phase deliberately
  omits them and resolves all language drivers from the same installed prefix.
  The r15 fresh run then proved that the target shell contract is independent:
  omitting `SHELL` and `CONFIG_SHELL` from the same command made the nested MPI
  test configure fail with `working directory cannot be determined` before it
  could select wrappers. Its runner log SHA-256 is
  `5936277c731c995f419558f5388d981db2fd45c010957cd429be29d4c2ca5859` and
  Conan JSON SHA-256 is
  `a8430103c400205324e4b900d211f8af7cd62a4763e5216fac3b6cbc9a47c31e`.
  The closed command contract therefore keeps only target `SHELL`,
  `CONFIG_SHELL`, and `MKDIR_P` assignments while rejecting language compiler
  assignments, missing values, wrong values, and duplicate overrides.
- `mpi_f08` is deliberately disabled. MPICH's probe requires
  `ISO_Fortran_binding.h`, which is absent from both `flang-ohos/20.1.0` and
  the matching OHOS SDK. The package does not claim an unverified F08 ABI.
- ROMIO is enabled for the official inventory. Its architecture fallback now
  invokes `util/tarch` through the target POSIX shell only when `ARCH` is empty,
  preserving an explicit caller-selected architecture in both `configure.ac`
  and generated `configure`.
- The official 5.0.1 release archive contains only `mpi.f90`; it does not
  contain the `mpi_base.f90` file tested by the no-Python configure branch.
  Configure therefore receives the exact Python 3 interpreter already running
  Conan, with PATH discovery, `PYTHONPATH`/`PYTHONHOME`, user-site imports, and
  bytecode writes disabled.
  The recipe pins the release F90 inventory, requires all four generated F90
  files as nonempty regular files, checks the exact generator command in
  `config.status`, and rechecks source and generated hashes after `make`.
- The exact Flang runtime archives are copied under `lib/flang-runtime` and
  referenced relative to the installed wrapper location. Because those LLVM
  archives are redistributed rather than only linked as an external package,
  the recipe also downloads the official LLVM 20.1.0 `LICENSE.TXT` by pinned
  SHA-256 and installs it beside MPICH's `COPYRIGHT`; both files are mandatory
  package artifacts, and the consumer verifies the exact LLVM license digest.
- Wrapper compilers are command names (`clang`, `flang`) rather than Conan
  cache paths. Package-time checks reject source, build, package-cache,
  `.conan2`, and historical `/storage/Users/currentUser/usr/local` paths.
- Upstream test setup resolves `env` and `make` through Conan's
  controlled tool contracts. Target bootstrap r20 reached the completed install
  and then proved that the recipe process PATH alone could not see the
  build-environment `make`; it is now resolved through `VirtualBuildEnv`,
  matching the standard build commands. Bootstrap r21 then proved that the
  recipe process PATH is not required to expose the clean-environment launcher,
  so that launcher is fixed and validated as executable `/system/bin/env`.
  The directed gate covers both resolutions, restores ambient PATH twice, and
  rejects both missing-tool classes.
- The r52 device run completed the full upstream suite and created the MPICH
  package, then stopped in `test_package.build()` because the closed consumer
  environment tried to resolve bare `clang` and `clang++` only from the Conan
  recipe process's ambient `PATH`. The OHOS profile already binds both tools by
  absolute path in `tools.build:compiler_executables`; buildenv serialization
  does not guarantee that path is applied to the Python recipe process. The
  consumer now requires those two explicit absolute single-executable values,
  verifies that each directory binds the matching bare wrapper name, and adds
  those directories before sanitized ambient entries. Missing, relative,
  multi-token, nonexistent, and mismatched compiler configurations fail closed.
- Conan 2.29.1 `Environment.unset()` serializes an empty value for
  `vars().apply()`; it does not remove the key from Python's `os.environ`.
  Bootstrap r22 exposed that mismatch before the official suite. The launch
  scrubber now removes all 107 override keys transactionally, fixes its minimal
  PATH, and restores the complete prior environment on both normal and
  exceptional exits.
- Bootstrap r23 completed all six wrapper `-show` commands and entered the
  official `make testing` target. The process-token scan then saw target
  `/proc/<pid>/environ` return `EINVAL` and correctly stopped the run. A bounded
  target churn probe reproduced that error only while one identity moved from
  running to zombie. The scanner now skips `EINVAL` only after proving the
  process disappeared, its start time changed, or its current state is zombie;
  a stable non-zombie `EINVAL` remains fatal.
- Bootstrap r26 completed configure, the full MPICH library build, installation,
  and test-tree compilation, then stopped before the official Perl test runner:
  the relocated `perl/5.42.2` ELF retained compile-time `//lib/perl5` entries,
  so `runtests` could not load the package's existing `strict.pm`. The negative
  control fails without `PERL5LIB`; the positive control loads `strict`,
  `warnings`, and `File::Spec` after binding the package's core, architecture,
  and site library directories. The recipe now validates and exports that
  exact closure through the isolated `PERL5LIB` allowlist and scrubs any
  ambient value before each upstream command.
- Conan component keys are `mpich::c` and `mpich::fortran`. Their generated
  targets are `MPI::MPI_C` and `MPI::MPI_Fortran`; downstream recipes must use
  the component keys in `cpp_info.requires`.
- MPI handles, ranks, counts, errors, `MPI_Fint`, and `MPI_INTEGER` remain four
  bytes. This MPI boundary is independent of BLAS/LAPACK integer width.

## Validation contract

The 40 patches are intentionally path-specific: the release archive vendors
18 independent `config.guess`/`config.sub` pairs, the source and generated
forms of the `config.rpath` shell invocation, one generic Hydra lifecycle fix,
and the ROMIO shell/ARCH contract. Keeping one diff per vendored file makes
every archive path explicit and lets Conan reject a missing or changed copy
independently. The current replay closure is stored outside the candidate
metadata under
`validation/mpich-5.0.1.1/patch-replay-r26-offline-remediation` and
must be regenerated after every source or patch change.
Outer-unsafe blank and leading-Tab context was normalized with anchored hunks;
the source and patches contain no conditional-compilation macro whose name
includes `OHOS`.

The prior r19 and r22 replays are retained as historical evidence only. The
current r26 replay under
`validation/mpich-5.0.1.1/patch-replay-r26-offline-remediation` covers 40 patch
files and 43 unique target files and passed 40/40
forward and 40/40 reverse in Git, GNU patch, and patch-ng after the ROMIO ARCH
correction and test-package transaction/race fixes. The Hydra recipe contract
passed its positive check and 12/12
single-fragment deletion mutations; the malformed-abort probe contract passed
its positive check and 21/21 deletion mutations after the PR #5446 High/P1
remediation. The spawn probe now carries one unambiguous
`--spawned=<mode>` argument, reads it from the child process's `argv[1]`, and
rejects empty, extra-argument, or truncated encodings. The production-source
host regression passed 7/7 cases with `-Wall -Wextra -Werror`; result SHA-256
is `3af6ffde8b531d6bc56c3fb16e793c5c9d696800281173031f21eede0de4990e`.

The recipe runs upstream `make -j1 testing`, then parses both official XML and
JUnit outputs because MPICH's Perl runner prints failures without returning a
nonzero process status. The upstream top-level target deliberately sets
`NOXMLCLOSE=YES`; the parser adds the missing root close only in memory and
only when the last `MPITEST` record is complete, while a truncated record is
rejected. It requires 2858 completed raw executions, 1410 logical entries
after folding `(WORKDIR, NAME, ARGS, NP)`, zero failures, and the one
runtime `multinic_infohints` skip retained by XML. JUnit additionally records
30 tests skipped before execution and omitted from XML, for 31 JUnit skips and
2889 testcase elements in total. Skips are reported separately and are not
counted as passed executions. Synthetic negative probes verify that one
injected failure, one missing execution, or an incomplete record is rejected.

The nine consumer flows compile and run C, the MPI C API through both
`mpicxx` and the `mpic++` alias, `mpif.h`, `use mpi`, mixed C/Fortran, and an
NWChem `USE_MPIF4` i8-core/i4-MPI bridge with two ranks. They use `mpif77` and
`mpif90` for their corresponding interfaces, check `-show`, `-compile-info`,
and `-link-info` on all six compiler wrappers, validate the serialized Conan
`c`/`fortran` component contract, exercise both `mpiexec` and `mpirun`, and
repeat the same matrix after copying the package to a new prefix. For the two
CMake flows, the generated CMakeDeps files are transactionally rebound to the
relocated prefix, both consumers are rebuilt with `_relocated` output names,
and the CMake cache/link records must contain the relocated prefix and no
original package path. The mixed test
converts a four-byte Fortran communicator through `MPI_Comm_f2c`, compares rank
and size across both languages, and performs a C `MPI_Allreduce` inside the
Fortran process. The bridge compiles with `-fdefault-integer-8` while keeping
MPI handles, counts, ranks, errors, and reduction values explicitly four-byte.
The closed test environment rejects every foreign MPI wrapper, launcher, and
`libmpi.so*` outside the selected prefix. Destructive tests then hide the
relocated `hydra_pmi_proxy`, all relocated `libmpi.so*` files, and all
relocated `libpmi.so*` files separately, require every run to fail while the
original package remains byte-identical, restore the files, and require fresh
two-rank recovery runs. Package generation also requires each compiler wrapper
to contain exactly one complete build-tree `src/pmi/libpmi.la` token and
rewrites it to package-local `-lpmi`; missing, duplicated, or suffix-extended
tokens are rejected. These internal contract checks and the repeated
relocation executions are not additional independent test cases.

Device r33 closed the official TAP stream at `1..2889` and created the MPICH
package before the clean Git-archive test package exposed a stale layout
assumption: exported test sources live at the test-package root, not in an
untracked `src/` directory. The test package now uses that root source layout;
the directed layout gate proves the clean archive succeeds and the old
`src/`-only lookup fails closed.

Device r34 at HEAD `159f7915b21e08c6f3cc4fa6a2dbb4b59b1bd2ee`
completed the official upstream closure with 2858/2858 raw executions,
1410/1410 logical entries, zero failures, one XML runtime skip, 31 JUnit skips,
and TAP plan `1..2889`. It created package
`mpich/5.0.1.1#8234b351ef64beef666d16e029501e20:783062abfdc1764333d0178d0c88145bad0e32a7#0c7e14e829571e288fd947cd4e2b143b`
before the consumer test failed. Conan presents component `libdirs` to a
consumer as package-rooted absolute paths, while the test compared them
directly with the producer recipe's relative declarations. The component gate
now resolves either representation under the exact dependency package root,
rejects missing or escaping directories, and compares the resulting relative
paths in order. r34 remains a failed W3 because none of the nine consumer flows
ran after that metadata assertion.

Both launch paths replace ambient `HOME` with an empty per-build directory and
select an explicit empty `mpiexec.hydra.conf`. The consumer path also removes
all `MPIR_CVAR_*`, legacy `MPIR_PARAM_*`, `PMI_*`, and `PMIX_*` inputs before
running invalid poison values through the same active path. Managed launchers
start a new process group and pass a random per-run token through the same
`env -i` command that launches make, Hydra, and MPI ranks. Cleanup repeatedly
unions the process tree, the still-owned process group, and exact NUL-delimited
token matches from `/proc/*/environ`; PID start times guard every signal, and a
group signal is allowed only while the original root still owns that PGID.
Normal upstream monitoring samples this union once per second while retaining a
50 ms timeout clock; exit, error, TERM, and KILL paths rescan every 50 ms.
Tree, process-group, and token scanner errors are isolated during cleanup so
the remaining scanners and already-bound identities still reach TERM, KILL,
and reap before the original error receives the cleanup report. A bounded
initial bind accepts a launcher that has already exited only when no
token-bearing descendant remains, avoiding false failures for short wrapper
diagnostic commands.
The consumer creates both TERM-responsive and TERM-ignoring double-forked
`setsid()` descendants and requires token discovery, cleanup, an absent delayed
canary, and a successful recovery run. Timeouts, nonzero exits, residue, and
sampler exceptions all use the same closure path. These are internal isolation
checks, not test cases.

The Hydra abort patch initializes malformed messages to a failure exit code and
strictly validates every supplied integer with an ASCII-only grammar before
`strtol`, including empty, nonnumeric, trailing-junk, out-of-range, and
leading-tab/CR/VT/FF inputs. Raw PMI-v1 parse failures that still begin with
`cmd=abort` now route through the same cleanup function as parsed aborts, so
`exitcode=` with an empty value cannot bypass cleanup in `handle_pmi_cmd()`.
The raw-frame classifier accepts the exact command or an ASCII control/space
separator (`0x00` through `0x20`) and rejects longer command names such as
`cmd=aborted`. Explicit abort never becomes an ordinary success return merely
because automatic cleanup is disabled. Valid and invalid PMI-v1 abort paths
signal every active proxy across all live process groups with `SIGKILL`, wait
for the bootstrap processes, and terminate the launcher; parse, signal, or wait
failures use a failure exit code.

Raw `PMI_FD` probes now record structured `role/rank/pid/pgid` evidence for the
two parent ranks and one spawned rank, and require exactly one observed
`hydra_pmi_proxy` processes. The launcher writes an armed marker before sending
the malformed frame, so a fast `SIGKILL` cannot create a false missing-marker
diagnosis. Invalid modes cover missing, empty, nonnumeric, trailing-junk,
overflow, above-int, below-int, and leading tab/CR/VT/FF `exitcode` tokens
under `-disable-auto-cleanup`; each requires zero residue, no delayed canary,
and a normal recovery launch. Separate valid `INT_MAX` and `INT_MIN` controls
under `-disable-auto-cleanup` require all three recorded ranks to be bound while
live, then require the explicit abort to terminate them before a delayed
survival canary can be written. These probes are internal checks and do not
change the nine consumer-test flows.

The ordinary abort and timeout cases also require launcher cleanup. On an outer
timeout, the harness checks all bound process identities before invoking its
fallback cleanup and fails if any Hydra-managed process is still alive. The
exception path then performs the bounded cleanup only to leave the machine
safe; it cannot convert the failed Hydra-cleanup assertion into a passing test.

The r34 upstream counts are current real-device evidence, but target consumer
counts remain pending until one later exact-HEAD device run completes every
consumer flow. The upstream-only result and the earlier C-only package are not
full W3 evidence.

## r62/r64 detached-descendant failures and r65 successor

The exact r62 W3 completed the upstream MPICH suite with 1410/1410 logical
entries and 2858/2858 raw executions before Conan returned RC 6 in the
`test_process_control detach` consumer probe. The managed runner reached its
15-second outer timeout, performed cleanup, asserted zero residue, and then
raised `managed MPI command exceeded 15 seconds`. The outer
`_expect_detached_descendant_cleanup` helper accepted only the alternative
`returned while descendants were still alive` diagnostic, so it rejected the
already-cleaned timeout before checking escape PID and delayed-canary evidence.

r62 remains an immutable W3 failure. Its frozen failure readback bound terminal
FAIL, runner PID/starttime 47851/42171234, Conan/wrapper RC 6/6, and tar SHA-256
`53a0910861275ca210457922f51e12eeb55baae82ce0d10e27c1b3dee04405b1`.
Certified release, postrelease root/unreadable 0/0, two clean scans, absent
lock/lease, sidecar deletion and atomic ledger release all passed.

The r63 successor kept the 15-second budget and accepted the exact timeout only
after zero-residue cleanup. Its local 10/10 matrix missed a timing contradiction:
the child wrote its canary four seconds after startup, but timeout cleanup could
not begin until 15 seconds. Exact r64 W3 therefore failed with `detached MPI
descendant wrote delayed canary for detach`; its Conan RC 6 evidence was
preserved, and certified release/postrelease again proved root/unreadable 0/0,
two clean scans, and absent lock/lease.

The r65 successor replaces the startup-relative timer with a 64-hex-token
one-shot gate. The child writes an armed token and waits. After the exact
returned-live or parsed timeout path has completed zero-residue cleanup, the
host requires the escape PID to be absent, publishes the token with create-new
and fsync semantics, and rejects any canary before or during a five-second
post-gate window. Timeout commands are parsed with `ast.literal_eval`, so
`detach` cannot match `detach-kill` by substring. The production-path matrix
passes 15/15; the actual C gate compiles under C17 with all warnings fatal and
passes 5/5 alive/killed/token/create-new runtime cases. This local closure does
not replace the required fresh exact-snapshot W3.

The production upstream summary now emits explicit `logical PASS` and
`raw PASS` tokens after its existing XML/JUnit zero-failure and inventory
digest gates. This keeps all counts and skip accounting unchanged while making
the genuine full-run terminal directly consumable by the blocking pre-PR
contract.

Device r36 used the same producer recipe revision and frozen input as r35. It
completed all 2858 raw executions and 1410 logical entries, but one four-rank
`coll/allredmany` collalgo case timed out after 180 seconds. Its derived result
was 2857 raw and 1409 logical passes with one raw/logical failure; JUnit
independently recorded 2858 tests, one failure, zero errors, and 31 skips.
r36 is not valid W3 evidence because Alberta and adwaita-qt work overlapped its
device lease. r35 was also explicitly parallel and timed out in five different
`allredmany` configurations plus one `reduce` configuration, while r34 ran the
same producer recipe through the complete upstream inventory with zero
failures. The changing timeout set under contaminated execution does not
justify changing MPICH algorithms, collalgo inputs, or the 180-second per-test
limit; a new exclusive-device run remains required.

The r36 timeout exposed a separate deterministic report-writer defect in the
official Perl `runtests`: when grouped `run_mpitests` exits unexpectedly, the
branch writes `RunTestFailed(...)` and immediately leaves the loop before the
shared `RunPostMsg(...)` call. The resulting XML omits `</MPITEST>` for the
failed record. The existing parser intentionally adds only the missing root
close used by `NOXMLCLOSE=YES`, so it rejected the malformed report before it
could surface the real test failure. The copied upstream runner is now changed
by one exact guarded replacement that calls `RunPostMsg($test_opt)` before that
`last`. An embedded contract checks the positive post-image and rejects a
missing source fragment, duplicate fragment, or already-rewritten fragment.
The original r36 XML remains immutable external evidence.

The exclusive r37 run closed the failed XML record but stopped at a different
collective entry: `allred6` record 340, four ranks.  Its requested
`tree/knomial_2/K=4/chunk=4096` setting is not an algorithm discriminator for
this test because `allred6` creates a non-commutative MPI operation and MPICH
therefore falls back from `knomial_2` to `knomial_1`; the immediately preceding
`knomial_1` case passed.  The reported current-case runtime was only 0.024
seconds when Hydra emitted `APPLICATION TIMED OUT, TIMEOUT = 180s`.  The older
r36 run stopped at `allredmany` record 411 after 2.552 seconds, confirming that
the failure position moved with accumulated group runtime rather than one
collective algorithm.

The recipe had incorrectly exported `MPIEXEC_TIMEOUT=180` before launching the
official grouped `run_mpitests` process.  Hydra applied that value to the whole
group, even though the official harness already sends each test's timeout to
`multi_tests.c`, which enforces it with `alarm()`.  The isolated environment now
exports `MPITEST_TIMEOUT=180` instead.  This retains the official per-test limit
for grouped and individual execution without imposing a 180-second lifetime on
the entire group.  Embedded guards bind the upstream grouped-launch, per-test
`TIMEOUT`, individual `MPIEXEC_TIMEOUT`, and `alarm()` paths and reject missing
fragments, a missing or invalid per-test value, a reintroduced group timeout,
and forced individual execution.  The preserved r36 and r37 reports remain
failure evidence and are not rewritten or promoted to W3 passes.

The first real per-test-timeout run, r44/v14 on `10.62.148.108`, completed
2888 of 2889 TAP entries and timed out only `rma/atomic_rmw_gacc` at
180.309 seconds. TAP, JUnit, and XML agree, so this is not a report-writer
classification error. Seven preserved earlier device runs completed the same
test in 104.800 to 167.996 seconds; the previous maximum left only 6.7 percent
headroom under the upstream default. The r44 timeout record also captured a
load average near 20 on a 20-CPU device.

This case is materially heavier than its neighbors: the unchanged source runs
the test twice, with 15 loops over four datatype modes, for 1,201,200
`MPI_Get_accumulate` plus flush pairs and roughly 120 million result
comparisons. Patch 0041 assigns only this entry the already-used 300-second
atomic-test budget. It does not reduce loops, buffer counts, rank count, or
coverage, and it leaves the global 180-second default intact. The production
recipe binds the exact testlist entry and workload constants/call counts, then
rejects missing, duplicate, 180-second, 600-second, and workload-reduction
mutations. The r44 FAIL remains immutable and a later passing exact-case device
run is still required; the larger budget is not itself a W3 pass.

The complete 41-patch set was replayed forward and reverse with GNU patch,
Git, and the Conan 2.29.1 `patch_ng` provider. All six paths completed 41/41,
the three forward trees were byte-identical, and every reverse tree matched
the 16,665-entry official archive manifest. The style-corrected r28 replay
result SHA256 is
`74e379ff32617a87e1764561cfa1050f4ba350ba3ffa915244036b63c2a8f802`;
it binds conandata SHA256 `dc86d5306881fc10e94c3b79fe91ebb50c53dede6116bb5bfb6278d45522f62c`
and patch manifest SHA256
`c6d20bc5c4c48814a2be1dfc88b42853d7ca310875db5fd564bb1f0a12faf1d1`.

The exclusive r47 run on `10.62.148.108` proved the previously failing heavy
case itself: `rma/atomic_rmw_gacc` completed with three ranks in 195.006
seconds. The complete TAP report contains 2,620 `ok` records, zero `not ok`,
and plan `1..2620`; JUnit independently contains 2,620 cases, zero failures,
zero errors, and 31 skips. This is target evidence for the case, but r47 is not
a W3 pass. After the test command completed, the run-token residue scanner read
`/proc/12351/environ` during an exit race and HarmonyOS returned `EINVAL` while
the immediate stat reread still reported the same non-zombie identity. Conan
therefore correctly failed closed with RC 6.

The scanner now gives only `EINVAL` a 250 ms bounded reconciliation window. It
retries the environment read every 10 ms while rechecking process start time
and state; disappearance, PID reuse, or zombie transition are accepted as an
exit race, and a later successful read is checked normally. A stable same-start
non-zombie `EINVAL` remains fatal, as does every unrelated error. Directed
tests cover transient recovery, disappearance, PID reuse, zombie state, stable
`EINVAL`, and unrelated `EIO`. The r47 FAIL and its raw reports remain immutable
historical evidence, and a later newly frozen candidate still needs one full
authorized W3 before push or PR.

The exclusive r48 run completed the full upstream TAP plan `1..2889` with zero
`not ok` records, including every four-rank and seven-rank `coll/allred6` case.
It is nevertheless a W3 failure: Conan returned 1 while the test package built
its topology-negative fixtures because HarmonyOS rejected `os.symlink()` with
`EACCES`. The fixture capability gate had handled `EPERM`, `ENOSYS`, and
`ENOTSUP`, but not `EACCES`. It now treats only the explicit link capability or
policy errors `EACCES`, `EPERM`, `ENOSYS`, `ENOTSUP`, and `EOPNOTSUPP` as an
unavailable fixture. When links are supported, the absolute escape, relative
escape, cycle, valid internal link, external hardlink, and internal hardlink
checks still run unchanged; every unrelated error remains fatal. Directed
production-path tests cover a supported filesystem, each allowed errno for
both symlink and hardlink creation, and unexpected `ENOENT` propagation. The
r48 raw failure, missing Conan JSON output, terminal, and release evidence stay
immutable and are not promoted to a W3 pass.

The exclusive r57 run at HEAD
`803f9c7b85df8156deee10ab2dcff09fae29b65d` again completed the full
upstream TAP plan `1..2889` with zero `not ok` records. It then failed the
first malformed PMI abort consumer probe with Conan RC 6:
`controlled MPI malformed-missing probe observed 1 Hydra proxies`. The probe
had already recorded and bound all three expected parent/spawned
role/rank/PID/PGID records, and the managed runner reached two empty cleanup
scans with no task process, lock, or lease residue. The failure was therefore
in the pre-fault topology observation contract, not the upstream suite, XML
reporter, or post-fault Hydra cleanup. The fixed one-second delay before the
raw abort frame did not synchronize with the comparatively expensive
HarmonyOS `/proc` scans, so the second short-lived proxy could escape the
host sampling history even though its spawned rank was recorded.

The successor probe replaces that timing assumption with a token-bound
observer-release gate. All malformed parent and spawned ranks wait without
sending the frame or starting their delayed-canary clock. The harness publishes
the exact 64-hex token through create-new binary I/O only after it has bound all
three still-live role/rank/PID/PGID records and exactly two still-live
`hydra_pmi_proxy` processes. Empty or partial bytes keep waiting; a stable
wrong token, CRLF, missing role, PGID drift, one proxy, or duplicate role never
authorizes the frame. Local production-path validation passed all seven
positive/negative publication cases, all 17 single-fragment probe mutations,
five C release-file cases, Python compilation, C11 `-Werror` syntax, and clean
diff checks. These local checks do not promote r57: its immutable fallback tar
SHA256 is
`0e5c901ba247d075602dd6a0cd41aceea5d7ddd01968421610879180e8548df1`,
its clean-release result SHA256 is
`8c761ea0cfed84cf2511ff117b93c59a1c9102344dceb99621cf1606bba6cca4`,
and a fresh successor still needs the complete exact-snapshot device W3.

The current-HEAD Review raised two source-visibility P1 findings. The Hydra
cleanup call is valid: official MPICH 5.0.1 declares `PMISERV_pg_max_id()` in
`hydra_server.h` and defines it in `pg.c`; the patch now states that ownership
at the call site, and the recipe mechanically requires the declaration and
definition after patch application. The PMI spawn probe still passes exactly
one bounded `--spawned=<mode>` command argument, but now names the array
`spawn_arguments`, documents that `command` is separate, and explicitly
accepts the launcher's literal `argv[0]` projection without weakening empty,
extra-argument, or truncation rejection. On the official tarball SHA256
`8c1832a13ddacf071685069f5fadfd1f2877a29e1a628652892c65211b1f3327`,
the complete patch series passed 41/41 forward and 41/41 reverse checks with
`core.autocrlf=false`, and all 44 touched files returned byte-identical to a
fresh extraction; the host contract passed 7 parser cases, 13 mode round
trips, one truncation case, 25/25 fragment
deletion mutations, and 3/3 registry bindings with 3/3 negative removals.
Python compilation, Ruff, `git diff --check`, and LF checks also passed. These
are local source-contract checks and do not replace exact-current-HEAD CI or a
fresh Review; no device run was repeated.

Buildbot builder 1 / build 26404 then exposed a stale valid-abort test oracle.
The production fix correctly terminates a valid PMI abort even when automatic
cleanup is disabled, so `valid-int-max` returned nonzero after cleaning the
launcher; the old test still required a zero return and survival canaries.
The successor oracle now requires managed launcher cleanup, binds the three
live parent/spawned role-rank/PID/PGID records and one Hydra proxy, rejects PMI
parser diagnostics, requires exact armed evidence, forbids a delayed survival
canary, and follows with an ordinary MPI smoke launch. The directed validator
passed 2 production modes, 4 negatives, 26 single-fragment mutations, and C11
`-Wall -Wextra -Werror`; result SHA256 is
`93df84e25ade8b321a7588a2c045b101f85a950824e29218eda2fbbcb02403b6`.
The full 41-patch set passed forward and reverse replay through Git, GNU patch
2.7.6, and patch_ng with identical forward trees and byte-identical pristine
reverse trees; replay result SHA256 is
`72518c0a6415cca359b8783297abcc52ba91107fc2d92ec56df2bf7ed9eb2c9f`.
