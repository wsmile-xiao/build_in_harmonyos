# Boost.Math long-double promotion on HarmonyOS PC

## Summary

Some Boost.Math algorithms promote internal `double` calculations to `long double`.
On HarmonyOS PC aarch64, the resulting `long double` ABI and precision behavior can
differ from the assumptions in older C++ numerical libraries. The failure may appear
as a numerical convergence error rather than a compiler or linker error.

## Error pattern

Typical symptoms include:

- `boost::math::evaluation_error` from `halley_iterate`.
- A root-finding path reporting that no root was found.
- `non_central_chi_squared` PDF or CDF evaluation reporting that its series did not converge.
- The same upstream test suite passing on a conventional Linux host but failing on HarmonyOS PC.

QuantLib 1.43 exposed this pattern in four upstream cases involving CDO and FdCev
calculations. The initial result was 1335/1339 passing tests; the failures disappeared
after the promotion policy was disabled.

## Diagnosis

1. Confirm that the failures originate in Boost.Math and mention `long double` or
   `evaluation_error`.
2. Check whether the affected code is being instantiated through a double-to-long-double
   promotion path.
3. Reproduce with the full upstream test suite. Do not rely only on a consumer smoke test.
4. Compare the result after setting `BOOST_MATH_PROMOTE_DOUBLE_POLICY=0`.

## Recommended adaptation

Set the macro in the Conan-generated CMake toolchain for the affected package:

```python
tc.preprocessor_definitions["BOOST_MATH_PROMOTE_DOUBLE_POLICY"] = "0"
```

This keeps the affected Boost.Math computations on the `double` path. It is a
package-level compatibility setting and does not modify the upstream test cases or
the shared Boost headers.

The adaptation must still run the complete upstream suite and preserve its exit code:

```bash
cmake --build .
ctest --output-on-failure
```

## QuantLib evidence

- Package: QuantLib 1.43.
- Platform: HarmonyOS PC aarch64.
- Initial result: 1335/1339 upstream tests passed.
- Final result: 1339/1339 upstream tests passed.
- Conan result: `EXIT=0`.
- Consumer result: `quantlib curve test passed: 0.951229`.
- Related issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2280

## Scope and limits

This entry applies to Boost.Math numerical paths whose behavior is affected by the
target platform's `long double` representation. It does not prove that every numerical
failure on HarmonyOS has the same cause. A package must first reproduce the error
signature and then verify the workaround with its complete upstream test suite.

Do not mark the suite successful by ignoring a non-zero exit code, skipping the affected
tests, or weakening assertions. If the macro does not resolve a failure, retain the
failure evidence and diagnose the specific numerical path.

## Reuse candidates

The pattern is relevant to C++ financial, statistics, scientific-computing, and
probability libraries that consume Boost.Math distribution or root-finding algorithms,
including packages with QuantLib-like numerical workloads.
