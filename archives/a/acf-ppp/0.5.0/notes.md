# acf-ppp 0.5.0 adaptation notes

## Scope and source

- Issue: `#211`
- Upstream: Alpine Configuration Framework PPP module
- Official source: `acf-ppp-v0.5.0.tar.gz` from Alpine distfiles v3.24
- SHA-256: `4162282b3749221f51df02b631c499d79a345e98fb03c4760e5b9ab361b08565`
- SHA-512 was cross-checked against Alpine aports `main/acf-ppp/APKBUILD`.

## Build-system analysis

The project is a pure Lua/LSP ACF application. Its Makefile has an empty
`all` target and installs `ppp*` into `/usr/share/acf/app/ppp`; there is no
C/C++ compilation, configure step, or generated code.

The recipe uses Conan's `unknown` package type and exposes only resource
directories because it installs no CLI; the Lua runner is test-only and is not
part of the package.

The release contains 10 installed entries: two Lua modules, two regular LSP
views, four LSP symlinks to shared ACF views, and the menu/role declarations.
The symlinks intentionally remain dangling inside this standalone package and
resolve only when overlaid with the ACF framework resources.

HarmonyOS extraction drops those four dangling links, and HMDFS rejects new
symlink creation with `PermissionError`. The recipe therefore materializes
byte-identical copies from the declared `acf-core/0.24.1` package: three from
`filedetails-html.lsp` and one from `status-html.lsp`. No upstream Lua logic or
LSP template content is modified.

## W0 dependency result

Alpine's official APKBUILD declares `depends="acf-core ppp"`:

- `acf-core/0.24.1` and `acf-lib-lua5.4/0.11.1` are runtime requirements.
  acf-core supplies dispatcher/model helpers and shared views; acf-lib supplies
  `acf.fs`, `acf.processinfo`, and `acf.validator`.
- `ppp/2.5.2` is a hard runtime dependency. It was adapted independently under
  issue `#2118` and PR `#5226`, merged on 2026-08-17, and published by its
  successful release pipeline (`#2725`, including upload and signing).

Official acf-ppp CI `#26382` then resolved the complete dependency graph on a
healthy worker and passed L0, L1, and the Conan consumer test. Formal W0 is
therefore satisfied without mixing dependency changes into this PR.

The complete validation graph contains OHOS packages for
`acf-core/0.24.1`, `acf-lib-lua5.4/0.11.1`, `lua/5.4.8`, `ppp/2.5.2`, and
`openssl/3.5.6`. No dependency source or recipe is changed by this branch.

## Tests

Alpine aports explicitly sets `options="!check" # no test suite`, and the
release has no check/test target. The consumer test performs 28 assertions:

1. verifies six required regular package files;
2. compares four materialized views byte-for-byte with their acf-core sources;
3. verifies each of four materialized views with one regular-file assertion and
   one non-link assertion, for eight representation assertions;
4. verifies the test-only Lua runner built against the packaged Lua;
5. executes the packaged model/controller with isolated ACF service stubs;
6. exercises status/version, pppd detection, peer listing, PAP/CHAP paths, and
   controller dispatch through nine Lua assertions.

The functional test does not write `/etc/ppp`, launch `pppd`, require root, or
claim PPP/PPPoE connectivity.

## OHOS shadow CI result

The Path B candidate passed a single-package run on 2026-08-13 at commit
`3233ff08e867357d49bbab3ef55a6682ac500f49`. It restored checksum-verified
dependency packages into a fresh Conan home and built only acf-ppp.

```text
outer: /storage/Users/currentUser/ohos-test-runs/codex-acf-ppp-0.5.0-issue-211-path-b-shadow-ci-20260813-192825-29196
inner: /storage/Users/currentUser/ohpc-ci-shadow/runs/3233ff08e867-20260813T112828Z-run-29337
completed_at: 2026-08-13T11:28:59Z
```

Results:

- `conan create`: passed with the complete six-package dependency graph.
- `test_package`: 28/28 assertions passed, including four regular-file checks,
  four non-link checks, and 9 Lua functional checks.
- Four dependency-owned views were packaged as byte-identical regular files.
- Gates: L0, L1 and L4 passed; L2 skipped because there is no CLI executable.
- L5 warned because the generic baseline only recognizes `bin/` or `lib/`;
  acf-ppp intentionally packages Lua/LSP resources under `usr/share/acf`.
- Build summary: 1 total, 1 success, 0 failed, 100% pass rate.

This run validates the recipe and tests at snapshot `3233ff08e867`. Later
commits improve the resource materialization contract, evidence accounting, and
the non-CLI Conan classification. Implementation commit `24ebcc862a` passed the
complete official PR pipeline as CI `#26382`.

Formal reproduction:

```sh
CI_PACKAGES="archives/a/acf-ppp/0.5.0" zsh ci/conan/build_and_test.sh
```

## Path B reusable-knowledge candidate

The Path B request is not the generic observation that HMDFS rejects symlinks.
That behavior and same-package copy/wrapper mitigations already exist in E018,
E050 and E073. The new candidate covers a narrower unresolved package-graph
case: an upstream archive intentionally carries links that are dangling until
another package is overlaid at deployment time.

The recipe now resolves each immutable resource from the declared `acf-core`
Conan dependency, rejects source or destination path escape, rejects missing or
linked dependency inputs, removes any dangling destination safely, copies the
resolved file, and fails unless the result is a byte-identical regular file.
This prevents a successful build from silently omitting views and prevents a
stale local golden copy from drifting away from the selected dependency version.

The reusable algorithm, inputs, outputs, forbidden cases and verification
contract are in
`knowledge/drafts/E321-draft-acf-ppp-cross-package-resource-materialization.*`.
The novelty comparison and evidence are in `reports/path-b-evidence.md`. The
candidate is submitted for committee review and does not claim formal knowledge
registration before approval.

## Remaining runtime boundary

The recipe and non-privileged model/controller behavior are validated. A real
PPP/PPPoE link still requires a disposable privileged job with `pppd`, writable
`/etc/ppp` fixtures, `/dev/ppp`, and kernel PPP/PPPoX support. Do not run that
probe against shared host configuration. Dependency PR `#5226` merge and
package-publication ordering are now satisfied.
