# DRAFT - tetgen static library + CLI tool hybrid recipe

> Contributor: codex | Status: DRAFT | Created: 2026-09-21

## Scope

Use this when a C/C++ library also builds a command-line front-end — the way
tetgen ships `libtet.a` + `tetgen`, gts ships `libgts` + tools, and gd ships
`libgd` + 11 CLI tools.

## Symptom

```text
ERROR: tetgen/1.6.0: Package type is 'library', but no 'shared' option declared
```

## Root Cause

Conan 2 requires `package_type="library"` to declare a `shared` option. tetgen
upstream only builds a static archive (`libtet.a`), so there is no shared
variant to implement; the correct type is `static-library`. But the package
still emits a CLI binary, which must be declared for R38 and the L0k gate.

## Recommended Solution

1. `package_type = "static-library"` (no `shared` option needed).
2. Copy the CLI into `bin/` and set `self.cpp_info.bindirs = ["bin"]`.
3. Add a software-level `commands.json` with `"type": "tool"` (R38).
4. Set `self.cpp_info.libs` to the **archive basename**: `libtet.a` ->
   `["tet"]` (not `["tetgen"]`).
5. `self.cpp_info.system_libs = ["m"]` when the code links `libm`.

## Verification

tetgen/1.6.0 `conan create` passed L0 (L0j version collision + L0k
commands.json), L1 (test_package), L1e (destructive negative test), L2
(`tetgen --version`), L4, and L5:

```text
Build Summary: Total 1, Success 1, Failed 0
```

## Forbidden Shortcuts

- Do not declare `package_type="library"` without a `shared` option.
- Do not set `cpp_info.libs = ["tetgen"]` when the archive is `libtet.a`.
- Do not omit `commands.json` for a package whose `bin/` has content.

## Relation To Existing Knowledge

E307 covers the test_package cmake closure. This draft records the packaging
type/name mapping for "static library + CLI" hybrid packages, complementing the
gts/gd precedents already present in the archive.
