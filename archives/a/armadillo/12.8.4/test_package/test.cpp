#include <armadillo>
#include <iostream>
#include <cassert>

int main() {
    // Print version
    std::cout << "Armadillo version: " << arma::arma_version::as_string() << std::endl;

    // Matrix creation
    arma::mat A = arma::randu(3, 3);
    arma::mat B = arma::randu(3, 3);

    // Matrix addition
    arma::mat C = A + B;
    assert(C.n_rows == 3 && C.n_cols == 3);

    // Matrix multiplication
    arma::mat D = A * B;
    assert(D.n_rows == 3 && D.n_cols == 3);

    // Transpose
    arma::mat At = A.t();
    assert(At.n_rows == 3 && At.n_cols == 3);

    // Element access
    double val = A(0, 0);
    (void)val;

    // Special matrices
    arma::mat Z = arma::zeros(3, 3);
    arma::mat O = arma::ones(3, 3);
    arma::mat I = arma::eye(3, 3);
    assert(Z(0, 0) == 0.0);
    assert(O(0, 0) == 1.0);
    assert(I(0, 0) == 1.0 && I(0, 1) == 0.0);

    // Vector operations
    arma::vec v = arma::ones(5);
    double s = arma::sum(v);
    assert(s == 5.0);

    // Matrix accumulation
    double acc = arma::accu(O);
    assert(acc == 9.0);

    // Norm
    double n = arma::norm(v);
    assert(n > 0.0);

    // Min/max
    arma::vec w = arma::linspace(1, 5, 5);
    assert(arma::min(w) == 1.0);
    assert(arma::max(w) == 5.0);

    // Dot product
    double dp = arma::dot(v, w);
    assert(dp == 15.0);

    // ---- LAPACK-dependent tests (require OpenBLAS) ----

    // Solve linear system Ax=b
    arma::mat A5 = arma::randu(5, 5);
    arma::vec b5 = arma::randu(5);
    arma::vec x = arma::solve(A5, b5);
    assert(x.n_elem == 5);

    // Matrix inverse
    arma::mat Ai = arma::inv(A5);
    assert(Ai.n_rows == 5 && Ai.n_cols == 5);

    // SVD (Singular Value Decomposition)
    arma::mat U;
    arma::vec sv;
    arma::mat V;
    arma::svd(U, sv, V, A5);
    assert(sv.n_elem == 5);

    // Eigenvalue decomposition (symmetric)
    arma::mat S = A5 + A5.t();  // make symmetric
    arma::vec eigvals = arma::eig_sym(S);
    assert(eigvals.n_elem == 5);

    std::cout << "All tests passed (including LAPACK-dependent: solve, inv, svd, eig_sym)!" << std::endl;
    return 0;
}
