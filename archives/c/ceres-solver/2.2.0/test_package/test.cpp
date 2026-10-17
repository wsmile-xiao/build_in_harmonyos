#include <ceres/ceres.h>
#include <iostream>
#include <cmath>

// Simple cost function: f(x) = 10 - x
struct CostFunctor {
    template <typename T>
    bool operator()(const T* const x, T* residual) const {
        residual[0] = T(10.0) - x[0];
        return true;
    }
};

int main() {
    double x = 0.5;

    ceres::Problem problem;
    ceres::CostFunction* cost_function =
        new ceres::AutoDiffCostFunction<CostFunctor, 1, 1>(new CostFunctor);
    problem.AddResidualBlock(cost_function, nullptr, &x);

    ceres::Solver::Options options;
    options.minimizer_progress_to_stdout = false;
    options.max_num_iterations = 100;
    ceres::Solver::Summary summary;
    ceres::Solve(options, &problem, &summary);

    // The optimal solution is x = 10.0
    if (std::abs(x - 10.0) < 1e-3) {
        std::cout << "test ceres-solver 2.2.0: OK (solution: " << x
                  << ", iterations: " << summary.iterations.size() << ")" << std::endl;
        return 0;
    } else {
        std::cout << "test ceres-solver 2.2.0: FAIL (solution: " << x << ")" << std::endl;
        return 1;
    }
}
