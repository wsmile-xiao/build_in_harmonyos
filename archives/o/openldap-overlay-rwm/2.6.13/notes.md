# openldap-overlay-rwm 2.6.13 HarmonyOS pre-adaptation

## Scope

This archive builds the OpenLDAP rewrite/remap overlay from the official
OpenLDAP 2.6.13 release. The target artifact is the dynamically loaded
`rwm.so` slapd module. A minimal, ABI-matched slapd host and the OpenLDAP
shared libraries are retained privately so the module can be tested without
pulling unrelated OpenLDAP backend packages into this issue.

Client commands and administrator command symlinks are removed during
packaging. The only enabled backend is `null`, used by the configuration
smoke test and retained in the package's private host. The LDAP proxy and
relay backends plus the syncprov overlay are built from the same source tree
only to execute upstream rwm integration tests; their module artifacts are
removed before packaging. MDB and unrelated backends/overlays remain disabled.

## Source and build system

- Upstream: https://www.openldap.org/
- Release archive: `openldap-2.6.13.tgz`
- SHA-256: `d693b49517a42efb85a1a364a310aed16a53d428d1b46c0d31ef3fba78fcb656`
- Build system: Autotools with a release-provided `configure`
- Rwm sources: `rwm.c`, `rwmconf.c`, `rwmdn.c`, and `rwmmap.c`
- Required switches: `--enable-modules=yes --enable-rwm=mod`

The official tarball and hash were downloaded and verified locally on
2026-08-11. The source tree contains the expected rwm module make rule and
the `slapo-rwm(5)` manual.

## W0 dependencies

The only Conan dependency retained by the minimal build is
`libtool/2.5.4`, which supplies `ltdl.h` and `libltdl` for slapd's dynamic
module loader. A temporary isolated Conan 2.31.2 client successfully
downloaded its recipe from `ohpcd` on 2026-08-11. The published recipe
revision is `fe9f8e735ad45469571cf4de3ce552f4`.

The following upstream-recommended features are optional for rwm and are
disabled: Cyrus SASL, TLS, libevent/lloadd, argon2, LMDB, systemd, and
fetch(3). No dependency recipe is added or modified in this PR.

The W0 command used was:

```sh
conan download "libtool/2.5.4" -r=ohpcd --only-recipe
```

W0 passed. No dependency adaptation is included in issue 2044.

## HarmonyOS handling

- Build and host use the native `aarch64-unknown-linux-ohos` triplet to avoid
  an unsupported HarmonyOS `config.guess` result.
- OHOS configure probes the native `/data/storage/el2/base/cache` root first,
  then a caller-provided `TMPDIR`, and finally a build-local fallback. The
  selected root receives a unique child directory after a
  create/write/remove probe. This order remains stable when a Conan worker
  rewrites `TMPDIR` to HMDFS-backed user storage before calling the recipe.
- Release-provided shell helpers are invoked through `CONFIG_SHELL` or
  `$(SHELL)` because HMDFS does not preserve their executable behavior.
- Patch 0001 accepts the OHOS config.sub triplet, uses `/bin/install` so
  libtool receives a single executable installer, and removes the
  `umask 077` wrapper from the generated `config.status` scratch directory.
- The recipe changes the liblunicode `.links` rule to copy its seven sources
  into the out-of-source build directory because HMDFS rejects the upstream
  symbolic links. A strict Conan text replacement avoids patch-tool temporary
  rename behavior on that directory.
- The libtool package directory is added to `LD_LIBRARY_PATH` while configure
  runs its native conftest programs.
- Builds use `-j1` to avoid HMDFS jobserver FIFO failures.
- Upstream test scripts, generated target programs, and helper scripts are
  invoked through `CONFIG_SHELL`; their test state uses `umask 007` because
  HMDFS ownership mapping made upstream's `umask 077` directories inaccessible
  to subsequent target processes.
- Service-test storage is selected by capability. The recipe probes both
  ordinary file I/O and `mkfifo` in an isolated child directory. HMDFS-backed
  user storage passed file I/O but rejected FIFOs, while
  `/data/storage/el2/base/cache` passed both and was used by the final run.

## Tests

Upstream has eight directly identified rwm integration/regression entries.
All eight now run from the recipe after the target build:

- `test028-idassert`;
- `test030-relay`;
- `test039-glue-ldap-concurrency`;
- `test047-ldap`;
- `test079-proxy-timeout`;
- `test087-librewrite`;
- `test088-syncprov-glue-rwm`;
- `its9468`.

The tests use target `slapd` and client programs, unique listener port blocks,
isolated FIFO-capable state, and the original upstream terminal success marker.
`test030-relay` additionally must report both `Using relay backend` and
`Using ldap backend`, preventing a false pass that skips either path. The
LDAP, relay, and syncprov modules required by these entries are test-only
same-source fixtures. Package inspection after the final build confirmed that
none of them remained under `libexec/openldap`; only `rwm.la` and `rwm.so*`
were present.

The test_package is not a file-only check. It locates the installed rwm
module and packaged `core.schema`, generates a slapd configuration using
`overlay rwm` and `rwm-suffixmassage`, then runs the packaged private host as:

