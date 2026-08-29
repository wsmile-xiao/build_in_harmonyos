# attica-kf5 5.116.0 notes

## Scope

This package tracks the KDE Frameworks 5.116.0 Attica release under the
`attica-kf5` package name. The explicit KF5 suffix keeps it distinct from the
existing `attica` KF6 packages and the previously published `attica5` recipe.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- The optional `tests/projecttest` is configured only when the selected Qt
  package provides Qt Widgets; the published Qt5 package used here provides
  Core, Network, and Test but no Qt5Widgets CMake package.
- `providertest` is excluded from the CTest invocation because it depends on
  live OCS network endpoints (`autoconfig.kde.org` and `invalid-url.org`);
  the current OHOS runner can hang while waiting on those external requests.
- Runtime/build dependencies use the current local baseline:
  `qt5-qtbase/5.15.2` and `ecm/6.20.0`.

## Knowledge Extension

This adaptation adds the PR-attached reusable draft pair:

- `knowledge/drafts/E2166-draft-2301.kv`
- `knowledge/drafts/E2166-draft-2301.md`

The draft records the Windows-to-OHOS Qt5 host/target tool split: the target
Qt package remains the OHOS dependency, while native Qt `moc`, `rcc`, and
`uic` are injected through the Conan CMake toolchain. Deduplication searched
`knowledge/graph`, `knowledge/drafts`, `knowledge/doc`, and
`knowledge/operations` with exact-signature, Qt host-tool, `QT_HOST_PATH`,
and semantic host/target separation queries. The conclusion was
`NO_EQUIVALENT_REUSABLE_KNOWLEDGE`; evidence is in
`reports/knowledge-dedup-result.json` with SHA-256
`7076916cc039fb60b70ab41a0b1c4e3e01856d1a6963067847e2881f8d61e275`.

The pair is submitted with this software PR as a draft and is not yet a
formal knowledge-graph entry.

## Verification

Local and OHOS checks:

- The official release checksum is recorded in `conandata.yml`.
- W0 was rechecked on 2026-08-27 against the ohpcd Conan v2 revisions API:
  `qt5-qtbase/5.15.2` and `ecm/6.20.0` both returned HTTP 200 with a
  non-empty recipe revision. `zlib/1.3.1` returned HTTP 200 as the known
  published-package control.
- The OHOS profile, SDK Clang target/sysroot detection, Ninja configuration,
  CMake compiler/linker probes, 86/86 target build, package creation, and
  1/1 Conan consumer cross-link have passed locally. The Windows host build
  uses explicitly supplied native Qt host tools; the target Qt package's
  AArch64 `moc` is not executed on Windows.
- The package consumer was uploaded to a HarmonyOS PC AArch64 staging
  directory. After the staging ELF files were signed in place and given
  execute permission, `test_attica` returned 0 and printed
  `PASS: Attica value objects OK`.
- The upstream `configtest` and `persontest` executables were also signed and
  run on the target. Each reported 3 passed, 0 failed, 0 skipped, and exit
  code 0. `libQt5Test.so.5` was added to the staging runtime because both
  executables declare it in `DT_NEEDED`.
- A bounded target run of `providertest` reached
  `https://autoconfig.kde.org/ocs/providers.xml` but received no usable
  provider entry; the upstream test then aborted on `QList::at` with exit
  code 134. It is retained as a failed network-dependent upstream test and
  is excluded from the Conan cross-build CTest invocation to avoid hanging
  on external OCS requests.

## Validation Boundary

The local cross-build proves dependency resolution, CMake configuration,
86/86 target compilation, package creation, and consumer linking. Target
execution proves the package consumer and the two non-network upstream
autotests. The network-backed provider test remains a separate failed
environment-dependent result; it is not counted as an upstream pass.
CI/review, merge, and Conan publication are still pending.

The repository `finish` workflow was attempted after validation. On this
Windows host its G0 step could not find the ignored source tarball, the
ConanVerifier could not find a `python3` command, and W3 could not run because
`zsh` is unavailable. These workflow-environment failures are separate from
the independently successful Conan create and target tests, so the package
status remains `built`.
---

**编译结束**: 2026-08-28 04:26
**最终状态**: built
