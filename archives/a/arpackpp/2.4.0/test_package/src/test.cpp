/*
 * test_package test for arpackpp 2.4.0
 * Substantive test: solves a real symmetric eigenvalue problem
 * using ARPACK++ C++ interface to ARPACK.
 *
 * Defines a simple symmetric tridiagonal matrix functor and uses
 * ARSymStdEig to find eigenvalues.
 */
#include "arssym.h"
#include <cstdio>
#include <cstdlib>

/*
 * Simple symmetric tridiagonal matrix functor.
 * Matrix: 4 on diagonal, -1 on off-diagonals.
 * This is the 1D discrete Laplacian (size n).
 */
template <class ARFLOAT>
class SymTridiagMatrix {
private:
    int n;

public:
    SymTridiagMatrix(int dim) : n(dim) {}

    int ncols() const { return n; }

    void MultMv(ARFLOAT* v, ARFLOAT* w) {
        const ARFLOAT dd = 4.0;
        const ARFLOAT dl = -1.0;
        const ARFLOAT du = -1.0;

        if (n <= 0) return;

        // First row
        w[0] = dd * v[0] + du * v[1];
        // Middle rows
        for (int j = 1; j < n - 1; j++) {
            w[j] = dl * v[j - 1] + dd * v[j] + du * v[j + 1];
        }
        // Last row
        w[n - 1] = dl * v[n - 2] + dd * v[n - 1];
    }
};

int main() {
    // Problem dimension
    int n = 50;
    int nev = 4;  // Number of requested eigenvalues

    // Create the matrix
    SymTridiagMatrix<double> A(n);

    // Define the eigenvalue problem: find 4 eigenvalues with smallest magnitude
    ARSymStdEig<double, SymTridiagMatrix<double> >
        dprob(A.ncols(), nev, &A, &SymTridiagMatrix<double>::MultMv, "SM");

    // Find eigenvalues and eigenvectors
    dprob.FindEigenvectors();

    // Check convergence
    int nconv = dprob.ConvergedEigenvalues();

    // Print results
    printf("Dimension: %d\n", n);
    printf("Requested eigenvalues: %d\n", nev);
    printf("Converged eigenvalues: %d\n", nconv);

    // Print the eigenvalues
    for (int i = 0; i < nconv; i++) {
        printf("  Eigenvalue %d: %e\n", i + 1, dprob.Eigenvalue(i));
    }

    // Return success if all requested eigenvalues converged
    return nconv >= nev ? EXIT_SUCCESS : EXIT_FAILURE;
}
