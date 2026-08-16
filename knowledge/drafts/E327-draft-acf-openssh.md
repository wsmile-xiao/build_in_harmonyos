# E327 - Materialize Dependency-Owned Resources When Links Are Forbidden

## Symptom

An upstream package contains relative symbolic links for public resource names,
but the link targets are owned by a separate runtime dependency. Packaging on
the target produces one of two failures:

- archive extraction or recursive copy omits the dangling links; or
- explicit `symlink()` or `ln -s` fails with a permission error.

The resulting package is otherwise created successfully but is missing files
that consumers expect at stable public paths.

## Scope

Use this pattern only when all of the following are true:

- upstream public resources are links rather than independent files;
- each target is owned by a declared Conan runtime dependency;
- the target filesystem cannot preserve or create the links; and
- consumers need file content, not link identity or link mutation semantics.

Do not use this pattern for shared-library SONAME links, cyclic resource trees,
or links whose identity is part of the public API.

## Root Cause

The upstream installation assumes a merged filesystem hierarchy. A relative
link can traverse from one application directory to a shared resource installed
by another package. Conan packages isolate those owners, and HMDFS-like target
storage can additionally reject link creation. Reproducing the pathname alone
does not preserve the source ownership contract.

The portable contract is therefore the content selected by the exact resolved
dependency node, installed under the upstream consumer-facing filename.

## Solution

In the consumer recipe:

1. Declare the resource owner as a production requirement.
2. Resolve it through `self.dependencies["<dependency>"].package_folder`.
3. Define an explicit mapping from each upstream public filename to the
   dependency-owned source filename.
4. Reject a missing source rather than creating an empty placeholder.
5. Copy the source into the consumer package as a regular file.
6. Keep machine-specific Conan cache paths out of package metadata.

In `test_package`:

1. Resolve the same dependency node.
2. Require every public resource to be a regular file and not a symbolic link.
3. Compare each complete file with its dependency-owned source.
4. Verify the expected package inventory so a missing or extra resource cannot
   hide behind the mapped checks.
5. Keep content checks separate from runtime behavior tests.

A shell-level identity check can use:

```sh
test -f "$installed"
test ! -L "$installed"
cmp -s "$dependency_source" "$installed"
```

## Why Existence Checks Are Insufficient

A copied file can exist while containing content from an unrelated source-tree
path, a stale cache revision, or a wrongly mapped dependency file. Byte-level
identity binds the installed resource to the exact package revision in the
current Conan graph. For generated resources, use a semantic or digest contract
defined by the provider instead of assuming byte identity.

## Forbidden Shortcuts

- Do not retry `os.symlink` after the target filesystem has rejected it.
- Do not hard-code a Conan cache or device home path.
- Do not copy a same-named file from the consumer source tree when ownership
  belongs to a dependency.
- Do not create empty placeholders to satisfy layout checks.
- Do not count file existence as content correctness.
- Do not claim service-level or end-to-end behavior from resource identity.

## Verification Matrix

| Check | Expected result |
|------|-----------------|
| Dependency resolution | Exact declared provider node is present |
| Provider source | Required source exists and is a regular file |
| Consumer path | Expected upstream public filename exists |
| Link policy | Installed resource is not a symbolic link |
| Content identity | Full bytes match the provider source |
| Inventory | All expected resources, and no unintended entries |
| Runtime | Tested independently with real package dependencies |

## Source Evidence

`acf-openssh/0.11.2` has three public LSP resource names that upstream expresses
as relative links to shared ACF templates. On the OHOS target, copy omitted the
links and explicit `os.symlink` failed with `PermissionError`. The recipe now
materializes the corresponding files from the exact `acf-core/0.24.1` Conan
node. Its consumer test verifies regular-file layout and byte-compares all three
resources. A separate Lua 5.4 runner validates application behavior; those
functional checks are not counted as proof of resource identity.

## Related Knowledge

- E292 includes no-links pre-extraction for third-party FetchContent archives;
  it does not cover cross-package ownership or installed resource identity.
- E274, E316, and DRAFT-2045 cover shared-library SONAME compatibility names;
  dynamic-loader identity is not equivalent to static resource content.
- This entry covers links inside ordinary resource trees and derives replacement
  content from the exact resolved dependency rather than a consumer source tree.
