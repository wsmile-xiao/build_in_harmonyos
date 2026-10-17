# E2174: Resolve OHOS signing tools from the frozen task closure

## Symptom

An OHOS Conan recipe compiles and links successfully, then fails in
`package()` with shell status 127 because `binary-sign-tool` or `llvm-objcopy`
is not present at a hard-coded system path. The target may expose the same
tools under the task user's local tool directory.

## Root cause

Signing utilities are part of the target toolchain boundary, not a guaranteed
system HNP installation. A recipe that assumes `/data/service/hnp/bin` can
pass all compile steps while failing only after install, when the package ELF
must be signed.

## Fix

1. Resolve each required tool in a deterministic order: Conan compiler
   configuration, PATH, the compiler's directory, the task-owned user-local
   `usr/local/bin`, then a system fallback.
2. Check that both resolved paths are regular executable files and fail closed
   before modifying package outputs if either tool is missing.
3. Invoke the tools with shell-safe quoting and record the resolved paths in
   the package log.
4. If the target truly lacks a tool, transfer a frozen, SHA-256-bound tool
   closure into the task-owned root/bin and validate mode, version, and hash;
   never write shared HNP directories.
5. Regenerate a create-new W3 freeze after any resolver or tool-closure change.

## Validation

libavif 1.4.2 r5 built the shared library but failed at the hard-coded
`/data/service/hnp/bin/binary-sign-tool` path. A read-only target probe showed
both tools at `/storage/Users/currentUser/usr/local/bin`. The resolver repair
selected those paths; the subsequent target run signed `libavif.so.16.4.2`,
completed `conan create`, executed the upstream CTest inventory at 3/3, and
passed the Conan test package.

## Applicability and safety boundaries

This applies to OHOS recipes that sign ELF outputs on targets with
task-provided tools or partial system images. It does not permit ignoring
signing failures, copying tools into shared system directories, or reusing a
W3 transaction after changing the resolver or tool closure. A final result
must be tied to the regenerated recipe, tool paths, and target receipt.
