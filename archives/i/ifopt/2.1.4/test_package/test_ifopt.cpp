// Consumer test for ifopt/2.1.4 (ifopt_core, solver-independent layer).
//
// Builds the textbook example problem from upstream
// ifopt_core/test/ifopt/test_vars_constr_cost.h without copying that file:
//   min_x f(x) = -(x1-2)^2
//   s.t.  x0^2 + x1 = 1,  -1 <= x0 <= 1
// Every CHECK below exercises a real packaged API; any failure exits nonzero.

#include <cmath>
#include <cstdio>

#include <ifopt/constraint_set.h>
#include <ifopt/cost_term.h>
#include <ifopt/problem.h>
#include <ifopt/variable_set.h>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool cond, const char* name, double got, double want) {
  ++g_checks;
  if (cond) {
    std::printf("PASS %s (got=%g want=%g)\n", name, got, want);
  } else {
    ++g_failures;
    std::printf("FAIL %s (got=%g want=%g)\n", name, got, want);
  }
}

void check_bool(bool cond, const char* name) {
  ++g_checks;
  if (cond) {
    std::printf("PASS %s\n", name);
  } else {
    ++g_failures;
    std::printf("FAIL %s\n", name);
  }
}

class MyVars : public ifopt::VariableSet {
 public:
  MyVars() : ifopt::VariableSet(2, "var_set1"), x0_(3.5), x1_(1.5) {}
  void SetVariables(const VectorXd& x) override {
    x0_ = x(0);
    x1_ = x(1);
  }
  VectorXd GetValues() const override {
    VectorXd v(2);
    v << x0_, x1_;
    return v;
  }
  VecBound GetBounds() const override {
    VecBound b(GetRows());
    b.at(0) = ifopt::Bounds(-1.0, 1.0);
    b.at(1) = ifopt::NoBound;
    return b;
  }

 private:
  double x0_, x1_;
};

class MyConstraint : public ifopt::ConstraintSet {
 public:
  MyConstraint() : ifopt::ConstraintSet(1, "constraint1") {}
  VectorXd GetValues() const override {
    VectorXd g(GetRows());
    Eigen::Vector2d x =
        GetVariables()->GetComponent("var_set1")->GetValues();
    g(0) = x(0) * x(0) + x(1);
    return g;
  }
  VecBound GetBounds() const override {
    VecBound b(GetRows());
    b.at(0) = ifopt::Bounds(1.0, 1.0);
    return b;
  }
  void FillJacobianBlock(std::string var_set,
                         Jacobian& jac) const override {
    if (var_set == "var_set1") {
      Eigen::Vector2d x =
          GetVariables()->GetComponent("var_set1")->GetValues();
      jac.coeffRef(0, 0) = 2.0 * x(0);
      jac.coeffRef(0, 1) = 1.0;
    }
  }
};

class MyCost : public ifopt::CostTerm {
 public:
  MyCost() : ifopt::CostTerm("cost_term1") {}
  double GetCost() const override {
    Eigen::Vector2d x =
        GetVariables()->GetComponent("var_set1")->GetValues();
    return -std::pow(x(1) - 2.0, 2.0);
  }
  void FillJacobianBlock(std::string var_set,
                         Jacobian& jac) const override {
    if (var_set == "var_set1") {
      Eigen::Vector2d x =
          GetVariables()->GetComponent("var_set1")->GetValues();
      jac.coeffRef(0, 0) = 0.0;
      jac.coeffRef(0, 1) = -2.0 * (x(1) - 2.0);
    }
  }
};

}  // namespace

int main() {
  ifopt::Problem nlp;
  nlp.AddVariableSet(std::make_shared<MyVars>());
  nlp.AddConstraintSet(std::make_shared<MyConstraint>());
  nlp.AddCostSet(std::make_shared<MyCost>());

  // 1-2: problem dimensions come from the packaged library.
  check(nlp.GetNumberOfOptimizationVariables() == 2, "num_vars",
        (double)nlp.GetNumberOfOptimizationVariables(), 2.0);
  check(nlp.GetNumberOfConstraints() == 1, "num_constraints",
        (double)nlp.GetNumberOfConstraints(), 1.0);

  // 3-6: variable bounds round-trip through the installed headers.
  auto vb = nlp.GetBoundsOnOptimizationVariables();
  check((int)vb.size() == 2, "var_bounds_size", (double)vb.size(), 2.0);
  check(vb.at(0).lower_ == -1.0 && vb.at(0).upper_ == 1.0, "var0_bounds",
        vb.at(0).upper_, 1.0);

  // 7-8: set/get variable values.
  double x0[2] = {2.0, 3.0};
  nlp.SetVariables(x0);
  Eigen::VectorXd xv = nlp.GetVariableValues();
  check(xv(0) == 2.0 && xv(1) == 3.0, "var_values", xv(0) + xv(1), 5.0);

  // 9-10: constraint evaluation: g = x0^2 + x1 = 7 at (2,3).
  Eigen::VectorXd g = nlp.EvaluateConstraints(x0);
  check(g.size() == 1, "constr_size", (double)g.size(), 1.0);
  check(std::abs(g(0) - 7.0) < 1e-12, "constr_value", g(0), 7.0);

  // 11-12: constraint Jacobian: [2*x0, 1] = [4, 1] at (2,3).
  auto jac = nlp.GetJacobianOfConstraints();
  check(jac.rows() == 1 && jac.cols() == 2, "jac_shape",
        (double)(jac.rows() + jac.cols()), 3.0);
  check(std::abs(jac.coeffRef(0, 0) - 4.0) < 1e-12 &&
            std::abs(jac.coeffRef(0, 1) - 1.0) < 1e-12,
        "jac_values", jac.coeffRef(0, 0), 4.0);

  // 13-14: cost term presence and value: -((3-2)^2) = -1 at (2,3).
  check_bool(nlp.HasCostTerms(), "has_cost");
  double c = nlp.EvaluateCostFunction(x0);
  check(std::abs(c - (-1.0)) < 1e-12, "cost_value", c, -1.0);

  // 15-16: cost gradient: [0, -2*(x1-2)] = [0, -2] at (2,3).
  Eigen::VectorXd grad = nlp.EvaluateCostFunctionGradient(x0);
  check(grad.size() == 2, "grad_size", (double)grad.size(), 2.0);
  check(std::abs(grad(0)) < 1e-12 && std::abs(grad(1) - (-2.0)) < 1e-12,
        "grad_values", grad(1), -2.0);

  std::printf("test_ifopt: %d checks, %d failures\n", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
