# Ceres Solver

Ceres Solver is an open source C++ library for modeling and solving large, complicated optimization problems. It can be used to solve Non-linear Least Squares problems with bounds constraints and general unconstrained optimization problems.

## Features

- Non-linear least squares optimization
- Bundle adjustment
- General unconstrained optimization
- Automatic differentiation
- Numerical differentiation

## Dependencies

- Eigen 3.4.0 (linear algebra library)
- glog 0.7.1 (Google logging library)
- gflags 2.2.2 (command-line flags library)

## Optional Dependencies

- SuiteSparse (sparse linear algebra)
- LAPACK (linear algebra)
- CUDA (GPU acceleration)

## Version 2.2.0

Release date: October 2023

### Build Information

- Build system: CMake
- Compiler: Clang 15.0.4
- Platform: HarmonyOS (aarch64)

### Installation

```bash
# Using precompiled package
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ceres-solver 2.2.0
```

### Usage

```cpp
#include <ceres/ceres.h>

// Define cost function
struct CostFunctor {
  template <typename T>
  bool operator()(const T* const x, T* residual) const {
    residual[0] = T(10.0) - x[0];
    return true;
  }
};

// Solve optimization problem
ceres::Problem problem;
double x = 0.5;
problem.AddResidualBlock(
  new ceres::AutoDiffCostFunction<CostFunctor, 1, 1>(new CostFunctor),
  nullptr,
  &x
);

ceres::Solver::Options options;
ceres::Solver::Summary summary;
ceres::Solve(options, &problem, &summary);
```

## References

- Official website: http://ceres-solver.org/
- GitHub: https://github.com/ceres-solver/ceres-solver
- Documentation: http://ceres-solver.org/nnls_tutorial.html