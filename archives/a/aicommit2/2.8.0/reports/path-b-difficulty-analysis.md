# aicommit2 2.8.0 path B difficulty analysis

## Scope

- Library: `aicommit2`
- Upstream: `https://github.com/tak-bro/aicommit2`
- Release: `2.8.0`
- Release archive SHA256: `a5d30aedbebe8ae9017f1ef86bfdb5d3e2cc20ef3a5a999a14e88450ba28a96c`
- Adaptation path: A (basic adaptation) + B (knowledge-base extension)
- Difficulty classification: B
- No separate Conan dependency PR is required. Node.js and npm are runtime/build
  prerequisites, not a library dependency added to this package.

## Reusable problem boundary

This release is a prebuilt ESM Node.js CLI. The npm tarball contains `dist/` but
does not contain `node_modules`, so a package recipe that only unpacks the
release is incomplete. The production dependency tree must be installed during
the build with lifecycle scripts disabled.

The validated HarmonyOS device exposed three independent runtime boundaries:

1. HNP supplies Node.js and npm outside the default non-interactive PATH. The
   build accepts explicit `AICOMMIT2_NODE` and `AICOMMIT2_NPM_CLI` paths instead
   of adding a device-specific dependency to this PR.
2. npm's normal executable-link step is not usable on HMDFS. `--no-bin-links`
   keeps installation deterministic without relying on symlink materialization.
3. The shadow L5 scanner recursively sees dependency-internal `lib/` directories
   as native library artifacts. The package stores the complete npm tree in
   `res/aicommit2.tar.gz`; the launcher extracts it into `TMPDIR` on demand.

The cached launcher is also not directly executable by the shadow runner on
HMDFS. The test package therefore runs the actual package launcher through
`sh`, while the L2 result remains an explicit non-blocking skip. This separates
the shell execution restriction from package functionality and avoids claiming
an unexecuted runtime assertion as passed.

## Validation evidence

Shadow CI #29189 completed successfully on the HarmonyOS aarch64
device (address withheld from public report):

```text
RUN_DIR=<redacted single-package runner directory>
Total: 1
L0_RESULT=pass
L1_RESULT=pass
L4_RESULT=pass
L5_RESULT=pass
package success=1/1
exit code=0
ci-metadata.json=generated
```

L2 was explicitly skipped because direct execution of the cached launcher is
restricted by HMDFS. The Conan consumer test still ran the package-owned
launcher through `sh`; direct device checks also returned `2.8.0` for
`--version` and `aicommit2 config --help`.

The follow-up correction changes only manifest command metadata and B-class
documentation. The recipe and test-package content validated by Shadow CI
#29189 are unchanged.

## Test completeness and limits

- Exact upstream source: npm `gitHead`
  `57ee029ecc9e22b4373b8a4dc6cff96caa043dda`, with all retrieved files checked
  against official GitHub blob hashes.
- Official upstream command: `pnpm build && pnpm test`.
- Upstream result reproduced twice on Windows: 377 passed, 3 failed, 380 total,
  raw pass rate 99.21%.
- The three failures are Windows-only boundaries: two LF/CRLF exact-string
  expectations and one `EBUSY` fixture cleanup after test assertions complete.
- Upstream skips credential-backed provider suites when credentials are absent
  and skips TTY cases on Windows; these are upstream runner exclusions, not
  counted as package passes.
- Official npm release smoke checks: 4/4 passed (100%).
- Conan consumer checks: 5/5 passed (100%).
- HarmonyOS package-specific total: 9/9 passed (100%).
- The B-class claim is for the reusable npm/HNP/HMDFS packaging and validation
  boundary; it is not a claim that provider-specific commands are fully tested.

## Review request

Please review this as a B-class knowledge-base extension. The reusable result
is the artifact-first packaging rule for Node.js CLIs on HarmonyOS: validate the
production dependency tree, make the launcher relocatable, isolate nested npm
directories from native-artifact scanners, and report HMDFS execution limits
without weakening the functional test boundary.
