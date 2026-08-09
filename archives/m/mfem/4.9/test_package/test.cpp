#include <iostream>

#include "mfem.hpp"

int main() {
    // 1. Create a simple 2D mesh: 2x2 quadrilateral elements on [0,1]^2
    mfem::Mesh mesh(2, 2, mfem::Element::QUADRILATERAL, 1, 1.0, 1.0);

    // 2. Define a finite element space on the mesh (H1, order 1)
    mfem::H1_FECollection fec(1, mesh.Dimension());
    mfem::FiniteElementSpace fespace(&mesh, &fec);

    // 3. Verify we have degrees of freedom
    int ndof = fespace.GetTrueVSize();
    std::cout << "MFEM 4.9 test: OK (ndof = " << ndof << ")" << std::endl;

    if (ndof <= 0) {
        return 1;
    }

    return 0;
}
