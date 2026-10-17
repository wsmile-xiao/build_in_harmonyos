# ifopt

An Eigen-based, light-weight C++ interface to nonlinear programming solvers (Ipopt, Snopt).

This directory tracks the HarmonyOS PC adaptation of `ifopt`
(upstream: https://github.com/ethz-adrl/ifopt). Version 2.1.4 adapts the
solver-independent `ifopt_core` layer (problem formulation on top of Eigen3);
the optional Ipopt/Snopt solver backends stay disabled via the official
`BUILD_IPOPT`/`BUILD_SNOPT` options.

## Dependencies

- `eigen/3.4.1` (Conan, transitive headers)
- `gtest/1.17.0.1` (`test_requires` only, for the upstream test suite; in-repo recipe, avoids conancenter cmake `KeyError: 'OHOS'`)
