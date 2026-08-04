#include <mpi.h>
#include <stdio.h>
#include <string.h>

static void check_mpi(int rc, const char *call, int abort_code)
{
    if (rc != MPI_SUCCESS) {
        fprintf(stderr, "%s failed with MPI error code %d\n", call, rc);
        MPI_Abort(MPI_COMM_WORLD, abort_code);
    }
}

int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    char version[MPI_MAX_LIBRARY_VERSION_STRING] = {0};
    int version_len = 0;
    int value = 0;
    int sum = 0;
    int rc = MPI_SUCCESS;

    rc = MPI_Init(&argc, &argv);
    if (rc != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Init failed with MPI error code %d\n", rc);
        return 1;
    }

    check_mpi(MPI_Comm_rank(MPI_COMM_WORLD, &rank), "MPI_Comm_rank", 2);
    check_mpi(MPI_Comm_size(MPI_COMM_WORLD, &size), "MPI_Comm_size", 3);
    check_mpi(MPI_Get_library_version(version, &version_len), "MPI_Get_library_version", 4);

    value = rank + 1;
    check_mpi(MPI_Allreduce(&value, &sum, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD), "MPI_Allreduce", 5);

    if (rank == 0) {
        int expected = size * (size + 1) / 2;
        if (sum != expected) {
            fprintf(stderr, "MPI_Allreduce returned %d, expected %d\n", sum, expected);
            MPI_Abort(MPI_COMM_WORLD, 6);
        }
        if (strstr(version, "MPICH") == NULL) {
            fprintf(stderr, "MPI library version does not mention MPICH: %s\n", version);
            MPI_Abort(MPI_COMM_WORLD, 7);
        }
        printf("mpich smoke: %d ranks, %.*s\n", size, version_len, version);
    }

    rc = MPI_Finalize();
    if (rc != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Finalize failed with MPI error code %d\n", rc);
        return 8;
    }
    return 0;
}
