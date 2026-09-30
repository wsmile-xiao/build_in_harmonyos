# wcalc 2.5 adaptation notes

## Registered knowledge used

This adaptation used the repository's registered knowledge entry `knowledge/graph/E011.kv` (documentation: `knowledge/doc/E011.md`, `edit-umask-in-configure`). The first OHOS CI run failed at Autoconf `config.status` with `./confPkMlmf/subs1.awk: Permission denied`; the released `configure` creates a `confXXXXXX` directory under `umask 077`. E011 identifies this HMDFS permission pattern and recommends changing that umask to `022`. The OHOS-only patch `patches/0001-configure-hmdfs-umask.patch` applies that remedy, and CI build `conan-pr-check/63647` subsequently completed configuration, build, upstream tests, and packaged consumer tests. This is a use record for E011, not a new knowledge entry.

## Source and dependency selection

The source is the upstream 2.5 tarball from SourceForge's download service, pinned by SHA256 in `conandata.yml`. The direct project-page download initially returned an anti-bot page, so the recipe uses SourceForge's `downloads.sourceforge.net` endpoint. The downloaded bytes have SHA256 `2c188cd5a58e90ec1d85e4c8cc891c2c2596d946fcc4a4096c878ad91dac77c7`, identical to the already-tested Debian `orig.tar.gz` mirror; SourceForge's own release page lists the same digest. The released `mpfr/4.2.2.1` Conan recipe explicitly requires `gmp/6.3.0`; using `gmp/6.3.0.1` caused a reproducible Conan version conflict. Anonymous `conan download --only-recipe` succeeded for both exact references. An OHOS 6.0 / armv8 dependency graph found downloadable binaries for both.

Readline is optional in upstream `configure.ac`; `--without-readline` removes that dependency. Interactive standard input works in the Linux baseline and the OHOS packaged consumer test, but readline history and completion are disabled. The generated Conan Autotools configuration for OHOS contains `--host=aarch64-linux-ohos`, `--without-readline`, and the GMP/MPFR package locations.

## Validation completed

- Linux x86_64 source baseline: `./configure --without-readline`, `make -j2`, `make check` completed. Upstream suite: 21 total, 12 PASS, 9 XFAIL, 0 FAIL, 0 ERROR. The nine `err.*.test` cases are marked expected failures by upstream `test/Makefile.am`; they are not counted as passes.
- The seven consumer assertions in `test_package/test.sh` failed without `wcalc` and passed against the freshly compiled upstream binary. They cover version, arithmetic, precision, hexadecimal formatting, variables, plain interactive standard input, and syntax error reporting.
- Conan's OHOS 6.0 / armv8 graph and `conan install` resolved and downloaded the exact published GMP/MPFR binaries. This checks dependency availability and recipe generation, not compilation of wcalc for OHOS.

## OHOS target validation

This workstation has no configured OpenHarmony SDK or device access, so local WSL runs cannot validate an OHOS binary. The official OHPCD PR worker built and ran the package on OHOS armv8 in `conan-pr-check/63647` for commit `66df5ab2` on 2026-09-28. `conan create` passed; upstream `make check` reported 21 total, 12 PASS, 9 XFAIL, 0 FAIL, 0 ERROR. The packaged CLI passed all seven consumer assertions, including interactive standard input. CI also passed L0/L1/L2/L4/L5, including the destructive negative test that confirms the consumer test requires the packaged binary. The binary has not been uploaded to the public Conan registry, so both manifests record `built`, not `published`. The local `ohc-run.py conan-verify` command has not been run on this workstation; the official PR CI is the target-build evidence.

## OHOS CI round 1 and portability fix

PR #13439 CI build `conan-pr-check/63403` reached `conan create` and passed L0 quality gates, dependency availability, and source configuration checks. It failed during `config.status`: `./confPkMlmf/subs1.awk: Permission denied`. The generated script creates `./confXXXXXX` with `umask 077 && mktemp -d`; on the worker's HMDFS filesystem, that directory is not writable by the build user. This is the same HMDFS/Autoconf issue already handled by the repository's `cln/1.3.7` and `libgtop/2.41.3` recipes.

`patches/0001-configure-hmdfs-umask.patch` changes the two temporary-directory creation umasks in the released `configure` script to `022`. Conan applies the patch only for `os=OHOS`, leaving the upstream source and Linux build path unchanged. The patch applies to the exact SHA256-pinned release source. The target rerun `conan-pr-check/63647` confirmed configuration, build, upstream tests, packaging, consumer tests and smoke checks.
