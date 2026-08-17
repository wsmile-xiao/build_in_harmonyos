#include <mpi.h>

#include <iostream>

static int fail_mpi(int rc, const char *call, int code)
{
    if (rc == MPI_SUCCESS) {
        return 0;
    }
    std::cerr << call << " failed with MPI error code " << rc << '\n';
    MPI_Abort(MPI_COMM_WORLD, code);
    return code;
}

int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    int value = 0;
    int sum = 0;

    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        std::cerr << "MPI_Init failed\n";
        return 31;
    }
    if (fail_mpi(MPI_Comm_rank(MPI_COMM_WORLD, &rank), "MPI_Comm_rank", 32)) {
        return 32;
    }
    if (fail_mpi(MPI_Comm_size(MPI_COMM_WORLD, &size), "MPI_Comm_size", 33)) {
        return 33;
    }
    if (size != 2) {
        std::cerr << "C++ consumer expected 2 ranks, got " << size << '\n';
        MPI_Abort(MPI_COMM_WORLD, 34);
    }

    value = rank + 1;
    if (fail_mpi(
            MPI_Allreduce(&value, &sum, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD),
            "MPI_Allreduce",
            35)) {
        return 35;
    }
    if (sum != 3) {
        std::cerr << "C++ consumer allreduce returned " << sum << '\n';
        MPI_Abort(MPI_COMM_WORLD, 36);
    }
    if (MPI_Finalize() != MPI_SUCCESS) {
        std::cerr << "MPI_Finalize failed\n";
        return 37;
    }
    if (rank == 0) {
        std::cout << "MPICH C++ wrapper consumer: PASS\n";
    }
    return 0;
}
