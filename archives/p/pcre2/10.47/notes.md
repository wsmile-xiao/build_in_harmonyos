# PCRE2 10.47 OpenHarmony PC adaptation notes

## Scope

- Official source: PCRE2 10.47 release archive.
- Static PIC libraries: 8-bit, 16-bit, 32-bit, and POSIX wrapper.
- Tools: `pcre2grep`, `pcre2test`, and `pcre2-config`.
- JIT is enabled and exercised by both the official suite and consumer tests.

## Portability changes

1. `config.guess` identifies the target's `uname -s=HarmonyOS` result without a compile-time platform macro.
2. `config.sub` accepts the canonical `aarch64-linux-ohos` triplet emitted by the Conan toolchain.
3. The extracted source tree may be on a noexec mount, so the recipe invokes `configure` through an executable shell selected from `CONFIG_SHELL`, the configured compiler directory, `/system/bin/sh`, or `PATH`. Each candidate must first execute `pwd` from the real Conan build directory with exit 0 and no output or diagnostics; this rejects shells that start but cannot preserve the working directory.
4. Optional zlib and bzip2 support in `pcre2grep` is disabled; the recipe has no third-party dependencies.
5. Documentation and manual pages are excluded from package installation; headers, static libraries, pkg-config metadata, and tools remain installed.
6. The recipe uses Conan's `static-library` package type. The generic `library` type requires a `shared` option and failed during the first fresh target graph calculation before source download.
7. Conan profile buildenv values are applied to child commands but are not guaranteed to appear in the recipe Python process environment; shell discovery therefore cannot depend on `os.environ` alone.
8. The HNP Bash executable can return success from a child command while emitting `getcwd` diagnostics and making Autoconf reject the build directory. Shell executability alone is therefore insufficient; the recipe uses a runtime working-directory capability probe.
9. Autoconf re-executes itself through `CONFIG_SHELL` even when the outer command explicitly uses another shell. The recipe binds both `CONFIG_SHELL` and `SHELL` to the capability-tested shell for the configure invocation so a profile-provided shell cannot replace it.
10. Conan's `self.run()` implicitly sources `conanbuild`, which can overwrite an in-process environment context. Configure, build, check, and install therefore source an explicit `pcre2_shell` environment after `conanbuild` so the tested shell remains authoritative throughout the Autotools lifecycle.
 11. Automake's race-free directory probe can select the source-tree `install-sh -c -d`. Direct execution of that helper is denied from HMDFS during `config.status` dependency bootstrapping, so the OHOS invocation environment binds `MKDIR_P=/system/bin/mkdir -p`. Dependency tracking remains enabled, and the secure Autoconf temporary-directory mask is unchanged.
 12. The CI failure `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` is caused by the generated `configure` creating `./confXXXXXX` with `umask 077` on HMDFS. The third patch changes only the two temporary-directory creation masks to `022`, preserving the rest of Autoconf's temporary-file logic.
 13. Automake's parallel test harness directly executes suffixless tests. The two upstream shell drivers are denied from the noexec source tree even though their test logic passes under the selected shell. `make -j1 check` therefore receives a `LOG_COMPILER` dispatcher that interprets only `RunTest` and `RunGrepTest`; the two compiled ELF tests remain direct executions, and Automake still produces one authoritative four-entry summary.
 14. The upstream install metadata records the configure prefix. The recipe rewrites all four `.pc` files to derive `prefix` from `pcfiledir`, makes `pcre2-config` derive its prefix from its installed path, and removes `.la` files whose `libdir` cannot be made relocatable.

No source or patch uses an OHOS-named conditional compilation macro.

## Test inventory

The official `make -j1 check` target registers four entries:

1. `pcre2posix_test`
2. `pcre2_jit_test`
3. `RunTest`
4. `RunGrepTest`

The independent Linux native reference build passed `4/4` with `SKIP=0`, `XFAIL=0`, `FAIL=0`, and `ERROR=0`.

The Conan consumer adds eight flows: 8/16/32-bit APIs, POSIX APIs,
`pcre2grep`, `pcre2test`, one consumer linked from the installed pkg-config
metadata, and one `pcre2-config` relocation flow. The metadata tests reject
system `/lib` or `/include` fallback paths.

## Validation

The candidate intentionally contains no package revision, target-run log hash,
or result-bundle hash. Those values are outputs of a particular execution and
must be recorded only in that run's checksummed result closure.

A fresh target run must execute the four upstream Automake entries, all eight
consumer flows, and all six metadata relocation checks from one exact snapshot.
It must use `tools.build:jobs=1`, reject `-j20` and `--parallel 20`, and publish
the newly observed Conan recipe revision, package ID, and package revision from
the current structured `conan create` output. Historical run values are not an
acceptance oracle for a new freeze revision.

## Path B knowledge contribution

The reusable combination of a clean working-directory shell capability probe,
post-`conanbuild` `CONFIG_SHELL`/`SHELL` reassertion, and selective
`LOG_COMPILER` dispatch for mixed suffixless shell and direct-ELF Automake tests
is submitted as `knowledge/drafts/E330-draft-2301.kv` plus its Markdown pair.
It extends E228's Libtool-wrapper rule and E232's initial configure-launch rule
without replacing either one. No path C claim is made.
