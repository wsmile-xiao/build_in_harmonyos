# Redis 8.2.7 path B knowledge-extension candidate

Date: 2026-08-16

## Submission position

Redis 8.2.7 completes path A on HarmonyOS 6.0/armv8 and is proposed as a path B
knowledge-extension candidate. Final classification belongs to project review.
The claim is not that Redis compatibility is new; `main` already has a Redis
8.6.0 recipe. The contribution is the reusable behavior and test evidence that
go beyond that recipe.

## Difference from the existing Redis adaptation

| Area | Existing behavior | Redis 8.2.7 contribution |
|---|---|---|
| Thread cancellation | No-op fallback reports success | Returns `ENOSYS`, so callers do not join a live thread |
| Compatibility scope | Platform-specific object patch | Libc capability guards with no fragile object-list edit |
| Scripts/tools | Relies on direct execution | Uses explicit shell and trusted system install tool on HarmonyFS |
| Package aliases | Relies on symlinks | Packages six real signed command files |
| Upstream tests | Version/smoke evidence | Runs default, Module API, Sentinel, and Cluster official suites |
| Capability gaps | Not explicitly counted | Per-test SIGSTOP accounting with fail-closed helper guard |
| Consumer coverage | Small service smoke test | 121 assertions across persistence, replication, failover, Sentinel, Cluster, ACL, scripting, and negative paths |

## Reusable findings

### Unsupported asynchronous operations must not report success

A fallback may return success only when the promised state transition happened.
Redis joins a thread after successful cancellation, so a success-returning no-op
can block indefinitely. Returning `ENOSYS` preserves the caller's error path.

### HarmonyFS mode bits do not guarantee direct execution

Readable archived scripts can fail direct execution because of ownership
mapping. Passing the script to an explicit shell makes the interpreter the
executed object. The same diagnosis led to `/system/bin/install` and regular
signed command aliases when symlink creation failed.

### Platform test exclusions must be fail-closed and observable

The HarmonyOS user session acknowledges SIGSTOP without suspending the process.
Skipping entire files would hide unrelated coverage. The adaptation identifies
only direct or coupled pause cases, increments visible skip totals, and fails if
an unaccounted pause helper is reached. This pattern is reusable for restricted
targets where a capability probe can succeed syntactically but not semantically.

### Target integration suites must exercise signed binaries

Redis tests launch source-tree server binaries. Signing after tests would make
the evidence irrelevant to the shipped ELF files. This recipe signs first,
runs all official entry points, and packages those exact binaries.

## Final evidence

- Tested commit: `de15e2c3afa3f1f91a76ca0e411dda9f0b048cb3`
- Final run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/de15e2c3afa3-20260816T093310Z-redis-tcl-run-4598`
- All official entry points: 4/4 pass
- Observed upstream result: 4,977 OK, 56 explicit capability skips, 0 errors
- Package test: 121/121 assertions
- Gates: L0/L1/L2/L4/L5 all pass
- Package result: 1/1 passed
- Cleanup: no Redis/Tcl process or Shadow lock remained

The 212 Tcl files are a source inventory, not 212 one-to-one assertions. Exact
runner units, skip names/categories, and replacement coverage are documented in
`upstream-tests.md`; hashes and failure convergence are in `W3-shadow-ci.md`.

## Review request

Review this PR as path A plus a path B knowledge-extension candidate based on:

- correct failure semantics for unsupported pthread cancellation;
- reusable HarmonyFS execution and packaging diagnosis;
- a signed-binary workflow for target-side upstream integration suites;
- fail-closed, per-test accounting for unavailable process suspension;
- complete device evidence and broad replacement integration coverage.
