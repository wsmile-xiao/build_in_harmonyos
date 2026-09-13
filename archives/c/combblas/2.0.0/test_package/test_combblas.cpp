/* CombBLAS test_package consumer probe.
 * Initializes MPI and creates a CombBLAS distributed sparse matrix via the
 * public API — verifies libCombBLAS links and initializes.
 */
#include <mpi.h>
#include <CombBLAS/CombBLAS.h>
#include <iostream>

using namespace combblas;

int main(int argc, char** argv)
{
    MPI_Init(&argc, &argv);

    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    {
        /* SpParMat: distributed sparse matrix (default 1x1 process grid).
         * Scope block so it is destroyed BEFORE MPI_Finalize (its destructor
         * frees the MPI communicator — otherwise "after finalizing MPICH"). */
        SpParMat<int, int, SpDCCols<int, int>> A;
        if (rank == 0) {
            std::cout << "combblas OK" << std::endl;
        }
    }

    MPI_Finalize();
    return 0;
}
