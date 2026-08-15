#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    char version[MPI_MAX_LIBRARY_VERSION_STRING];
    int version_len = 0;
    int value = 0;
    int sum = 0;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Get_library_version(version, &version_len);

    value = rank + 1;
    MPI_Allreduce(&value, &sum, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);

    if (rank == 0) {
        int expected = size * (size + 1) / 2;
        if (sum != expected) {
            fprintf(stderr, "MPI_Allreduce returned %d, expected %d\n", sum, expected);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }
        if (strstr(version, "MPICH") == NULL) {
            fprintf(stderr, "MPI library version does not mention MPICH: %s\n", version);
            MPI_Abort(MPI_COMM_WORLD, 3);
        }
        printf("mpich smoke: %d ranks, %.*s\n", size, version_len, version);
    }

    MPI_Finalize();
    return 0;
}
