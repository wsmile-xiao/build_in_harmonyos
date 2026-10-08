# puremagic 2.2.0

## Source and scope

- Upstream: https://github.com/cdgriffith/puremagic, PyPI source distribution.
- Fixed source: `puremagic-2.2.0.tar.gz`, 1,189,752 bytes,
  SHA-256 `eb4bddf07c177c4b434554b92165b67449f5a51e152b976202d6254498810eef`.
- `pyproject.toml` declares Python `>=3.12`; the library has no runtime
  dependencies and consists of the `puremagic` Python package plus its JSON
  signature database.
- The task board language is `cpp`, while the source is Python. This is being
  prepared through the existing human contest contribution route and disclosed
  as an eligibility risk; no platform tag or language gate is changed.

## Adaptation

The Conan recipe verifies a supplied local source archive against the fixed
SHA-256 or downloads the same upstream sdist, compiles the Python modules, and
packages the Python files, signature database, and MIT license. It exposes the
module through Conan's `PYTHONPATH` run environment. No source patch or runtime
dependency is required.

## Test inventory and evidence

The unmodified upstream suite consists of 66 tests in `test/test_scanners.py`
and 29 in `test/test_common_extensions.py`.

- Python 3.12.14 local run: **95/95 passed** with pytest 9.0.2 loaded from the
  existing offline test-runtime ZIP (SHA-256
  `9d8efee5250a6ae4ea0b2356eb3d79b54091d68b4473802091283bb1e475adc1`). The
  ZIP passed its CRC check and contains pure-Python modules only; pytest was
  loaded through `PYTHONPATH`, not installed. This is a new run against the
  fixed puremagic source, not a result reused from the task that supplied the
  test-runtime ZIP.
- H1-002 target suite: **not run**. The target Python is 3.12.9, but its
  existing environment has no pytest. No dependency was installed. Request
  #003 asks to rerun the two files with the same hash-pinned, test-only ZIP via
  `PYTHONPATH`.
- H1-002 target package: Conan setup and `conan create` both returned 0 on
  OHOS 6.0/armv8. The real package consumer passed four scenarios and four
  assertions. Its 17 Python files, JSON signature database, and MIT license
  (18 runtime files) matched the fixed sdist file-by-file by SHA-256. Conan
  package reference:
  `puremagic/2.2.0#2514b55aac812af981693977d013db85:da39a3ee5e6b4b0d3255bfef95601890afd80709#c915ed033e4e2c47150dd52bc063037c`.
- Earlier Python 3.11 pytest 9.0.2 result: **95/95 exploratory only** because
  Python 3.11 is below the upstream minimum. It is not used as target evidence.

The test-only runtime ZIP came from an existing second-account task artifact;
its hash and archive contents were independently checked. It is not included in
the Conan package or declared as a runtime dependency.

## Remaining validation

H1 #003 ran the target upstream tests and W3 successfully. Its overall
`finish` returned rc 1 and reported failed steps `step3`, `step5b`, and
`step8`. The G0 log specifically says the original tarball was not found at
the expected location; it did not reach a configure/make attempt. Separately,
inventory of the fixed sdist shows neither `configure`/`configure.ac` nor
Makefile/Makefile.in, indicating that the legacy clean-build expectation does
not match this pure Python source. Keep this source-shape observation distinct
from the logged G0 failure. H1 #003's G1 report failed its static checks for
the standard Conan patch hooks. Those standard hooks were added with an empty
patch list and then exercised by H1 #004's successful real Conan create.

H1 #004 ran one targeted `conan create` on OHOS 6.0/aarch64 and returned rc 0.
Conan called `export_sources()`, `export_conandata_patches()` and
`apply_conandata_patches()`; no patches were defined. The real consumer passed
4 scenarios, 4 API calls and 4 assertions. Package reference:
`puremagic/2.2.0#589899285f20ac01d1e8b745fe341981:da39a3ee5e6b4b0d3255bfef95601890afd80709#c915ed033e4e2c47150dd52bc063037c`.
H1 #004 did not rerun G1, upstream pytest, W3, full `finish`, submission
preflight or official CI. H1 #003's 95/95 and W3 pass remain historical
evidence for its earlier candidate tree; its full `finish rc 1` remains
unchanged. Manifest status remains `pending`.

### 对话 #003

- 2026-09-27: H1 #003 confirmed target pytest 95/95, W3 pass, Conan consumer
  4/4, and reported `finish` rc 1. The raw G0/G1/finalize outcomes and the
  fixed-source build-system mismatch are retained without reclassification.
- 2026-09-28: added only the standard no-op Conan patch hooks requested by G1.
  No source behavior, patch list, or manifest status changed. H1 #004 then
  confirmed one target Conan create and the four-scenario consumer passed; the
  original H1 #003 W3/95 and finish rc 1 remain tied to their original tree.
