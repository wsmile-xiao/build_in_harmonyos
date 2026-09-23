// test_optimize for chuffed 0.13.1 — optimisation scenario in a separate
// process (the chuffed engine singleton solves one problem per process).
//
// Maximise x subject to: x + y <= 10, x - y = 2, x,y in 1..9.
// Feasible x values are 3..6, so the optimum is x = 6 (y = 4).

#include <chuffed/branching/branching.h>
#include <chuffed/core/engine.h>
#include <chuffed/core/options.h>
#include <chuffed/core/propagator.h>
#include <chuffed/vars/modelling.h>

#include <cstdio>

namespace {

class OptProblem : public Problem {
public:
    vec<IntVar*> v;

    OptProblem() {
        createVars(v, 2, 1, 9);

        vec<int> coefs1;
        coefs1.push(1);
        coefs1.push(1);
        int_linear(coefs1, v, IRT_LE, 10);

        vec<int> coefs2;
        coefs2.push(1);
        coefs2.push(-1);
        int_linear(coefs2, v, IRT_EQ, 2);

        branch(v, VAR_INORDER, VAL_MIN);
        output_vars(v);
        optimize(v[0], OPT_MAX);
    }

    void print(std::ostream& os) override {
        os << "x=" << v[0]->getVal() << " y=" << v[1]->getVal() << "\n";
    }
};

int failures = 0;

void check(bool ok, const char* what) {
    if (ok) {
        std::printf("PASS %s\n", what);
    } else {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
}

}  // namespace

int main() {
    so.nof_solutions = 1;
    so.verbosity = 0;
    engine.solve(new OptProblem());
    check(engine.solutions >= 1, "optimisation search produced at least one solution");
    check(engine.best_sol == 6, "maximise x reaches the known optimum 6 (engine.best_sol)");

    if (failures == 0) {
        std::printf("All chuffed optimisation tests passed!\n");
        return 0;
    }
    return 1;
}
