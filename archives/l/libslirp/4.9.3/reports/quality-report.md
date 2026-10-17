# libslirp 4.9.3 quality report

**Verdict: LOCAL AND TARGET GATES PASS; PR GATES PENDING**

## Confirmed

- Official tag `v4.9.3`, release commit
  `dd76415fce457e319d665eb8210d05c5731360ba`, and archive SHA-256
  `ee698ca4ce05217ca7d520c7f0b1b1228fd7d32922dd32d1051c347152588417`
  are bound.
- `glib/2.84.0` recipe revision
  `f67d99412319fab1849399b3878a424c` passed W0 availability checks.
- The portability patch applies once to a fresh source tree, rejects a second
  application, passes reverse-check, and leaves `git diff --check` clean.
- Python AST parsing, YAML parsing, and the repository L0 pre-commit gate pass.
- The post-sync current-main L0 hook reports zero warnings and zero errors for
  `archives/l/libslirp/4.9.3`.
- Fresh fallback-device r3 completed real G2 and W3 `conan create` runs. The
  W3 stage passed upstream `2/2`, consumer `1/1`, and generated an authentic
  `.ci-result.json` with exit code 0.
- Fresh primary-device r4 independently completed the standard CI build/test
  script with exit code 0. L0, L1, the L1 destructive test, L4, and L5 passed;
  upstream `2/2` and consumer `1/1` passed.
- Both devices produced byte-identical AArch64 shared libraries. Each package
  has one real `libslirp.so`, no library symlink, and one `.codesign` section.
- Independent W4 passed for frozen input HEAD
  `0502bd41545d4e97d4aeaa35d400736a3accf662`: P0=0, P1=0, P2=1, P3=0.
  The P2 is the upstream-deprecated poll compatibility API retained to keep
  the target-validated consumer snapshot exact.
- Frozen evidence bundle SHA-256 values are
  `34254c2ede3bacd9100c4e69238515da54d5ecd463d24ae293ad298274107664`
  and
  `fa70010e0f983d31b96b567c4bde91d88c466e5caf4a2f044d753de8ed842d3a`.

## Evidence boundary

The fallback-device `finish` outer process returned 1 after G2 and W3 passed
because the historical close/readiness implementation still checks
deprecated `packaging/` and `.staging-verified` artifacts and treats the
reduced target snapshot as the complete repository graph. Those legacy files
were not fabricated. The finish-generated W3 result and independent primary
pipeline are retained as the actual build/test evidence.

The v4.9.3 native-host tests were not run. No older-version host or target
result is counted for this version.

W5 was executed against the current tree. It found matching graph, document,
and index counts (`214/214/214`), then reported 123 schema errors and 91
warnings in pre-existing graph entries. This PR changes no file under
`knowledge/**`, so the repository-wide baseline findings are recorded but are
not repaired in this atomic dependency PR.

## Blocking gates

- Current-HEAD Review, all discussions resolved, and official CI bound to the
  complete revision and PR number.
- PR-view submission readback and merge-triggered publication before DOSBox
  Staging resumes.
