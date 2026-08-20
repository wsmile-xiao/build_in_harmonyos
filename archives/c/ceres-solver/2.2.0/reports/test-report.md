# Test Report — ceres-solver 2.2.0

## Test Environment
- Platform: HarmonyOS (aarch64)
- Compiler: Clang 15.0.4
- Build System: CMake
- Date: 2026-08-06

## Build Configuration
- MINIGLOG=ON (internal glog implementation)
- GFLAGS=OFF
- BUILD_EXAMPLES=OFF
- BUILD_TESTING=OFF
- BUILD_SHARED_LIBS=OFF (static library)

## Dependencies
- eigen/3.4.0 (from Conan repository)

## Test Results

### Conan test_package (L1)
- Status: PASS
- Test binary: test_ceres_solver
- Test description: Solve simple optimization problem f(x) = 10 - x using AutoDiff
- Result: OK (solution: 10, iterations: 3)
- Solver converged to optimal solution x=10.0

### CI Quality Gates
- L0 (recipe quality): PASS
- L1 (test package): PASS
- L2 (smoke test): PASS
- L4 (security scan): PASS
- L5 (baseline): PASS

## Conclusion
All tests passed. The ceres-solver 2.2.0 library is fully functional on HarmonyOS.
