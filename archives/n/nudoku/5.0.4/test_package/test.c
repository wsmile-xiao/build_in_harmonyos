/* test_package/test.c — exercises the nudoku solver API (libnudoku.a).
 *
 * Calls is_valid_puzzle()/solve() on a fully-solved valid grid (which needs no
 * backtracking, so solve() returns exactly 1) and on an invalid grid. Exits 0
 * only if all assertions hold.
 */
#include "sudoku.h"
#include <stdio.h>
#include <string.h>

int main(void)
{
    /* A fully-solved, valid sudoku (classic shift-by-3 pattern), 81 chars + NUL.
     * Using a solved grid avoids the recursive backtracker, so solve() returns
     * exactly 1 (the traversal reaches the end without backtracking). */
    char solved[STREAM_LENGTH] =
        "123456789456789123789123456234567891567891234891234567345678912678912345912345678";

    /* 1) a solved, well-formed grid is reported valid */
    if (!is_valid_puzzle(solved)) {
        printf("FAIL: solved grid rejected as invalid\n");
        return 1;
    }

    /* 2) solve() confirms at least one solution */
    int solutions = solve(solved);
    if (solutions < 1) {
        printf("FAIL: solved grid returned %d solutions\n", solutions);
        return 2;
    }

    /* 3) an invalid grid (two '1's in the first row) is rejected */
    char bad[STREAM_LENGTH];
    memset(bad, '.', STREAM_LENGTH - 1);
    bad[0] = '1';
    bad[1] = '1';
    bad[STREAM_LENGTH - 1] = '\0';
    if (is_valid_puzzle(bad)) {
        printf("FAIL: invalid grid accepted\n");
        return 3;
    }

    /* 4) solve() of an invalid grid returns 0 */
    if (solve(bad) != 0) {
        printf("FAIL: solve(invalid) != 0\n");
        return 4;
    }

    printf("PASS: nudoku solver test (solved grid: %d solution(s))\n",
           solutions);
    return 0;
}
