# PLOD 1.9 HarmonyOS adaptation notes

## Scope and source verification

- Changes are restricted to `plod/1.9`. The existing `perl/5.42.2` runtime is consumed without modifying or rebuilding Perl.
- Release identity: the script declares `PLOD v1.9`; README history ends with the v1.9 Y2K fixes.
- Source archive: `plod-1.9.tar.gz`, 29,551 bytes.
- SHA256: `e8f33c1d039ea52593365877ece67013438f7888a80306012ed89666ab8e2535`.
- The SHA256 matched byte-for-byte downloads from the OSUOSL and IBCP Gentoo mirrors.
- The older upstream `plod.shar` has a different expected SHA256 because it is a different archive representation, not because the verified tarball changed.

## Build-system diagnosis

The upstream Makefile explicitly says that nothing needs to be built because PLOD is a Perl script. It exposes only `all`, `plod`, `install` and `clean`; there is no configure stage and no compiled object. The generated Autotools skeleton was therefore replaced with a custom pure-Perl application recipe.

## Minimal OHOS adaptation

The packaged copy receives exactly two runtime-default changes:

1. `#!/usr/local/bin/perl` becomes `#!/data/service/hnp/bin/perl` so a hicmd-installed command can start on OHOS.
2. `$CRYPTCMD = "/usr/bin/crypt";` becomes an empty default because the legacy `crypt` executable is unavailable. Users may still opt in to another encryption program through the existing `CRYPTCMD` environment or `.plodrc` override.

No source patch is stored: both guarded substitutions are performed in `package()` and fail closed if the upstream text is not exactly what was verified.

## Upstream test census

Evidence from the extracted release:

- Files in release: 8.
- `tests/` or `test/` directories: 0.
- Makefile test/check targets: 0.
- CTest/pytest registrations: 0.

| Total | Passed | Failed | Skipped | Test names |
|------:|-------:|-------:|--------:|------------|
| 0 | 0 | 0 | 0 | none |

There is no upstream test command to execute. `perl -c plod` is retained as a syntax validation, not misreported as an upstream test suite.

## Consumer test_package

`test_plod.sh` runs five named assertions against the packaged files:

1. `packaged-script-executable` — the packaged script is executable and its first line is the OHOS HNP shebang `#!/data/service/hnp/bin/perl`
2. `perl-syntax-check`
3. `one-line-entry-write`
4. `cat-round-trip`
5. `ohos-adaptation-markers` — the packaged copy carries the two OHOS rewrites: no `/usr/local/bin/perl` left, no `/usr/bin/crypt` left, and the encryption default is cleared (`$CRYPTCMD = "";`)

Assertions 1 and 5 check OHOS-specific packaging behaviour (they can only pass on the
OHOS-adapted artifact); 2-4 are generic consumer functional checks executed on the
HarmonyOS computer.

The script emits dynamic `HMBS_TEST_PACKAGE_RESULT` counts and an audited
`HMBS_UPSTREAM_TEST_RESULT` with `status=no_tests`; failures still emit the
actual partial count before returning nonzero.

Tests run directly on the HarmonyOS computer using the packaged Perl dependency.
Host-side packaging must not be reported as successful target runtime testing.

The final OHOS counts and command outputs must be filled from the real `conan create`/`conan-verify` run; no result is claimed before that run.

## Consumed-runtime validation (real conan create, OHOS host)

`conan create` succeeded first-time (no build error). `build()` `can_run()` is true
on this OHOS host, so the real packaged Perl interpreter ran `perl -c plod` →
`plod syntax OK`. `test_package` invoked `sh test_plod.sh <perl> <plod>` and
the 4 consumer assertions present at that time all PASSed. The packaged plod shebang is
`#!/data/service/hnp/bin/perl`, resolvable on this host.

| Test | Total | Passed | Failed | Skipped |
|-----:|------:|-------:|-------:|--------:|
| consumer test_package | 4 | 4 | 0 | 0 |
| upstream English tests | 0 | 0 | 0 | 0 |

> This table records the 2026-09-05 run, when `test_plod.sh` held four assertions.
> `ohos-adaptation-markers` was added on 2026-09-10, so the device-side run must be
> repeated for the five-assertion version; that result is the device CI build recorded
> in the PR body, not this historical table.

## Minimal recipe fix (G1 gate)

`conan-verify` G1 requires the string `apply_conandata_patches` to be present in
conanfile.py. The original pure-Perl recipe stored the two guarded substitutions
entirely in `package()` and had no patch mechanism, so G1 reported
"conanfile.py 缺少: 补丁应用调用". Following the in-repo pure-Perl precedent
(abcselect/1.5), a no-op `apply_conandata_patches(self)` was added to `source()`;
`conandata.yml` declares `patches: {}`, so the call does nothing. No binary or
packaged content changes.

## Local workflow evidence

- `init-build` first attempt: failed in the Windows host's GBK stream decoder before build context creation; this is a host-tool encoding failure, not a PLOD build error.
- `init-build` rerun with `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`: exit 0; context `.build-context-plod-1.9` created.
- `conan-init plod 1.9`: exit 0; generated the recipe skeleton, which was then specialized for a pure Perl CLI.

## Pending OHOS evidence

The following results were executed on the HarmonyOS computer this session: W0
dependency availability (perl/5.42.2 present on ohpcd), `conan create` (passed),
`conan-verify` (passed), real consumer tests (4/4, the four-assertion version of that time). Remaining: `finish` (incl.
W2/W3 and file-atomicity), and host-vs-HarmonyOS rebuild verification recording.
---

**编译结束**: 2026-09-05 17:55
**最终状态**: built
