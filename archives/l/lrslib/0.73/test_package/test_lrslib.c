/* test_package consumer: drive the installed lrslib C API through its
 * public headers and verify an exact, hand-checkable invariant.
 *
 * A d-dimensional hypercube has exactly 2^d vertices; lrslib must
 * enumerate them from the H-representation built below. */
#include <stdio.h>
#include <string.h>

#include <lrslib/lrsdriver.h>
#include <lrslib/lrslib.h>

#define MAXCOL 32

static long failures = 0;
static long checks = 0;

static void check(long cond, const char *what)
{
    checks++;
    if (cond)
        printf("[ok]   %s\n", what);
    else
    {
        printf("[FAIL] %s\n", what);
        failures++;
    }
}

/* H-representation of the unit hypercube of dimension (Q->n - 1):
 * 0 <= x_j <= 1 written as 2*(n-1) inequalities. */
static void makecube(lrs_dic *P, lrs_dat *Q)
{
    long num[MAXCOL], den[MAXCOL];
    long row, j;
    long m = Q->m, n = Q->n;

    for (row = 1; row <= m; row++)
    {
        for (j = 0; j < n; j++)
        {
            num[j] = 0;
            den[j] = 1;
        }
        if (row < n)
        {
            num[0] = 1;
            num[row] = -1;
        }
        else
        {
            num[0] = 0;
            num[row + 1 - n] = 1;
        }
        lrs_set_row(P, Q, row, num, den, GE);
    }
}

int main(void)
{
    long dim, expected, got, col;
    lrs_dic *P;
    lrs_dat *Q;
    lrs_mp_vector output;
    lrs_mp_matrix Lin;

    if (!lrs_init("\n*test_lrslib:"))
    {
        printf("[FAIL] lrs_init\n");
        return 1;
    }

    for (dim = 2; dim <= 4; dim++)
    {
        Q = lrs_alloc_dat("LRS globals");
        if (Q == NULL)
        {
            printf("[FAIL] lrs_alloc_dat\n");
            return 1;
        }
        Q->n = dim + 1;       /* columns = dimension + 1 */
        Q->m = 2 * dim;       /* rows = 2 * dimension   */

        output = lrs_alloc_mp_vector(Q->n);
        P = lrs_alloc_dic(Q);
        if (P == NULL || output == NULL)
        {
            printf("[FAIL] lrs_alloc_dic\n");
            return 1;
        }

        makecube(P, Q);

        if (!lrs_getfirstbasis(&P, Q, &Lin, FALSE))
        {
            printf("[FAIL] lrs_getfirstbasis (dim=%ld)\n", dim);
            return 1;
        }

        got = 0;
        do
        {
            for (col = 0; col <= P->d; col++)
                if (lrs_getsolution(P, Q, output, col))
                    got++;
        } while (lrs_getnextbasis(&P, Q, FALSE));

        /* every reported solution of a full-dimensional cube is a vertex */
        expected = 1L << dim;
        {
            char what[128];
            snprintf(what, sizeof(what),
                     "hypercube dim=%ld enumerates %ld vertices (lrslib reported %ld)",
                     dim, expected, got);
            check(got == expected, what);
        }

        lrs_clear_mp_vector(output, Q->n);
        lrs_free_dic(P, Q);
        lrs_free_dat(Q);
    }

    lrs_close("test_lrslib:");
    printf("[summary] %ld/%ld assertions passed\n", checks - failures, checks);
    return failures == 0 ? 0 : 1;
}
