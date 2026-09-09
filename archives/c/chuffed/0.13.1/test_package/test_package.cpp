// test_package for chuffed 0.13.1 — exercises the public C++ API of the
// solver library (engine, modelling, branching) the same way the upstream
// examples do (e.g. chuffed/examples/queens.cpp, chuffed/examples/steel_mill.cpp).
//
// The chuffed engine is a global singleton (`engine`) and one process solves
// exactly one problem (upstream fzn-chuffed/main() calls engine.solve() once),
// so each scenario runs in its own binary.
//
// test_package (this binary):
//   6-Queens all-solutions search — must find exactly the 4 known solutions.
// test_optimize:
//   maximise x subject to x+y<=10, x-y=2, x,y in 1..9 — optimum is x=6.

#include <chuffed/branching/branching.h>
#include <chuffed/core/engine.h>
#include <chuffed/core/options.h>
#include <chuffed/core/propagator.h>
#include <chuffed/vars/modelling.h>

#include <cstdio>

namespace {

class QueensProblem : public Problem {
public:
    int const n;
    vec<IntVar*> x;  // placement of queens, one IntVar per row

    explicit QueensProblem(int _n) : n(_n) {
        createVars(x, n, 1, n);

        vec<int> a;
        vec<int> b;
        for (int i = 0; i < n; i++) {
            a.push(i);
            b.push(-i);
        }

        all_different(x);            // different columns
        all_different_offset(a, x);  // different "/" diagonals
        all_different_offset(b, x);  // different "\" diagonals

        branch(x, VAR_INORDER, VAL_MIN);
        output_vars(x);
    }

    void print(std::ostream& os) override {
        for (int i = 0; i < n; i++) {
            os << x[i]->getVal() << " ";
        }
        os << "\n";
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
    // All-solutions search on 6-Queens: exactly 4 solutions are known.
    so.nof_solutions = 0;  // 0 = enumerate all solutions
    so.verbosity = 0;
    engine.solve(new QueensProblem(6));
    check(engine.solutions == 4, "6-Queens all-solutions search finds exactly 4 solutions");
    check(engine.nodes > 0, "engine explored a non-empty search tree");

    if (failures == 0) {
        std::printf("All chuffed satisfiability tests passed!\n");
        return 0;
    }
    return 1;
}
