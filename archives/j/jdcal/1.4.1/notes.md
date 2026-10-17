# jdcal 1.4.1 adaptation notes

## Fixed input and scope

- Official PyPI sdist `jdcal-1.4.1.tar.gz`, 7,479 bytes, SHA-256
  `472872e096eb8df219c23f2689fc336668bdb43d194094b5cc1707e1640acfc8`.
- This is a pure-Python, single-module package with no runtime dependencies.
- Contest task #7593 is labelled `cpp`, while the fixed source is Python. The
  human contest route is being used with the mismatch disclosed; the label was
  not changed and no general exemption, eligibility, or points are claimed.
- GCW account's active Developer/write membership in the upstream repository
  was verified on 2026-09-28. This proves repository membership only, not
  contest eligibility, language approval, merge authority, or points; the
  supporting receipt remains in internal project evidence.

## Packaging

The Conan recipe pins the source URL and SHA-256, and rechecks the digest when
`JDCAL_SOURCE_ARCHIVE` supplies the already-verified archive. It compiles the
module with the target `python3`, packages `jdcal.py` and the upstream BSD
license, and exposes the module with Conan's `PYTHONPATH` run environment.
The recipe now uses the repository's `export_conandata_patches()` and
`apply_conandata_patches()` hooks; there are no patches declared. These hooks
were added after H1-001 and still require fixed-candidate verification.

## Validation evidence

H1-001 ran once on OpenHarmony PC aarch64 with Python 3.12.9 and Conan 2.29.1.
The official `finish` process returned RC1. Its internal W3 setup and
`build_and_test.sh` returned RC0, a real Conan package was created, and the
target consumer function checks passed 7/7. The old consumer script inserted
the package path directly into `sys.path`, so it did not verify Conan's
`PYTHONPATH` run-environment wiring. The fixed consumer removes that insertion and requires a new run-environment-backed
verification. G0 failed because the legacy clean-build step could not find an
original tarball, despite the fixed sdist being supplied
to Conan with `JDCAL_SOURCE_ARCHIVE`. G1 failed because the original candidate
lacked the two recipe hooks; this candidate now adds them and needs a new
fixed-input verification. The H1-001 raw result is retained in project evidence; H1-004 fixed-candidate result is pending its separate receipt.

The host upstream pytest run on CPython 3.11.0rc2 was 9 passed, 1 skipped (the
optional Astropy/ERFA comparison). A CPython 3.14 staged-layout simulation of
the consumer passed 7/7; it is not Conan or target evidence. No source-level
portability patch was required.

The same H1 run reported a `gen_summary` exception and shared knowledge-field
errors in E219, E253 and E305. These are retained as framework/shared-data
issues; this candidate does not modify the framework or unrelated knowledge
entries. Old tarball, `packaging/`, and staging-marker readiness expectations
are not recreated because the project has migrated to the Conan workflow.
