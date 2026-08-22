# E2154 - Register optional AppConfig variables before guarding their values

> Contributor: 2301_80739235 | Status: DRAFT | Created: 2026-08-21

## Symptom

A Perl application treats a configuration key as optional and guards the
returned value before lowercasing it. When the key is omitted, the valid path
still emits a diagnostic such as:

```text
debug: no such variable
```

The process may otherwise continue, so an integration test that requires clean
stderr exposes the defect more reliably than an exit-code-only check.

## Root cause

AppConfig validates an accessor name before it returns a value. A caller-side
expression such as `defined($config->debug())` invokes the accessor first. If
`debug` was never registered in the AppConfig definition, the diagnostic is
already emitted before `defined` can protect the later string operation.

Variable registration and value normalization are different contracts. The
schema must know the optional variable, and the consumer must still handle an
omitted or undefined value safely.

## Recommended solution

1. Register the optional variable in the AppConfig definition before reading
   configuration, using the intended inherited or empty default.
2. Keep a separate defined-value guard before `lc`, comparison,
   interpolation, or other string operations.
3. Test an omitted-key configuration through the packaged runtime and require
   exit code 0 plus zero stderr.
4. Test an explicit value to prove the registered option still controls the
   intended behavior.
5. Test an unrelated unknown accessor and require the exact AppConfig
   `no such variable` diagnostic, proving the fix did not globally suppress
   diagnostics. Applications that intentionally enable AppConfig `CREATE`
   may still accept dynamic configuration keys, so key acceptance alone is
   not a valid oracle for this boundary.

For Flamethrower 0.1.8, patch 0011 registers `debug` with the existing empty
default and patch 0010 independently protects the lowercasing path. The host
consumer and an authorized OpenHarmony target W3 both passed with zero-byte
test stderr on the diagnosis snapshot.

## Verification

A diagnosis snapshot used AppConfig/1.71.1 from `ohpcd` and produced a real
Flamethrower package and consumer. Its authorized device run launched once,
returned runner exit code 0, printed both wrapper version markers and the
module/consumer success markers, and produced zero-byte test stderr. The task
root was then removed and independently read back as absent.

Exact package and W3 identities remain in external hash-bound receipts. They
must be regenerated after any committable candidate change and are not made
self-referential inside this draft.

## Safety boundaries

- Do not silence stderr or warnings globally; genuine unknown variables must
  remain visible.
- Do not register arbitrary misspellings merely to make a test pass. The
  variable must be part of the application's real configuration contract.
- Registration does not replace undefined-value handling when a provider can
  still return no value.
- A host consumer is not a substitute for an authorized target W3.
- This rule does not prove W4, W5, PR, CI, submission, or publication for a
  package that has not passed those independent gates.

## Difference from current knowledge

The existing AppConfig entry for Flamethrower explains Debian patch-root
normalization and `ARGCOUNT_LIST` array-reference handling. It does not cover
an unregistered optional accessor, the ordering of schema registration before
value guards, or clean-stderr validation for an omitted scalar setting.

Bounded searches of `knowledge/graph`, `knowledge/drafts`, `knowledge/doc`,
and `knowledge/operations` found no equivalent rule for AppConfig optional
variable registration or the exact `no such variable` signature. This draft
adds that missing reusable contract without replacing the existing list-value
entry.
