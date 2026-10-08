# WCD state root and scan root differ; exit zero can hide unwritable go script

Status: knowledge-base extension candidate for maintainer review. This is a
portable test/packaging lesson drawn from a HarmonyOS PC case, not an assertion
of automatic Path B points or difficulty rating.

## Symptom and cause

On the restricted SSH account, `wcd --version` emits
`Unable to write file /storage/Users/currentUser/bin/wcd.go: Permission denied`
while returning exit code 0. It is therefore unsafe to treat a zero exit code
or the version banner alone as proof of a working shell directory changer.
WCD writes a shell fragment `bin/wcd.go`; a sourced function must execute
that fragment in the caller's shell, since the CLI process cannot change its
parent's working directory.

The upstream 6.0.6 manual documents that `WCDHOME` redirects WCD state files.
Since WCD 5.1.5, it does **not** change the default directory scanned; `-S`
or `WCDSCAN` must be used separately to bound discovery. This distinction
matters when an app-private writable state directory is needed while the
ordinary `HOME` remains shared and unwritable.

## Reusable diagnosis and fix

1. Reproduce the command without `WCDHOME`, capture stderr and exit status,
   and check whether the go script was actually created.
2. Set `WCDHOME` to an application-owned private directory. Select scan roots
   separately with `wcd -S <tree>` or `WCDSCAN`; do not assume the state root
   affects discovery.
3. Package or source a shell function that runs WCD and sources the generated
   `wcd.go`. In a consumer test outside the source tree, inspect the state
   files and assert the caller's final `pwd`, not merely command exit status.

## Evidence and scope

- Official source SHA-256:
  `c5d1b22aefbb0f142e27b1cddad17021c43034c76103830fb2757387ac593eb1`.
  Target: `/data/storage/el2/base/haps/entry/files/wcd-6.0.6-20260926T190000`.
- Without `WCDHOME`, `wcd --version` emitted the permission error and RC 0;
  with `WCDHOME=<private>/smoke/home`, the same command returned 0 without
  the error. Both logs and checksums are in the target verification root.
- `conan create` passed the external installed-package consumer test and
  printed `WCD packaged binary, isolated scan, go script and shell function: PASS`.
  Full log checksum and package revision are in the recipe `notes.md`.
- The upstream manual itself documents `WCDHOME`/`WCDSCAN`; the proposed
  incremental knowledge is the restricted-account failure, exit-status trap,
  and end-to-end verification method. If an existing entry already covers
  those, this should be merged rather than counted twice.

This does not demonstrate curses/NLS support, unrestricted account behavior,
or direct target download from SourceForge.
