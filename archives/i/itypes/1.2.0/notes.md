# itypes 1.2.0 adaptation notes (candidate)

## Fixed source and scope

- Source: PyPI `itypes-1.2.0.tar.gz`, 4,355 bytes, SHA-256
  `af886f129dea4a2a1e3d36595a2d139589e4dd287f5cab0b40e799ee81570ff1`.
- The package is one pure Python module with no runtime third-party dependencies.
- The contest task is still tagged `lang=cpp` while the upstream source is Python.
  Continue only through the normal human contest and Conan route, disclose this
  mismatch, and do not claim a blanket exemption or guaranteed score.
- The PyPI sdist omits the license file. The adjacent `LICENSE.md` is copied
  verbatim from `LICENSE.md` inside the fixed upstream tag archive at commit
  `86b6fb6aea3546fd86eb319bd06a82a655a94a97`. The full upstream test-source
  archive is 5,583 bytes, SHA-256
  `0e62f24639beec41d503cb20dba5b87e4395966ebb70bbfe7393c0b5a32bb5d9`;
  its extracted license file is 1,509 bytes, SHA-256
  `7f37eae935f7ec3e3ea58b84b0ca4b18c7b624542207cab9b756a8dc4d52b136`.

## Adaptation

The Conan package installs `itypes.py` under `lib/python` and exposes that
directory through `PYTHONPATH`. It exports the fixed license file with the
recipe. It has no native build step; `build()` runs Python bytecode compilation
for the shipped module. No source patch is needed.

## Knowledge reference

- Applied [knowledge entry E410](../../../../knowledge/graph/E410.kv) and its
  [human-readable note](../../../../knowledge/doc/E410.md): a consumer test
  should exercise the packaged library's semantics, not only import it. The
  existing consumer checks immutable conversion, copy-on-write, nested
  updates, equality/hash/conversion, and immutable object properties. These
  are seven scenario groups in one consumer test definition, with seventeen
  literal assertions.
- No new knowledge graph entry is claimed for this package.

## Verification

- The sdist module and the module in the fixed upstream tag archive have the
  same SHA-256: `3d3730dd68f746a6d3767d20c77904d1b0c12579f426c6a7a3cdd50861dc6445`.
- The unmodified upstream `tests.py` passed 11/11 on host Python 3.11.0rc2 with
  pytest 9.0.2 (`-p no:cacheprovider`).
- The consumer script passed 7/7 against a local directory laid out like the
  intended Conan package, with `PYTHONPATH` set to its `lib/python` directory
  and Python site packages disabled (`python -S`).
- `test_package/MANIFEST.yml` counts the 17 literal `assert` statements in
  `functional.py`; all 17 run on a successful consumer execution. Two expected
  `TypeError` checks use exception handling and are separate from that count.
- Fixed H1-001 input was patch SHA-256
  `709fa2379911d42a7f516383f48d83c9029af8348ff892e8327b5b60a88cf679`, with
  the PyPI sdist and upstream test archive hashes listed above. On OpenHarmony
  aarch64, H1-001 ran the upstream suite 11/11, official W3 setup/build, Conan
  create, and the consumer 7/7 successfully. Its official `finish` still
  returned rc 1: G0 could not find the original tarball, and G1 rejected the
  missing `export_sources()` hook and patch application call. This is not a
  full-gate pass. Its original raw logs are retained separately from this
  candidate.
- This candidate adds Conan's `export_sources()` hook to export the fixed
  license and any patches declared in conandata, then calls
  `apply_conandata_patches(self)`. `conandata.yml` intentionally keeps
  `patches: []`: the source needs no patch, so both patch helpers are no-ops for
  this package. H1-002 validated the recipe changes under its fixed candidate
  patch digest.
- The H1-001 upstream test input remains unchanged and its 11/11 result was
  reused for candidate 002; it was not rerun.
- G0 remains unresolved. No success is inferred from the W3 or Conan results.

### 对话 #7547：H1-002 实测结果（2026-09-28）

- Candidate 002 patch SHA-256:
  `8b457dbb91dceb12f18147781b85540abbebd28b54e76eb033e66ff232153329`.
- H1-002 reported G1/G2/G3/G4 PASS. Conan G2 downloaded the fixed sdist over
  HTTPS; its consumer passed 7/7 scenario groups and 17/17 literal assertions.
- Official W3 `setup.sh` and `build_and_test.sh` returned rc 0. The W3 consumer
  passed the same 7/7 groups and 17/17 assertions. This is the same one
  integration-test definition as G2, executed in two stages.
- The unchanged upstream suite remains 11/11 PASS from H1-001 and was reused;
  it was not rerun for candidate 002.
- G0 remains unresolved: the fixed source has no `configure`; `./configure`
  returned rc 127. It was non-blocking in `finish` but is still a recorded
  failure. The H1-002 `finish` and runner both returned rc 1, with final failed
  steps `step5b` and `step8`; no online CI pass is claimed.
- `reports/test-report.md` and the software-level `README.md` now record the
  results. H1-003 found the pinned CLI has no public `package` command. The
  pinned SKILL R19 instead requires Conan `create` + `upload` and forbids manual
  tar creation; H1-002 `create` passed, and upload is reserved for the post-merge
  release pipeline. The old finish log noted a missing `.staging-verified`
  marker, but R19/R20 deprecate this marker. The pure Python package contains
  no ELF debug symbols; no debug archive is part of the current Conan route.
- The original `finish` ended with failed steps `step5b` and `step8`. In that
  finish implementation, `step5b` is the W5 knowledge completeness check; its
  log identified missing required fields in global records E219, E253 and
  E305, none of which concerns itypes. The same log reported zero pending
  itypes knowledge gaps. This is evidence of an unrelated fixed-baseline W5
  problem; the recorded step5b failure remains unchanged.
  `step8` is submit readiness, whose captured missing items were the test
  report, `packaging/`, and `.staging-verified`. The report is now present, but
  packaging and staging entries belong to the legacy R19/R20 path. The original
  finish result remains rc 1 and has not been replayed.
- H1-002 raw evidence archive SHA-256:
  `a6838df4caa3a65ed9bff8d1bc9be8e407b33e9ccf0a4c932518edd73f95a561`.
- The contest task is tagged `cpp` while the fixed upstream source is Python.
  This is disclosed as a task-metadata and scoring risk for the normal human
  Conan route; no blanket language exemption or guaranteed score is claimed.
- The account's OpenHarmony project membership was verified on 2026-09-28 as
  active Developer/write. The receipt is kept outside the package at
  `members/gcw_tlRDjnsx/evidence/project-role-20260928.json`.
