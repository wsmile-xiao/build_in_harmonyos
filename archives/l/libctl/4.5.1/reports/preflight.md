# libctl 4.5.1 preflight (2026-09-25)

Status: target-device Conan build, upstream `test-prism` 1/1, and installed-package consumer 1/1 passed. See `test-report.md` for exact run hashes and limitations. This is not a claim of platform CI or publication.

- Task #8151; branch `feat/libctl-4.5.1`; team 诶，云朵.
- Upstream archive SHA-256: `fcfeb2f13dda05b560f0ec6872757d9318fdfe8f4bc587eb2053a29ba328ae25`.
- The OHOS armv8 Conan graph resolved Guile and all direct dependencies from `ohpcd` without `info_invalid`.
- Recipe Python syntax and frozen runner/status/recovery/release/postrelease/validator shell syntax passed before the final device run. All nine frozen input hashes and exact-byte transfer/readback passed.
- The final target run `libctl-w3-20260925T092800Z` ended with `W3_VALIDATOR_PASS` and `conan create` RC 0. The private transaction record and exact Conan log are retained in the task-local evidence directory, not the repository.
- The B-path knowledge draft addresses the missing public Guile umbrella header and downstream Conan header propagation. Existing HMDFS `config.status` knowledge already covers the temporary-directory issue; it is not claimed as a new discovery.