```sh
slapd -Tt -f slapd-rwm.conf
```

Success proves that libltdl can load the module, rwm initialization completes,
and the rwm-specific configuration directives are accepted.

This reusable validation pattern is proposed as knowledge draft E319. It
covers module packages with no standalone consumer API: keep a minimal host
from the same build graph as a private artifact, generate configuration from
package-relative paths, run the host's validation-only mode, and require a
destructive missing-artifact run to fail. It also captures the complementary
upstream-test pattern learned here: build same-source fixtures only for the
test phase, execute real upstream entries, strip fixtures before packaging,
and choose service-test storage by probing required filesystem capabilities
instead of writability alone. The draft is stored in
`knowledge/drafts/E319-draft-openldap-overlay-rwm.{kv,md}` for maintainer
review; no formal graph entry or index is modified by this PR.

The core schema include is required before a suffix containing `dc=` can be
parsed. An earlier diagnostic config omitted it and failed with an invalid DN
syntax error before the rwm module was exercised. Adding the packaged
`core.schema` made the baseline, module-only, overlay, and suffix-massage
configurations all pass `slapd -Tt` on the device.

## Validation

Completed locally:

- issue/branch/worktree isolation checked;
- official source URL, size, SHA-256, and source layout checked;
- configure options, module install rule, dependency checks, and upstream rwm
  test inventory inspected;
- `libtool/2.5.4` recipe downloaded anonymously from `ohpcd`;
- Python syntax compilation and strict PyYAML parsing passed;
- `conan inspect`, `conan export`, and an offline dependency graph passed;
- dependency graph confirmed `libtool` is enabled for headers, libraries, and
  runtime (`HEADERS=True`, `LIBS=True`, `RUN=True`);
- patch dry-run passed against the official extracted source;
- isolated `conan source` passed download, hash verification, extraction, and
  patch application, and the expected rwm source files were present.

Completed on the aarch64 HarmonyOS device in the isolated issue 2044 job:

- cached-source diagnostic build passed `configure`, `make depend`, and
  `make -j1` in runner
  `codex-openldap-overlay-rwm-diagnose-build-r3j-20260811-210045-22764`;
- isolated `DESTDIR` installation passed in runner task
  `diagnose-install-r3p` (exit 0, 281.7 seconds including lock wait);
- target files transferred to the isolated repository were checked against
  all nine local SHA-256 values.
- a four-level diagnostic run passed the base null backend, rwm module load,
  `overlay rwm`, and `rwm-suffixmassage` configurations (all returned 0);
- formal single-package Shadow CI passed in runner
  `codex-openldap-overlay-rwm-shadow-ci-r12-20260812-134410-53615`
  (runner exit 0, about 662 seconds including lock wait);
- Shadow CI results were L0 pass, L1 pass, L2 skip (no public `bin/` by
  design), L4 pass, and L5 pass; the build summary was one success and zero
  failures;
- the destructive negative test passed, confirming that test_package really
  depends on the packaged artifacts.
- fresh-build Shadow CI runner
  `codex-openldap-overlay-rwm-issue-2044-r16i-final-upstream-tests-20260812-190906-919`
  executed all eight selected upstream rwm entries in one clean Conan build;
  every entry printed the upstream `>>>>> Test succeeded` terminal marker;
- the same r16i run then packaged only `rwm.so*`/`rwm.la` in the module
  directory and passed the private-host `test_package`;
- r16i reported L0 pass, L1 pass, L2 skip (no public `bin/` by design), L4
  pass, L5 pass, one package success, zero failures, and runner exit code 0;
  its upstream pass rate was 100% (8/8).

The successful single-package Shadow CI was run from the isolated job as:

```sh
. "$HOME/ohos-users/codex/openldap-overlay-rwm-2.6.13-2044-20260811/env.sh"
export CONAN_HOME="$OHOS_JOB_BASE/conan-home-r16i-final-upstream-tests"
cd "$CI_REPO_ROOT"
export CI_SHADOW_ROOT="$OHOS_JOB_BASE/ohpc-ci-shadow"
zsh ci/conan/setup.sh
zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

On a shared device, wrap that command with `$HOME/bin/ohos-test-runner.sh`
in heavy mode and keep the global lock enabled. Before rerunning in the same
isolated repository, restore `conandata.yml` from the worktree: the CI
pre-download step intentionally rewrites its source URL to a run-local
`file://` cache path.

## PR CI source fallback

PR CI build 21117 failed before compilation because its worker could not
connect to `www.openldap.org`. The failure did not indicate a recipe, build,
or test regression: L0 passed, `libtool/2.5.4` was resolved, and Conan stopped
only while downloading the source archive.

Two HTTPS fallbacks were added ahead of the upstream URL:

- OSU Open Source Lab's BLFS mirror;
- the Savoir-faire Linux mirror listed by OpenLDAP.

