# Test and build report — in-place 1.0.1

## Fixed input and target

- Source: `in_place-1.0.1.tar.gz`, 13,746 bytes, SHA-256 `4b0b2b9073c3e7a116f819f7f51711b56216b24b67be57cfcdfe717400bc8743`.
- Device: OpenHarmony 6.1.0.115, aarch64, Python 3.12.9.
- Conan: 2.29.1 with the `ohos-aarch64` profile.
- Package kind: pure Python; no executable or native library is produced.

## Results

| Check | Result | Scope and limits |
|---|---|---|
| Upstream pytest (H1-002) | 77 passed in 0.54 s | Full upstream `test/` suite on the fixed source, including all seven symlink cases. H1-005 did not rerun this unchanged suite. |
| Upstream consumer (H1-002) | Passed | One consumer scenario importing the module and rewriting a temporary file. |
| Conan verify (H1-005) | G1/G2 passed | Recipe completeness passed; real `conan create` completed source, syntax-only build, package, and `test_package`. |
| W3 local CI (H1-005) | Passed, 1 package | Setup and `build_and_test.sh` returned 0. L0, L1, and L4 passed; L2 skipped because there is no `bin/`; L5 warned because there are no `bin/` or `lib/` artifacts. |
| Conan consumer (H1-005) | Passed twice | The same single `consumer.py` scenario ran once in Conan verify and once in W3. It has one assertion; this is one distinct consumer scenario and two executions, not two distinct tests. |
| Official remote CI | Not run | Local W3 is not official CI. |

The H1-005 Conan report marks G4 pass but says no package ID was found; this report does not claim that a package ID was independently resolved. The W3 and Conan consumer outcomes are tied to the fixed candidate and source digest above.

## Framework gates and exceptions

- The framework's G0 clean-build step extracted the fixed sdist and returned 127 because this pure-Python source has no `./configure`; no C/C++ configure or make build is applicable. This is separate from Conan's G0 pre-build query.
- H1-005 `finish` returned 1, with recorded failing steps `step5b` and `step8`. In `step5b`, the global graph scan found missing fields in unrelated baseline entries E219, E253 and E305; the same report also found one local `manifest.yaml` knowledge item without a reference. This candidate now gives each knowledge item an explicit `knowledge_ref` and records both linked sources under a completed findings section. The original finish was not rerun, so this is a source correction, not a new gate pass. In `step8`, the historical report lacked `reports/test-report.md`, a software-level README, and legacy packaging/staging artifacts. The test report and version-scoped README are now present; the legacy tar/marker path is deprecated for Conan delivery by R19/R20 and the migration guide. The old software-level README check was not rerun, so no new finish pass is claimed. H1-005's actual Conan `create` package and W3 consumer evidence remains the relevant target package evidence; official release upload occurs after merge and is not claimed.
- A debug-symbol archive is not applicable: the real Conan package has only Python source, `py.typed`, and the MIT license, with no ELF files or debug symbols. No empty debug archive is claimed.
- `.staging-verified` was not produced by H1-005. The fixed migration guidance removes this legacy marker from the Conan delivery workflow; its absence is recorded, but this report does not treat it as a current Conan gate.
