/* ScaLAPACK two-rank BLACS and LP64 distribution probe. */

#include <stdio.h>

extern void Cblacs_pinfo(int *rank, int *size);
extern void Cblacs_get(int context, int request, int *value);
extern void Cblacs_gridinit(int *context, char *order, int rows, int columns);
extern void Cblacs_gridinfo(
    int context, int *rows, int *columns, int *row, int *column);
extern void Cblacs_gridexit(int context);
extern void Cblacs_exit(int continue_mpi);
extern int numroc_(
    int *n, int *block_size, int *process, int *source, int *process_count);

int main(void) {
    int rank = -1;
    int size = 0;
    int context = -1;
    int rows = 0;
    int columns = 0;
    int row = -1;
    int column = -1;
    int failures = 0;
    char order[] = "R";

    Cblacs_pinfo(&rank, &size);
    if (size != 2) {
        fprintf(stderr, "rank %d: expected 2 processes, got %d\n", rank, size);
        failures++;
    }

    Cblacs_get(-1, 0, &context);
    Cblacs_gridinit(&context, order, 1, 2);
    Cblacs_gridinfo(context, &rows, &columns, &row, &column);

    if (rows != 1 || columns != 2) {
        fprintf(
            stderr,
            "rank %d: unexpected grid shape %dx%d\n",
            rank,
            rows,
            columns);
        failures++;
    }
    if (row != 0 || column != rank) {
        fprintf(
            stderr,
            "rank %d: unexpected grid coordinate (%d,%d)\n",
            rank,
            row,
            column);
        failures++;
    }

    {
        int n = 8;
        int block_size = 2;
        int source = 0;
        int local = numroc_(&n, &block_size, &column, &source, &columns);
        if (local != 4) {
            fprintf(stderr, "rank %d: numroc returned %d, expected 4\n", rank, local);
            failures++;
        }
    }

    printf(
        "rank %d/%d grid=(%d,%d) failures=%d\n",
        rank,
        size,
        row,
        column,
        failures);
    Cblacs_gridexit(context);
    Cblacs_exit(0);
    return failures == 0 ? 0 : 1;
}
