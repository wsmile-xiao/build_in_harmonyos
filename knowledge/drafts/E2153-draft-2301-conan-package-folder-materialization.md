# E2153 - Bind Conan graph identity to install package materialization

> Contributor: 2301_80739235 | Status: DRAFT | Created: 2026-08-19

## Symptom

A fresh `--build=never` run resolves a package with complete recipe revision,
package ID, package revision, remote, and no invalid or missing node. A
post-run validator still rejects it because the matching `conan graph info`
node has `package_folder: null`.

HarfBuzz 14.3.1 r6 exposed this after its build, complete Meson suite, package,
and consumer had run. The failed validator classification is preserved.

## Root cause

`conan graph info` proves dependency resolution; it is not the package
consumption operation. Its JSON can identify the exact binary without exposing
a local package folder. `conan install` materializes or reuses that binary in
the isolated cache and reports the folder needed for artifact inspection.

The `path` field in a separately generated package inventory names individual
files. It is not a renamed or fallback form of Conan's `package_folder`.

## Recommended solution

1. Use one new task-isolated Conan home and identical OHOS/arm64 profiles for
   `graph info` and `install`, both with `--build=never`.
2. Parse both JSON documents and join the package by full name/version, RREV,
   PID, and PREV. Reject any mismatch.
3. Require graph topology, options, `info_invalid`, `Missing`, binary state,
   and remote attribution to pass. Allow only its `package_folder` to be null.
4. Require the matching install node to expose a nonempty `package_folder`,
   then inventory and consume files strictly below it.
5. Hash-bind both raw documents, return codes, isolated home, and the derived
   result. Correct a validator offline instead of rerunning a completed build.

## Verification

HarfBuzz r7 used shared package identity:

- RREV `d95aa2283a886e19705accd5a38c7aa9`;
- PID `02e364f2d646dda8acabc40d95696553e6e53235`;
- PREV `1ac65b51d4fb18288f6913c88114e961`.

The graph node kept `package_folder=null`; the install node had the folder.
The validator then verified 63 package files, 15 ordinary signed `.so` alias
files, 75/75 upstream Meson tests, and the real shaping/fetch consumer. The
collected result summary SHA-256 is
`edb87894926b00dcaf04e2c9455e35d79813f4ad6e8a8b53dbfdf0a6207d7937`.

## Safety boundaries

- Never use this rule to waive RREV/PID/PREV, remote, invalid-node, missing-node,
  binary retrieval, or artifact checks.
- Never accept `--build=missing` when provider publication is the gate.
- Never borrow a folder from another Conan home or another package identity.
- An offline schema correction cannot rewrite immutable logs or turn a real
  build/test failure into PASS.

## Difference from current main

At `origin/main` `a9b0a14269e3225f770f00415345e30fc2e6ab2a`, searches across
`knowledge/graph`, `knowledge/drafts`, `knowledge/doc`, and
`knowledge/operations` found general recipe-time `package_folder` uses and one
unrelated `graph info` reference, but no rule that separates graph identity
from install-time package materialization or cross-binds the two schemas.
The incremental `172e5480..a9b0a142` interval contains eight commits, including
four non-merge Alpine, Aladin, globus-common, and QuantLib content commits. Its
six knowledge draft paths cover Boost.Math long-double promotion, Java
environments without unzip, and the Conan settings L0p shape; none covers
graph/install package-folder materialization or the exact RREV/PID/PREV join.
The preceding `f2c4bf2c..172e5480` interval contains four commits, including
three non-merge miniserve and R41 documentation/tooling commits, and changes no
paths in the four knowledge scopes. The earlier `c6656396..f2c4bf2c` interval
contains two commits, including one non-merge lttoolbox content commit, and
also changes no paths in the four knowledge scopes. The
`f7f57bfa..c3a1e462` interval contains 100 commits and changes 18 knowledge
draft paths. Those additions cover topics such as dependency-version
reconciliation, tool relocation, runtime-library closure, and resource
materialization. In particular, E2145 requires a package-folder check after a
provider-version migration, but it does not describe a complete graph node with
`package_folder=null` or the exact graph/install identity join. No incoming
entry is semantically equivalent to this rule. Open PR 5810 owns `E2152` for a
different libpng rule; the all-open-PR scan found `E2153` unused, so this draft
is reallocated without claiming semantic equivalence or changing the other task.
This is a path B draft; no path C claim is made.
