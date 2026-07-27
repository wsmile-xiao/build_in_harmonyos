# E240 - Test protocol data at generator and discovery boundaries

> Contributor: 1catmint1 | Status: DRAFT | Created: 2026-07-20

## Symptom

A protocol-data package has the expected XML or schema files and its upstream
schema command passes, but a downstream binding generator still fails after
installation. Typical failures include a missing imported document, an
expression or type that cannot resolve, Python modules installed outside the
exported search path, or pkg-config variables that still contain the build
prefix.

## Root cause

These packages expose several independent contracts even though they produce
no ELF library:

1. The document inventory must match the upstream release.
2. Each document must satisfy the schema.
3. The real generator must register imports and resolve document semantics.
4. Public generator helpers must retain their documented behavior.
5. Installed language and pkg-config discovery must resolve inside the package.

A file-count assertion covers only the first contract. A single schema command
covers syntax and structure but not generator semantics or installed search
paths. Importing one helper module likewise does not prove that every protocol
input can drive code generation.

## Fix

Build a non-duplicating matrix around installed artifacts:

1. Derive and lock the exact protocol-document and generator-module
   inventories from upstream installation definitions.
2. Keep the upstream schema command unchanged and report it as its upstream
   entry, including an explicit SKIP when its optional validator is absent.
3. Start one generator process for each distinct installed protocol document.
   Register imports, resolve types and expressions, and fail with the document
   name so every input has its own failure boundary.
4. Add separate fixtures only for genuinely different public API branches,
   such as alignment arithmetic, expression tags, namespace kinds, generator
   callbacks, and documented failure behavior.
5. Add one installed-package workflow that checks exact inventories,
   relocatable metadata, and that the language import resolves from the
   package rather than an accidental system copy.

Do not count the same XML again merely because schema and generator checks both
run, do not repeat a data package under shared/static labels, and do not turn
multiple assertions in one fixture into separate test cases.

## Validation

xcb-proto 1.17.0 preserved the upstream XSD check, which validated all 32 XML
documents on HarmonyOS. Its Conan test package then launched 32 independent
installed `xcbgen.Module` register/resolve processes, 22 unique public API
fixtures, and one installed discovery workflow. All 55 adapted workflows
passed. The package contained exactly 32 XML files, one XSD, seven Python
modules, and one relocatable pkg-config module.

## Related knowledge

No equivalent formal entry exists in the current main branch. This draft is
self-contained and does not depend on an unmerged knowledge identifier.
