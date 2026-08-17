# E321 - Materialize immutable cross-package resources when HMDFS cannot preserve dangling links

## Error signature

This pattern was observed while packaging `acf-ppp/0.5.0`:

- an upstream archive contains relative symbolic links whose targets belong to
  a separate runtime package;
- the links are dangling before deployment overlay and disappear during source
  extraction; or
- recreating them on HMDFS raises `PermissionError` / `Operation not permitted`;
- the build still succeeds, but packaged application resources are missing.

## Trigger conditions

Use this pattern only when all conditions hold:

1. The target is immutable data, not an executable entry point.
2. The target is owned by a declared Conan dependency.
3. Byte-for-byte copying preserves application semantics.
4. The resource is small enough that duplication is acceptable.
5. A consumer test can compare the result with the resolved dependency.

## Root cause

Some package ecosystems assemble a shared filesystem namespace only after
independently built packages are installed together. A relative link can
therefore be intentionally dangling inside the source or package that owns the
link. Conan builds each package into a separate root, and HMDFS may reject or
drop the link before the other package is overlaid. Generic `cp $(readlink -f)`
cannot resolve a target that is absent from the current package root.

## Inputs and outputs

Inputs:

- declared dependency package root;
- dependency-relative immutable resource root;
- destination package root; and
- explicit destination-to-source mapping.

Outputs:

- one byte-identical regular file per mapping;
- deterministic content from the dependency version selected by Conan; and
- no runtime dependency on link creation or traversal.

## Recommended approach

Implement a fail-closed materialization helper in the Conan recipe:

1. Resolve the dependency root and source with `os.path.realpath()`.
2. Reject source paths outside the dependency root with
   `os.path.commonpath()`.
3. Check both the lexical destination and its resolved parent remain under the
   destination root.
4. Require the source to be a regular non-link file.
5. Use `os.path.lexists()` and `os.unlink()` before copying so `shutil.copy2()`
   cannot follow a pre-existing destination link.
6. Copy with `shutil.copy2()`.
7. Require a regular non-link destination and verify byte identity using
   `filecmp.cmp(..., shallow=False)`.

The mapping must be explicit. Do not infer arbitrary link targets from an
untrusted archive and do not search system paths for a same-named file.

## Consumer verification

For every materialized resource, verify content and representation:

```sh
cmp -s "$package_file" "$dependency_file"
test -f "$package_file"
test ! -L "$package_file"
```

The comparison catches stale embedded copies and dependency-version drift. The
representation checks prove the package does not rely on unsupported HMDFS link
semantics.

## Forbidden approaches

- Do not silently ignore link creation failures.
- Do not create empty placeholders for omitted links.
- Do not embed an unversioned duplicate golden file in the target recipe.
- Do not copy from undeclared system locations.
- Do not materialize mutable configuration, sockets, devices, identity files,
  large datasets or resources whose link identity is observable.

Use wrappers for executable aliases. Use deployment overlays or redesign file
ownership when content is mutable or duplication changes semantics.

## Difference from existing knowledge

- E018 covers generic link creation failures and wrapper/copy fallback.
- E050 covers a shared-library alias whose real file is in the same package.
- E073 covers runtime loader failure through shared-library links.

E321 adds dependency-graph resolution for intentionally dangling cross-package
resource links, plus containment and dependency-version identity checks. It
reuses, rather than replaces, the HMDFS premise in those entries.

## Validated example

`acf-ppp/0.5.0` maps three edit views to the selected
`acf-core/0.24.1:filedetails-html.lsp` and one status view to
`acf-core/0.24.1:status-html.lsp`. Snapshot
`3233ff08e867357d49bbab3ef55a6682ac500f49` passed single-package HarmonyOS
shadow CI with 28/28 assertions: four byte comparisons, four regular-file
checks, four non-link checks, nine Lua functional checks, six base-file checks
and one Lua runner check. This isolated-cache result validates the pattern but
does not replace formal dependency publication W0.

## Related entries

- E018: generic symlink creation failure.
- E050: same-package shared-library alias copy.
- E073: shared-library runtime symlink failure.
