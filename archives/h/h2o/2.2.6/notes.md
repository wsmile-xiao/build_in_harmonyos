# H2O 2.2.6

The upstream project defines test execution as its custom CMake `check` target.
The recipe runs that target only with `with_upstream_tests=True` on a native,
non-cross runnable target; cross builds require separate target-side test
evidence. It is not replaced with a consumer-only smoke test. Perl is a
test-only build tool in that mode because the target invokes `prove`. MRuby is
disabled because it needs host Ruby and Bison during the target build. The
selected H2O core, event-loop, picotls and Perl test path remain upstream code.
A completed adaptation requires the full upstream suite to run on an
OpenHarmony PC device with an actual `passed/total` result; host results and
pending CI are not target validation.

## 2026-08-04: upstream Perl test closure is test-only

The local HarmonyOS PC candidate completed native H2O compilation, but its
upstream CMake `check` target did not reach TAP assertions. The Conan
`perl/5.42.2` `prove` entrypoint has a malformed `#!//bin/perl` shebang. A
system `prove` combined with the Conan `PERL5LIB` is also invalid because it
mixes Perl XS ABIs (`Perl_my_cxt_init: symbol not found`). Explicitly using the
matching Conan Perl interpreter reaches H2O's scripts, which then stop before
assertions for missing upstream test modules such as `Net::EmptyPort`.

The retained summary, `Files=87, Tests=0, Result: FAIL`, is a test-environment
blocker, not a functional `0/87` rate. The local candidate now records an
ordered CPAN closure with exact URLs, versions and SHA-256 hashes in
`conandata.yml`. A native `check` must supply those archives through
`H2O_TEST_CPAN_ARCHIVE_DIR`; the recipe verifies them and installs them under
an isolated H2O build-folder prefix. They are not a product runtime
requirement, package payload, or `package_info()` export. See the local draft
`knowledge/graph/draft/E253-draft-7912.md` and
`reports/h2o-perl-test-dependency-closure.md`.

The local candidate now prepends an executable `prove` wrapper only while
running CMake's opt-in upstream `check` target. The wrapper executes the Conan
package's `bin/prove` script with that same package's `bin/perl`, and sets a
deterministic test-only `PERL5LIB` containing only the isolated test prefix,
the matching Conan Perl core and architecture library paths, and the H2O source
tree. The verified archives are re-extracted for every test run, so a stale
test source tree cannot bypass archive provenance. A native rerun is still
pending transfer of this local candidate and the small CPAN archive directory,
plus real target validation of the XS modules against Conan Perl and OpenSSL
3.5.6. No test rate changed.

## 2026-08-04: neverbleed native test-path result

This section supersedes the preceding historical wrapper/transfer note. The
current candidate executes the complete top-level `t/*.t` scope directly with
the matching Conan `perl` and `prove --exec`, after the SHA-256-verified
42-archive CPAN test closure has been installed. The `H2O_NEVERBLEED_TMPDIR`
source compatibility patch preserves H2O's upstream `/tmp` default unless the
native test runner explicitly exports a test-only directory.

Two complete HarmonyOS PC invocations reached `Files=87, Tests=21, Result:
FAIL`; this is a failed suite summary, not a passed/total rate. The first
test-only temporary directory was under the long Conan build path and exceeded
the named Unix-socket path budget. The second used a short writable user path,
but binding neverbleed's `AF_UNIX` socket there returned `Operation not
permitted`. Direct probes showed the same result for three writable user
storage paths. The device's `/tmp` is read-only and `/data/local` is not
writable for this user. A short writable filesystem that supports named Unix
sockets is therefore a concrete test prerequisite; no package or consumer
test ran. Missing `curl`, `nc`, and `nghttp` remained TAP skips, never passes.
# 2026-08-07 HarmonyOS PC validation

- Private r21 execution on HarmonyOS 1.12.0 aarch64 completed the complete
  `t/*.t` TAP scope with `Files=87, Tests=27, Result: PASS`, an actual
  executed upstream rate of 27/27 (100%).
- The native Conan `test_package` then passed 1/1 by checking `h2o -v` for
  version 2.2.6. This is device evidence only; no public PR body or review
  status was changed.
- The target lacks `make`, so a fresh Conan upstream-test closure cannot be
  rebuilt there. The completed TAP run used the retained SHA-verified CPAN
  closure from the preceding device transaction. Missing `curl`, `nc`,
  `nghttp`, `plackup`, and `start_server` remain upstream skip conditions.
