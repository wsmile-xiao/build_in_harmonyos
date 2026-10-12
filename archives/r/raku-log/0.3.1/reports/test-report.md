# raku-log 0.3.1 Test Report

## Source and upstream tests

- Upstream: https://git.tyil.nl/raku/log, tag `v0.3.1`
- Release archive SHA256: `7c5837fe116bcaa1710fc65ed7e2987272c1368c5e3943691fddaa638cf2b8dc`
- Upstream test inventory: 0 test files; the release archive and tagged tree contain no test directory.
- Upstream tests executed: 0 (none are supplied upstream).
- Upstream tests modified or omitted: none.

## Adaptation tests

| Test | Assertions | Result |
|---|---:|---|
| `test_module.raku` | 6 | Passed 6/6 |
| `test_ohos.raku` | 5 | Passed 5/5 |
| **Total** | **11** | **Passed 11/11** |

`test_module.raku` verifies the contiguous severity scale, role conformance, the
documented `with $Log::instance` guard idiom, a consumer-supplied implementation,
and callability of all eight log-level methods. `test_ohos.raku` verifies that the
runtime identifies the OHOS target (`$*KERNEL.name == 'harmonyos'`, HongMeng kernel
release, `aarch64`) and that UTF-8 data round-trips on the HarmonyOS cache
filesystem.

### Platform scoping of the applied test count

`test_ohos.raku` is gated on `os=OHOS` by `test_runner.py`, because its first three
assertions are HarmonyOS-specific by construction: MoarVM reports
`$*KERNEL.name` as `linux` on Linux and `harmonyos` on OHOS, so the test fails on a
generic Linux host. Consequently:

- **OHOS (the CI target profile `ohos-aarch64`)**: 11/11 assertions, both files.
- **Non-OHOS hosts**: 6/6 assertions, `test_module.raku` only.

The 11/11 figure below is therefore the OHOS result, not a cross-platform claim.

### Known coverage gap

The runner pins `MVM_JIT_DISABLE=1` (see `test_runner.py`), so the verified path is
the MoarVM interpreter path, not the JIT path a user gets by default. The recipe
does not set `MVM_JIT_DISABLE` for consumers — this is deliberate, since forcing it
would degrade unrelated packages through the shared runtime. JIT-enabled execution
on OHOS is consequently **not** covered by these tests.

## Upstream defect observed during test authoring

The role ships template-dispatch candidates that delegate to the single-argument
method via `$template.fmt(|@args)` (e.g. `Log::Implementation` `info(Str:D
$template, *@args)`). Raku's `Str.fmt` treats its first positional argument as the
**format string**, not as a value, so the call does not behave as the
sprintf-style API it resembles:

```
> 'value %d'.fmt(42)
Your printf-style directives specify 0 arguments, but 1 argument was supplied
```

The same request through `sprintf('value %d', 42)` correctly yields `value 42`. The
affected call path is therefore not exercised by the applied tests; this is a
documented upstream defect, not an adaptation regression, and is recorded in
`knowledge/drafts/E543-draft-DBC4.kv`. No upstream source was modified (the package
ships no patches).

## Conan verification

- Profile: `ci/conan/profiles/ohos-aarch64` (OHOS 6.0, armv8, clang 15).
- Command: `conan create archives/r/raku-log/0.3.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=raku-log/*`
- Result: package creation and test package passed; package reference `raku-log/0.3.1`.
- Runtime dependencies: published `rakudo/2025.11`, `nqp/2025.11`, and `moarvm/2025.11` recipes and matching OHOS/aarch64 binaries.
