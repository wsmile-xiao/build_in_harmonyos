/*
 * test.cpp — CoinMP consumer test for OpenHarmony aarch64.
 *
 * Loads the same LP instance as the upstream unitTest "CoinTest"
 * (8 columns, 5 rows, 14 non-zeros, optimal objective 1428729.28571),
 * solves it through the CoinMP C-API and asserts:
 *   1. CoinInitSolver succeeds
 *   2. the problem checks out (SOLV_CALL_SUCCESS)
 *   3. the solver returns an Optimal solution
 *   4. the reported objective matches the known optimal value
 * This exercises the actual CoinMP API surface (create/load/optimize/
 * query/unload) instead of printing a placeholder string.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "CoinMP.h"

#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (!(cond)) {                                                  \
            fprintf(stderr, "FAIL: %s\n", msg);                         \
            return 1;                                                   \
        }                                                               \
    } while (0)

int main(void)
{
    HPROB hProb;
    int result, status;
    double objValue, optimalValue = 1428729.28571;
    int colCount = 8, rowCount = 5, nonZeroCount = 14;

    /* Same instance data as upstream unitTest.cpp "CoinTest". */
    int objectSense = SOLV_OBJSENS_MAX;
    double objectConst = 0.0;
    double objectCoeffs[8]  = { 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0 };
    double lowerBounds[8]   = { 0., 0., 0., 0., 0., 0., 0., 0. };
    double upperBounds[8]   = { 1000000., 1000000., 1000000., 1000000.,
                                1000000., 1000000., 1000000., 1000000. };
    char rowType[5]         = { 'L', 'L', 'L', 'L', 'L' };
    double rhsValues[5]     = { 14., 80., 50., 50., 50. };
    int matrixBegin[9]      = { 0, 2, 4, 6, 8, 10, 11, 12, 14 };
    int matrixCount[8]      = { 2, 2, 2, 2, 2, 1, 1, 2 };
    int matrixIndex[14]     = { 0, 4, 0, 1, 1, 2, 0, 3, 0, 4, 2, 3, 0, 4 };
    double matrixValues[14] = { 3., 5.6, 1., 2., 1.1, 1., -2., 2.8,
                                -1., 1., 1., -1.2, -1., 1.9 };

    printf("CoinMP consumer test: version %g\n", CoinGetVersion());

    result = CoinInitSolver("");
    CHECK(result == SOLV_CALL_SUCCESS, "CoinInitSolver failed");

    hProb = CoinCreateProblem("CoinTestConsumer");
    CHECK(hProb != NULL, "CoinCreateProblem failed");

    result = CoinLoadMatrix(hProb, colCount, rowCount, nonZeroCount, 0,
                            objectSense, objectConst, objectCoeffs,
                            lowerBounds, upperBounds, rowType, rhsValues,
                            NULL, matrixBegin, matrixCount, matrixIndex,
                            matrixValues);
    CHECK(result == SOLV_CALL_SUCCESS, "CoinLoadMatrix failed");

    result = CoinCheckProblem(hProb);
    CHECK(result == SOLV_CALL_SUCCESS, "CoinCheckProblem failed");

    result = CoinOptimizeProblem(hProb, 0);
    CHECK(result == SOLV_CALL_SUCCESS, "CoinOptimizeProblem failed");

    status = CoinGetSolutionStatus(hProb);
    /* Upstream unitTest asserts solutionStatus == 0 for "Optimal
       solution found" (see CoinMP/test/unitTest.cpp). */
    CHECK(status == SOLV_CALL_SUCCESS, "expected optimal solution status");

    objValue = CoinGetObjectValue(hProb);
    printf("optimal value = %.8g (expected %.8g)\n", objValue, optimalValue);
    CHECK(fabs(objValue - optimalValue) < 1.0e-3,
          "objective value does not match upstream reference");

    CoinUnloadProblem(hProb);
    CoinFreeSolver();

    printf("PASS: CoinMP consumer test\n");
    return 0;
}
