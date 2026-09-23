# coinutils 2.11.12 OpenHarmony Port Notes

## Scope

This package prepares COIN-OR CoinUtils 2.11.12 for the OpenHarmony PC
aarch64 target. CoinUtils provides sparse matrix, MPS parsing, factorization,
and helper data structures used by downstream COIN-OR packages such as
coin-osi, coin-clp, and coin-cbc.

## Branch/PR Split

- Current branch: `feat/coinutils-2.11.12`.
- Recipe scope: `archives/c/coinutils/2.11.12/**`.
- Issue: skipped per handoff instruction; no issue lookup is required for this round.

## W0 Dependency Graph

```text
coinutils/2.11.12
  |-- bzip2/1.0.8
  `-- zlib/[>=1.2.11 <2]
```

The archive already contains built metadata for bzip2/1.0.8 and zlib/1.3.1,
so no dependency split-out is needed. BLAS, LAPACK, Glpk, and ASL are optional
upstream features and are disabled with `--without-*` configure arguments.
An initial shadow run exposed copied MSVC-only `automake`/`msys2` tool
requirements that were irrelevant for this OpenHarmony package and unreachable
from the target registry; those tool requirements were removed before the
passing run below.

## Source And Build Analysis

- Upstream source URL: `https://codeload.github.com/coin-or/CoinUtils/tar.gz/refs/tags/releases/2.11.12`
- SHA256: `eef1785d78639b228ae2de26b334129fe6a7d399c4ac6f8fc5bb9054ba00de64`
- Source retrieval note: this is GitHub's official codeload endpoint for the
  same upstream tag archive. It matches the verified SHA256 and avoids the CI
  worker timeout seen when the automatic `gh-proxy.com` fallback was tried.
- Build system: autotools, with root and nested `CoinUtils/configure` scripts.
- OpenHarmony-specific handling:
  - run configure in `ohos-work` under Conan build folder;
  - relax autotools temporary directory umask from 077 to 002;
  - disable optional solver/math backends;
  - patch both root and nested `config.guess` to recognize HarmonyOS/HongMeng as Linux + musl;
  - avoid install-time pkg-config `--libs` probing during cross/target packaging;
  - expose both `include` and `include/coin` for downstream consumers.

## Validation

Upstream test inventory:

```text
CoinUtils/test/Makefile.am
  noinst_PROGRAMS = unitTest
  test: unitTest$(EXEEXT)
        ./unitTest$(EXEEXT) $(unittestflags)
```

The `unitTest` target aggregates C++ checks for LP/MPS I/O, sparse matrices,
packed vectors, dense vectors, indexed vectors, models, errors, and message
handling. The OHOS-native recipe path now builds the noinst test binary,
re-signs it with `llvm-objcopy` and `binary-sign-tool`, and runs `make test`.
Because this package does not vendor Sample/Netlib datasets, the data-gated
MPS/LP/Model branches remain disabled while the non-data-gated checks execute.

Local preflight passed in this round:

```text
python -m py_compile archives/c/coinutils/2.11.12/conanfile.py archives/c/coinutils/2.11.12/test_package/conanfile.py
git diff --check -- archives/c/coinutils/2.11.12
```

Patch applicability was also checked against the 2.11.12 source tree with
`git apply --check` for all three patches.

Windows PATH did not provide `conan`/`cmake`, so local Windows `conan create`
was not run. The recipe was then validated on an OpenHarmony PC shadow CI run:

```text
run_root=/storage/Users/currentUser/ohpc-ci-shadow/runs/manual-coinutils-2.11.12-min-20260908T025816Z-22719
CI_PACKAGES=archives/c/coinutils/2.11.12 zsh -f ci/conan/build_and_test.sh archives/c/coinutils/2.11.12
```

Result:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Total: 1
Success: 1
Failed: 0
Pass rate: 100.0% (1/1)
```

The test package built `coinutils_smoke`, signed it with
`binary-sign-tool`, executed it on the target, and printed:

```text
CoinPackedMatrix::getNumElements() = 0
OK: coinutils 2.11.12 smoke test passed.
```

## Target Rerun Commands

Direct Conan rerun command:

```text
conan create archives/c/coinutils/2.11.12 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=coinutils/*
```

Optional repository wrapper:

```text
python3 scripts/ohc-run.py conan-verify coinutils 2.11.12
```

Expected L1 consumer check: build and run `test_package/coinutils_smoke.cpp`,
which constructs a default `CoinPackedMatrix` and verifies it is empty.

## Path B Knowledge Draft Candidate

This package now carries package-local knowledge drafts under
`archives/c/coinutils/2.11.12/knowledge/drafts/`. They are intentionally kept
inside the CoinUtils version directory so the PR remains scoped to one library.
They are draft evidence for a Path B / B-class difficulty application, not a
claim that the entries are already promoted to the shared knowledge graph.

Draft pairs added:

- `DRAFT-coinutils-autotools-dual-config-guess.{kv,md}`: COIN-OR nested
  autotools releases can carry both root and component `config.guess` copies;
  HarmonyOS/HongMeng support must be applied and checked in both places.
- `DRAFT-coinutils-install-pkgconfig-cross-probe.{kv,md}`: CoinUtils generated
  `install-data-hook` runs `pkg-config --libs coinutils` during `DESTDIR`
  packaging; Conan `package_info()` should be the stable consumer contract.
- `DRAFT-coinutils-generated-configure-umask-install-sh.{kv,md}`: generated
  configure temp-dir `umask 077` and direct `install_sh_DATA` calls can require
  OHOS-scoped generated-file fixes without introducing autoreconf tooling.
- `DRAFT-coinutils-optional-solver-backend-boundary.{kv,md}`: optional
  BLAS/LAPACK/GLPK/ASL probes must stay disabled until those backends are
  adapted as separate packages.
- `DRAFT-coinutils-ohos-tool-requirements-leak.{kv,md}`: copied MSVC-only
  `automake`/`msys2` tool requirements made the first target L0 fail before
  CoinUtils itself was evaluated; unused platform tool requirements should be
  removed from the OHOS path.
- `DRAFT-coinutils-consumer-smoke-negative-test.{kv,md}`: library-only numeric
  packages need a real CMakeDeps API consumer and negative-link evidence, not
  just file-existence checks.

Suggested B-class framing:

```text
coinutils/2.11.12 is a Path A + Path B candidate. The library itself is the
base of the COIN-OR solver stack, and the adaptation produced reusable knowledge
across six independent surfaces: nested autotools platform detection,
install-time pkg-config cross probes, generated configure/install helper
compatibility, optional solver backend dependency boundaries, tool-requirement
scope reduction, and target-executed consumer validation. Shadow CI on an
OpenHarmony PC passed L0/L1/L4/L5 with a signed CMakeDeps consumer and negative
dependency test.
```

Boundary for reviewers: the upstream aggregate target is recorded as 1/1
passed, with the data-gated Sample/Netlib branches explicitly excluded. The
validated evidence is the Conan package build, signed upstream `unitTest`,
package metadata checks, patch-clean gate, signed `test_package`, and L1e
negative test from the shadow CI run above. The new upstream-test signing
pattern is captured in the paired package-local knowledge draft.
