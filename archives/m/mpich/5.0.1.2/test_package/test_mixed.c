#include <mpi.h>

_Static_assert(sizeof(int) == 4, "C int must be four bytes");
_Static_assert(sizeof(MPI_Fint) == 4, "MPI_Fint must be four bytes");

int c_mpi_probe(int comm_f, int fortran_rank, int fortran_size)
{
    MPI_Comm comm = MPI_Comm_f2c((MPI_Fint) comm_f);
    int rank = -1;
    int size = 0;
    int value = 0;
    int total = 0;

    if (MPI_Comm_rank(comm, &rank) != MPI_SUCCESS ||
        MPI_Comm_size(comm, &size) != MPI_SUCCESS) {
        return 1;
    }
    if (rank != fortran_rank || size != fortran_size) {
        return 2;
    }
    value = rank + 1;
    if (MPI_Allreduce(&value, &total, 1, MPI_INT, MPI_SUM, comm) != MPI_SUCCESS) {
        return 3;
    }
    return total == size * (size + 1) / 2 ? 0 : 4;
}
