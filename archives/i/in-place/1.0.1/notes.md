# in-place 1.0.1 adaptation notes

## Packaging

This is a pure-Python package with no runtime dependencies. The Conan recipe stages `src/in_place` under `python/in_place` and exports that directory through `PYTHONPATH`; it does not invoke the upstream Hatch build backend. The source distribution requires Python 3.8 or newer and contains the upstream tests.

The competition entry is currently tagged `cpp`, while the fixed upstream source is Python. The local language-entry review found that the current `lang-preflight` is defined under the AI Worker protocol; the human `CONTRIBUTING`/`submit` path does not call it. Two recent Python-source tasks with `cpp` labels, shortuuid #10578/[PR #12589](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12589) and socksio #10785/[PR #12611](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12611), were merged through that route. These are empirical precedents, not an official blanket exemption or a guarantee of this task's eligibility or points. This candidate preserves the source language and task label; the mismatch remains disclosed.

The recipe accepts `IN_PLACE_SOURCE_ARCHIVE` for an already staged source archive, verifies its SHA-256 against `conandata.yml`, and extracts that fixed input without a network fetch. Without the variable, it retains Conan's normal source download behavior.

## Verification state

On the fixed sdist, the upstream suite produced 65 passed and 5 skipped on the available Windows Python 3.11.0rc2 host when the symlink module was excluded. Running that module separately produced seven failures because Windows refused symlink creation with `WinError 1314`; this is an environment permission limitation, not a product assertion failure. The Conan-style consumer import and in-place rewrite check passed against the staged package layout.

H1-002 on OpenHarmony 6.1.0.115/aarch64 ran the complete upstream suite against the same source archive: 77 passed, including all seven symlink cases; the consumer rewrite check passed. H1-003 exposed missing Conan G1 hooks and W3 L0 settings; H1-004 confirmed both fixes, then exposed the `package_type = "library"`/missing `shared` option error. H1-005 verified the corrected pure-Python package with `package_type = "unknown"`: Conan G1/G2 passed, W3 returned 0, and one distinct consumer scenario passed in each flow. It did not rerun upstream pytest. H1-003/004/005 G0 reported that the source has no `./configure`; this is a separate non-applicable native step for this pure-Python source. The H1-005 Conan report marked G4 pass while noting no package ID was found. The host results above remain host-only and are not combined with H1 results. H1-005 `finish` returned 1: final `step5b` and `step8` failed. The step5b report included one locally unreferenced manifest item and unrelated pre-existing graph entries with missing fields; step8 lacked ordinary report/README materials and also ran deprecated legacy packaging and staging-marker checks. These details are reported separately; this is not a complete finish.

## Knowledge references and findings

- ✅ [Pure-Python Conan packaging draft](../../../../knowledge/drafts/DRAFT-pyjson5-0.15.0-pure-python-no-build-packaging.kv) is a relevant pattern; its CLI wrapper and Python runtime dependency do not apply to this package.
- ✅ [E277](../../../../knowledge/graph/E277.kv) matches the `library` without `shared` Conan error signature. Its vendored/static remedy does not apply; H1-005 verified `package_type = "unknown"`.

## Packaging and submission state

The H1-005 Conan `create` produced a real package containing `python/in_place/__init__.py`, `python/in_place/py.typed`, and `licenses/LICENSE`; W3 independently rebuilt and consumed it. Under the fixed framework's Conan workflow, this is the PR-stage package artifact. R19/R20 deprecate the legacy tarball builder; release upload occurs after merge and is not claimed here. The legacy `.verify-passed` and `.staging-verified` markers were not produced and are not claimed as current Conan-workflow gates. H1-006, which requested the deprecated legacy packager, was withdrawn before dispatch. `compileall` may create `__pycache__` under Conan's source cache; the recipe packages only `*.py` and `py.typed`, and H1-005's actual package file list contained no `.pyc` files. No debug-symbol tarball is applicable because the package contains no ELF file.

状态: built

### 对话 #7457

- 2026-09-28: H1-002 completed upstream pytest (77/77, including symlink tests) and one consumer scenario.
- 2026-09-28: H1-003 exposed G1/L0 recipe gates; H1-004 exposed Conan package-type consistency. Both original failures remain in their evidence records.
- 2026-09-28: H1-005 passed Conan G1/G2 and W3; the same one consumer scenario passed once in each. Finish remained partial because G0 lacks `./configure` and archive/submit materials were incomplete.
