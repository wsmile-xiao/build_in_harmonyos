# perl 5.42.2.3 adaptation notes

## Version model

- Conan package version: `perl/5.42.2.3`
- Upstream source and runtime version: Perl `5.42.2`
- Source archive: `perl-5.42.2.tar.gz`
- Source SHA256: `9384e8deb75b7b1695e5637971b752281aaecd025a3d5d4734d33c1d0adfee47`

The fourth component is an OpenHarmony package revision. It does not claim an upstream Perl 5.42.2.3 release. The software-level `commands.json` retains mappings for `5.42.2`, `5.42.2.1`, and `5.42.2.3`.

## Iteration purpose

`5.42.2` and `5.42.2.1` recipes were already merged into `origin/main` and published to the `ohpcd` artifact registry by earlier collaborators. `5.42.2.3` is a clean independent iteration that:

- re-validates the full adaptation recipe (codesign of Perl ELF + XS modules, copy-link emulation, writeability probes, disabled `prctl`, excluded SysV IPC, short build-local `TMPDIR`) with a **fresh clean-source `conan create` on a true HarmonyOS aarch64 device**;
- re-runs the **complete upstream test suite** (`make test_harness_notty`) on that device and records per-file crash points with verified technical evidence (see `upstream-failure-analysis.md` and the QC evidence under the run worktree);
- keeps the recipe code identical to the validated `5.42.2.1` lineage — no silent deviation from the version already accepted upstream.

## Compatibility fixes carried in this revision (unchanged from the validated lineage)

1. Signs `perl`, `perl5.42.2`, and all built XS `.so` files in the build tree (OHOS rejects unsigned ELF / XS modules), then verifies `.codesign` sections in the final package.
2. Replaces Perl's hard-link/symlink build rules with a build-local copy wrapper (`ohos-ln-copy.sh`).
3. Uses actual create/unlink write probes for `ExtUtils::Install` and `installperl` where OHOS storage reports `-w` false but writes succeed.
4. Disables `prctl`/`PR_SET_NAME` (`-Ud_prctl -Ud_prctl_set_name`) — Configure probes a short name that succeeds while real `$0` updates fail with `EINVAL`.
5. Excludes `IPC/SysV` and external DBM libraries (`noextensions`).
6. Forces build-local `TMPDIR`/`TMPPREFIX` (device `/tmp` is read-only).
7. Applies `0004-extutils-xs-needed-on-ohos.patch` so `ExtUtils::MakeMaker` dynamic XS fixtures link correctly on OHOS.

## Verification

Clean-source command (host == build == OHOS native, repository `ohos-aarch64` profile):

```sh
cd archives/p/perl/5.42.2.3
CONAN_HOME=<isolated conan home> conan create . \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

Result and package reference are recorded in `manifest.yaml` `validation:` after the fresh true-device run (updated by W3).

Upstream full-suite evidence (`TEST_JOBS=4 HARNESS_NOTTY=1 make test_harness_notty`, run in the fresh build tree with a short absolute `TMPDIR`) is summarized in `upstream-failure-analysis.md`.
