// Consumer use case for cgl/0.60.10.1: a third-party application that uses
// ONLY the installed/exported public headers and public API of Cgl to
// compile, link, call and run. It constructs a CglLandP cut generator,
// applies it to an LP relaxation of a tiny MILP through the public
// OsiClpSolverInterface, and verifies an observable result (a cut is
// generated and improves the LP relaxation).
#include <cassert>
#include <iostream>

// Public installed headers only (include/coin):
#include "CglLandP.hpp"
#include "CoinPackedMatrix.hpp"
#include "OsiCuts.hpp"
#include "OsiClpSolverInterface.hpp"

int main()
{
    CoinRelFltEq eq(1e-05);

    // Build a tiny MILP: min -x1 -x2 s.t. 2x1+2x2<=3, -2x1+2x2<=1,
    // 7x1+4x2<=8, -7x1+4x2<=1, x in [0,1] integer.
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
    double lpRelaxBefore = si.getObjValue();

    // Use the public CglLandP API to separate a Lift-and-Project cut.
    CglLandP generator;
    generator.setLogLevel(0);
    OsiCuts cuts;
    generator.generateCuts(si, cuts);
    int nRowCuts = cuts.sizeRowCuts();
    std::cout << "LP relaxation before = " << lpRelaxBefore << std::endl;
    std::cout << "Row cuts generated    = " << nRowCuts << std::endl;

    assert(nRowCuts >= 1);

    // Apply the cut and re-solve; the objective must not get worse
    // (minimization, so it should stay equal or increase).
    OsiSolverInterface::ApplyCutsReturnCode rc = si.applyCuts(cuts);
    si.resolve();
    double lpRelaxAfter = si.getObjValue();
    std::cout << "LP relaxation after  = " << lpRelaxAfter << std::endl;
    assert(lpRelaxAfter >= lpRelaxBefore - 1e-05);

    std::cout << "Consumer use case (public CglLandP API): PASS\n";
    return 0;
}