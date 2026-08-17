#include <mpi.h>

#include <stdint.h>
#include <stdio.h>

extern void cmake_fortran_probe(int32_t comm, int32_t *status);

int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    int32_t status = -1;

    _Static_assert(sizeof(MPI_Fint) == sizeof(int32_t),
                   "MPI_Fint must be four bytes");
    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        return 111;
    }
    if (MPI_Comm_rank(MPI_COMM_WORLD, &rank) != MPI_SUCCESS ||
        MPI_Comm_size(MPI_COMM_WORLD, &size) != MPI_SUCCESS) {
        MPI_Abort(MPI_COMM_WORLD, 112);
    }
    if (size != 2) {
        MPI_Abort(MPI_COMM_WORLD, 113);
    }
    cmake_fortran_probe((int32_t)MPI_Comm_c2f(MPI_COMM_WORLD), &status);
    if (status != 0) {
        MPI_Abort(MPI_COMM_WORLD, 114);
    }
    if (MPI_Finalize() != MPI_SUCCESS) {
        return 115;
    }
    if (rank == 0) {
        puts("CMake MPI::MPI_Fortran consumer: PASS");
    }
    return 0;
}
