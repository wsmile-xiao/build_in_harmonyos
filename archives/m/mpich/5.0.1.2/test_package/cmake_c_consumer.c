#include <mpi.h>

#include <stdio.h>

int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    int value = 0;
    int total = 0;

    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        return 101;
    }
    if (MPI_Comm_rank(MPI_COMM_WORLD, &rank) != MPI_SUCCESS ||
        MPI_Comm_size(MPI_COMM_WORLD, &size) != MPI_SUCCESS) {
        MPI_Abort(MPI_COMM_WORLD, 102);
    }
    if (size != 2) {
        MPI_Abort(MPI_COMM_WORLD, 103);
    }
    value = rank + 1;
    if (MPI_Allreduce(&value, &total, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD) !=
        MPI_SUCCESS) {
        MPI_Abort(MPI_COMM_WORLD, 104);
    }
    if (total != 3) {
        MPI_Abort(MPI_COMM_WORLD, 105);
    }
    if (MPI_Finalize() != MPI_SUCCESS) {
        return 106;
    }
    if (rank == 0) {
        puts("CMake MPI::MPI_C consumer: PASS");
    }
    return 0;
}