Both fallbacks returned HTTP 200, were 6,525,768 bytes, and were downloaded
locally on 2026-08-12. Each produced the same SHA-256 as the upstream release,
`d693b49517a42efb85a1a364a310aed16a53d428d1b46c0d31ef3fba78fcb656`.
The original OpenLDAP URL remains the final candidate. Hyphens in the URL
paths use their equivalent `%2D` encoding so the repository's pre-download
URL extractor does not truncate the paths. A device-side HEAD probe was
attempted, but the SSH connection was reset during key exchange; the mirror
content verification itself completed locally.

PR CI build 21234 confirmed that the source fallback works: Conan downloaded
the archive from the OSU URL, verified and unpacked it, and applied the
portability patch. Its fresh build then failed at configure's first compiler
conftest. The CI worker supplied `TMPDIR=/data/storage/el2/base/cache`, but the
recipe had replaced it with an `_tmp` directory under the HMDFS-backed Conan
build folder. The common HarmonyOS guidance and knowledge entry E112 identifies
this as an unsafe location for configure scratch files.

The recipe now tries the native OHOS cache before a caller-provided temporary
root, requires a real create/write/remove probe, creates a private unique
subdirectory below the selected root, and only then falls back to build-local
`_tmp`.
A minimal device clang link test passed with an explicit writable temporary
directory. Configure failures also print the final 200 lines of `config.log`
so future CI failures retain the compiler's underlying diagnostic without
flooding the job log. Knowledge entry E112 was applied and is recorded in
`manifest.yaml`; the separate E319 draft captures the private-host module
validation pattern learned from this package.

The fix was verified from a fresh `openldap-overlay-rwm` package build on the
aarch64 HarmonyOS device in runner
`codex-openldap-overlay-rwm-shadow-ci-r15-tmpfix-20260812-154443-56733`.
The recipe selected
`/data/storage/el2/base/cache/openldap-overlay-rwm-6zpojd31`, configure reported
`checking whether the C compiler works... yes`, and the full source build,
package installation, and test_package completed successfully. The packaged
slapd host loaded `rwm.so` and accepted the rwm configuration. Shadow CI
reported L0/L1/L4/L5 pass, L2 skip (no public `bin/` by design), one success,
zero failures, and runner exit code 0.

After the high-difficulty evidence-only update, PR CI build 22131 exposed a
second form of the same boundary: its outer job environment advertised the
native cache, while the Conan recipe observed
`/storage/Users/currentUser/tmp`. The recipe now makes the native cache the
first OHOS configure candidate, followed by the inherited root and the
build-local fallback. This prevents a child-process environment rewrite from
moving configure scratch files back to HMDFS-backed user storage.

PR CI build 22141, queued before that fix was pushed, passed the package build,
upstream tests, `test_package`, L0/L1, and cleanup on worker CI-042. It confirms
that the high-difficulty evidence files themselves pass repository gates, but
its 22:06 start predates the 22:25 push of `ce8ab7582735d8f477b8c75e8e66ffee2db21b46`,
so it is not claimed as validation of the explicit OHOS-first temp-root fix.

## Upstream test review resolution

PR review identified that inventorying eight upstream rwm entries while
executing zero was not acceptable. Building the entire OpenLDAP product was
unnecessary, but the directly relevant entries needed the LDAP and relay
backends plus syncprov. The recipe now enables those three modules only as
same-source test fixtures and enables upstream's default cleartext support for
the bundled test identities. This adds no Conan dependency and does not expand
the final package contract because all three fixture modules are removed after
installation.

Initial target diagnostics found three HarmonyOS harness portability issues,
without changing upstream test semantics:

- HMDFS does not preserve direct execution behavior for copied shell scripts
  and generated target helper programs, so entry points run through
  `CONFIG_SHELL`;
- upstream `umask 077` produced private directories that later target
  processes could not traverse under the device's ownership mapping, so test
  state uses group-private `umask 007`;
- HMDFS-backed user storage rejects `mkfifo`, required by proxy timeout tests,
  so the recipe uses an isolated directory only after file-I/O and FIFO probes
  both succeed.

After these harness adaptations, the final clean r16i Shadow CI executed and
passed all eight entries in a single build, then passed `test_package`. The
tests themselves and their assertions were not replaced; the recipe only
adapts how their scripts, target helpers, permissions, and temporary storage
are launched on HarmonyOS.

## Path C high-difficulty candidate

This archive is submitted as a Path C high-difficulty candidate, not as an
already approved Path C result. Final classification, acceptance, and scoring
remain subject to official review.

The candidate basis is the combined target-side work rather than ordinary
compile complexity: eight rwm integration entries require multiple real LDAP
daemons, network listeners, concurrency/timeout helpers, and same-source
backend modules; HMDFS supports ordinary file I/O but rejects the FIFO needed
by the daemon harness; copied scripts and target helpers need shell-mediated
execution; and test fixtures must share the rwm ABI without becoming part of
the final package contract.

The final solution executes all eight original upstream entries on the target,
requires their terminal success markers, separately validates the packaged
module through an ABI-matched private host, and removes LDAP/relay/syncprov
fixtures before packaging. Fresh r16i Shadow CI and AtomGit CI build 21811 both
passed. The detailed failure evolution, package boundaries, results, and
reproduction command are recorded in
`reports/high-difficulty-evidence.md`.
