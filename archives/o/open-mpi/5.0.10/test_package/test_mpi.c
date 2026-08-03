#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv) {
    int rank = -1;
    int size = 0;

    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        return 1;
    }
    if (MPI_Comm_rank(MPI_COMM_WORLD, &rank) != MPI_SUCCESS ||
        MPI_Comm_size(MPI_COMM_WORLD, &size) != MPI_SUCCESS) {
        MPI_Finalize();
        return 2;
    }
    if (rank != 0 || size != 1) {
        MPI_Finalize();
        return 3;
    }
    printf("Open MPI consumer test: rank=%d size=%d\n", rank, size);
    return MPI_Finalize() == MPI_SUCCESS ? 0 : 4;
}
