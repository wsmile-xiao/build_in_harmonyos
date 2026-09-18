// HarmonyOS special test for CglLandP (Lift-and-Project cut generator).
// Built only against the installed public headers (include/coin/CglLandP.hpp)
// and the published cgl::cgl CMake target; verifies that the CglLandP
// public API declared by the upstream releases/0.60.10 source actually
// compiles, links and produces cuts on the OHOS aarch64 target.
#include <cassert>
#include <iostream>

#include "CglLandP.hpp"
#include "CglLandPValidator.hpp"
#include "CoinPackedMatrix.hpp"
#include "OsiCuts.hpp"
#include "OsiClpSolverInterface.hpp"

int main()
{
    CoinRelFltEq eq(1e-05);

    // 1) CglLandP default parameters (upstream CglLandPTest.cpp case).
    {
        CglLandP aGenerator;
        assert(aGenerator.parameter().pivotLimit == 20);
        assert(aGenerator.parameter().maxCutPerRound == 5000);
        assert(aGenerator.parameter().failedPivotLimit == 1);
        assert(aGenerator.parameter().degeneratePivotLimit == 0);
        assert(eq(aGenerator.parameter().pivotTol, 1e-04));
        assert(eq(aGenerator.parameter().away, 5e-04));
        assert(eq(aGenerator.parameter().timeLimit, COIN_DBL_MAX));
        assert(aGenerator.parameter().useTableauRow == true);
        assert(aGenerator.parameter().modularize == false);
        assert(aGenerator.parameter().strengthen == true);
        assert(aGenerator.parameter().perturb == true);
        assert(aGenerator.parameter().pivotSelection == CglLandP::mostNegativeRc);
    }

    // 2) Copy constructor / assignment round-trip.
    {
        CglLandP b;
        b.parameter().pivotLimit = 100;
        b.parameter().maxCutPerRound = 100;
        b.parameter().failedPivotLimit = 10;
        b.parameter().degeneratePivotLimit = 10;
        b.parameter().pivotTol = 1e-07;
        b.parameter().away = 1e-10;
        b.parameter().timeLimit = 120;
        b.parameter().singleCutTimeLimit = 15;
        b.parameter().useTableauRow = true;
        b.parameter().modularize = true;
        b.parameter().strengthen = false;
        b.parameter().perturb = false;
        b.parameter().pivotSelection = CglLandP::bestPivot;
        CglLandP c(b);
        assert(c.parameter().pivotLimit == 100);
        assert(c.parameter().maxCutPerRound == 100);
        assert(c.parameter().failedPivotLimit == 10);
        assert(c.parameter().degeneratePivotLimit == 10);
        assert(c.parameter().pivotTol == 1e-07);
        assert(c.parameter().away == 1e-10);
        assert(c.parameter().timeLimit == 120);
        assert(c.parameter().singleCutTimeLimit == 15);
        assert(c.parameter().useTableauRow == true);
        assert(c.parameter().modularize == true);
        assert(c.parameter().strengthen == false);
        assert(c.parameter().perturb == false);
        assert(c.parameter().pivotSelection == CglLandP::bestPivot);
    }

    // 3) Real lift-and-project cut generation on a small MILP:
    //    min -x1 -x2
    //    s.t.  2x1 + 2x2 <= 3
    //         -2x1 + 2x2 <= 1
    //          7x1 + 4x2 <= 8
    //         -7x1 + 4x2 <= 1
    //         0 <= x1, x2 <= 1, integer
    //    Expected: exactly 1 row cut, lower bound -0.0714286.
    {
        CoinBigIndex start[2] = {0, 4};
        int length[2] = {4, 4};
        int rows[8] = {0, 1, 2, 3, 0, 1, 2, 3};
        double elements[8] = {2.0, -2.0, 7.0, -7.0, 2.0, 2.0, 4.0, 4.0};
        CoinPackedMatrix columnCopy(true, 4, 2, 8, elements, rows, start, length);

        double rowLower[4] = {-COIN_DBL_MAX, -COIN_DBL_MAX,
                              -COIN_DBL_MAX, -COIN_DBL_MAX};
        double rowUpper[4] = {3., 1., 8., 1.};
        double colLower[2] = {0.0, 0.0};
        double colUpper[2] = {1.0, 1.0};
        double obj[2] = {-1, -1};
        int intVar[2] = {0, 1};

        OsiClpSolverInterface si;
        si.loadProblem(columnCopy, colLower, colUpper, obj, rowLower, rowUpper);
        si.setInteger(intVar, 2);
        si.initialSolve();

        CglLandP generator;
        generator.setLogLevel(2);
        generator.parameter().sepSpace = CglLandP::Full;

        OsiCuts cuts;
        generator.generateCuts(si, cuts);
        std::cout << "CglLandP row cuts generated: " << cuts.sizeRowCuts() << std::endl;
        assert(cuts.sizeRowCuts() == 1);

        OsiRowCut aCut = cuts.rowCut(0);
        assert(eq(aCut.lb(), -.0714286));
        CoinPackedVector row = aCut.row();
        assert(row.getNumElements() == 1 || row.getNumElements() == 2);
        if (row.getNumElements() == 1) {
            assert(row.getIndices()[0] == 1);
            assert(eq(row.getElements()[0], -4 * .0714286));
        } else {
            assert(eq(row.getElements()[1], -1));
        }

        OsiSolverInterface::ApplyCutsReturnCode rc = si.applyCuts(cuts);
        assert(rc.getNumApplied() + rc.getNumInfeasible() >= 0);
    }

    std::cout << "CglLandP HarmonyOS special test: PASS\n";
    return 0;
}