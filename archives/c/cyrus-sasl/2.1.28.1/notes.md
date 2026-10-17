# cyrus-sasl 2.1.28.1 adaptation notes

This is a recipe revision for the upstream Cyrus SASL 2.1.28 release.

## Source

- Official release tarball:
  `https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz`
- SHA256:
  `7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c`

## Dependency decisions

- The first pass keeps the core `libsasl2` library self-contained.
- `saslauthd`, `pwcheck`, authdaemon, PAM, LDAP, SQL, Berkeley DB/GDBM,
  Kerberos/GSSAPI, OPIE, DES, OpenSSL, NTLM, SRP, OTP, and sample programs are
  disabled to avoid external service and credential-store dependencies.
- Static SASL support is enabled for the default package so validation does not
  depend on OHOS runtime plugin directory discovery.

## OHOS build adjustments

- `0001-configure-ohos-tempdir.patch` changes the autoconf temporary directory
  creation umask from `077` to `022`, matching the OHOS/HMDFS build-directory
  permission workaround while keeping the change tracked in `patches/`.
- `0002-lib-Makefile.in-copy-linksrcs.patch` replaces the generated static
  archive symlink step with a copy operation so package creation does not depend
  on symlink support.
- The recipe passes `MKDIR_P`, `INSTALL`, `INSTALL_PROGRAM`, and `INSTALL_DATA`
  to `make`/`make install` for OHOS instead of rewriting generated Makefiles in
  the build tree.
- `CC_FOR_BUILD` is derived from `tools.build:compiler_executables` when
  available and otherwise falls back to the PATH-visible `clang` name; no
  absolute build-machine compiler path is hard-coded.

## Upstream tests

The release includes upstream test and sample sources such as:

- `utils/testsuite.c`
- `saslauthd/testsaslauthd.c`
- `sample/client.c`
- `sample/server.c`
- `sample/sample-client.c`
- `sample/sample-server.c`

These are not executed in the first cross-buildable package because they depend
on sample programs, daemon paths, plugin/backend configuration, or interactive
client/server negotiation. The Conan `test_package` instead validates the public
consumer API without system-authentication services.

For a disposable HarmonyOS PC upstream-harness candidate only, the recipe
also exposes default-off `with_upstream_tests` and `with_sasldb` options. They
must be enabled together on a native runnable OHOS target. That configuration
adds LMDB as a hidden target-side dependency only to build the temporary test
tree, then removes it from the package ID. It copies the patched source into a
temporary build-tree-only test directory, enables the upstream `libsasldb`
closure there, creates `utils/sasldb`, and runs `utils/.libs/testsuite -a`.
The default packaged tree always uses `db_none`; it has no LMDB requirement or
exported LMDB consumer dependency. The two test options are also removed from
the package ID because they do not change the delivered package.

The temporary harness applies `0003-testsuite-use-int-for-getopt.patch` to
the upstream `utils/testsuite.c` before the source copy is made. The patch only
stores the `getopt()` result in its specified `int` type; it does not change
test inputs, assertions, or pass criteria. Any submitted evidence must report
this upstream test-source modification.

## Validation status

PR CI build #11317 initially failed in `source()` before the consumer test ran
because the conandata patches were not present in the exported source folder.
The `exports_sources = "patches/*"` correction was included in subsequent CI
build #11333, which passed the Conan `test_package` and L0/L1 gates on recipe
commit `65f19f2b`. Later commits do not have a separate CI result. This archive
therefore uses
`status: built`; that remote result does not claim a successful local Conan
build, package upload, or OpenHarmony runtime test.

## 2026-08-04 HarmonyOS PC native evidence

The local-only r5 candidate ran on `frp-tip.com:48099` (HarmonyOS aarch64,
Conan 2.29.1) in its own `CONAN_HOME`. Its source archive SHA-256 was
`7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c` and
the executed recipe SHA-256 was
`4379b54897ed30789176401e76fa668e9d57aed40d62c505cdf4a2ff2a602369`.
`conan create` exited 0 with both test-only options enabled. The delivered
tree remained `db_none`; LMDB and `libsasldb` existed only in the copied
temporary test tree.

The actual `utils/.libs/testsuite -a` invocation completed successfully. Its
log reports all 18 scheduled top-level phase groups as successful: seven base
phases, eight mechanism-negotiation phases, all-corruption, proxy-policy, and
security-layer phases. The `-a` mode explicitly skips random tests; four
minimum-SSF requests are explicitly skipped by upstream for mechanisms without
a security layer and are not counted as passes. The consumer executable also
ran successfully: one executable invocation and all seven recorded assertions
passed. `saslauthd/testsaslauthd` is still outside this result because the
shipping recipe deliberately configures `--without-saslauthd`.

The first r4 target attempt showed that adding only the temporary tree's
`LD_LIBRARY_PATH` corrected the incompatible device `libsasl2.so.3` loader
failure, but `saslpasswd2` also needs `SASL_PATH` to load that tree's
`libsasldb` plugin and create the LMDB fixture. The r5 adjustment scopes both
variables to this test-only fixture command; neither is exported to consumers
or added to the delivered package.

## 2026-08-04 saslauthd native-test candidate

The local-only r6 candidate adds a default-off `with_saslauthd_tests` option.
It is valid only with the native `with_upstream_tests` plus `with_sasldb`
closure, is removed from `package_id()`, and only changes the copied temporary
test tree. That tree configures `--with-saslauthd=<test-run-dir>` and
`--with-dbpath=<test-tree>/utils/sasldb`; the delivered source tree still
configures `--without-saslauthd` and `db_none`.

On the HarmonyOS PC, default and daemon-candidate `conan graph info` produced
the same Cyrus package ID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`. The r6
candidate built `saslauthd` and `testsaslauthd`, rebuilt and completed the
actual `utils/.libs/testsuite -a` 18/18 top-level phases, then stopped before
starting `testsaslauthd`: `saslauthd -a sasldb -m <test-run-dir> -d` failed to
bind its `mux` socket with `Operation not permitted`.

A direct target probe reproduced `AF_UNIX` bind `EPERM` in the user's writable
`/storage/Users/currentUser/codex-tests` and `/storage/Users/currentUser/tmp`;
`/data/local/tmp` and `/tmp` are not writable by this user. Thus a short,
writable target mount that permits named Unix sockets is a device prerequisite
for daemon integration coverage. Do not report `testsaslauthd` as passed or
failed, because the client never started. The r6 transaction also stopped
before package installation and its consumer test; r5's separate 1/1 consumer
result remains the only consumer evidence.
