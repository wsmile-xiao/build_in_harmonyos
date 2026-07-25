# E239 - Preserve diagnostics across multi-case Conan consumer tests

## Symptom

A Conan `test_package` invokes one consumer executable for many independently
named cases. When one command returns non-zero, `self.run()` raises immediately,
so later cases are never attempted. The log exposes only the first failure. If
the consumer prints nothing for recognized non-zero results, even that failure
lacks an explicit case-level diagnostic.

## Root Cause

`self.run()` checks the command exit status by default and raises
`ConanException` for a non-zero result. A plain loop therefore has fail-fast
semantics even when its cases are independent and could all be executed safely.

The consumer's exit code remains the authoritative pass/fail signal, but a
silent non-zero return makes the outer exception the only diagnostic. It does
not explain which internal result the consumer produced.

## Decision And Fix

Catch only the command failure type, retain the case name and unchanged
exception text, continue through the declared cases, then fail once after the
loop:

```python
from conan.errors import ConanException

failures = []
for case in cases:
    try:
        self.run(command_for(case), env="conanrun", cwd=self.build_folder)
    except ConanException as error:
        failures.append(f"{case}: {error}")

if failures:
    details = "\n".join(f"- {failure}" for failure in failures)
    raise ConanException(
        f"{len(failures)} of {len(cases)} consumer cases failed:\n{details}"
    )
```

Do not catch `Exception`: syntax, configuration, and recipe programming errors
must retain their original traceback. The consumer should also print a stable
diagnostic for recognized failures while preserving its exit code:

```cpp
if (result != 0 && result != unknown_result) {
    std::cerr << "FAIL " << case_name << " result=" << result << '\n';
}
return result;
```

Use this pattern only when cases are independent. If one failure invalidates
shared state needed by later cases, keep fail-fast behavior or isolate each
case in a separate process or test entry.

## Verification

The iir1 1.10.0 recipe declares 46 independent consumer commands. A stubbed
Conan environment made two separated calls raise different exception strings.
The test still invoked all 46 commands, including the final case, and the final
`ConanException` contained both case names and both original messages. A
success-only run invoked the same ordered 46-case set without raising.

The production C++ source passed C++11 `-Wall -Wextra -Werror -pedantic`
syntax validation. A harness compiled the production `main()` unchanged with a
stub dispatcher and verified `PASS` with exit 0, the unknown-case diagnostic
with exit 2, and `FAIL failing-case result=7` with exit 7. The test-flow and
assertion metadata remained 46 and 91; aggregation does not create new cases.
