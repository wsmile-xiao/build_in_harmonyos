#include <slepceps.h>

int main(int argc, char **argv) {
    Mat matrix;
    EPS solver;
    PetscInt converged = 0;
    PetscScalar eigenvalue = 0.0;
    PetscReal error = 0.0;

    PetscCall(SlepcInitialize(&argc, &argv, NULL, NULL));
    PetscCall(MatCreateSeqAIJ(PETSC_COMM_SELF, 2, 2, 1, NULL, &matrix));
    PetscCall(MatSetValue(matrix, 0, 0, 2.0, INSERT_VALUES));
    PetscCall(MatSetValue(matrix, 1, 1, 3.0, INSERT_VALUES));
    PetscCall(MatAssemblyBegin(matrix, MAT_FINAL_ASSEMBLY));
    PetscCall(MatAssemblyEnd(matrix, MAT_FINAL_ASSEMBLY));

    PetscCall(EPSCreate(PETSC_COMM_SELF, &solver));
    PetscCall(EPSSetOperators(solver, matrix, NULL));
    PetscCall(EPSSetProblemType(solver, EPS_HEP));
    PetscCall(EPSSetDimensions(solver, 1, PETSC_DETERMINE, PETSC_DETERMINE));
    PetscCall(EPSSolve(solver));
    PetscCall(EPSGetConverged(solver, &converged));
    PetscCheck(converged >= 1, PETSC_COMM_SELF, PETSC_ERR_PLIB, "no eigenpair converged");
    PetscCall(EPSGetEigenpair(solver, 0, &eigenvalue, NULL, NULL, NULL));
    PetscCall(EPSComputeError(solver, 0, EPS_ERROR_RELATIVE, &error));
    PetscCheck(PetscRealPart(eigenvalue) > 2.99 && PetscRealPart(eigenvalue) < 3.01,
               PETSC_COMM_SELF, PETSC_ERR_PLIB, "unexpected dominant eigenvalue");
    PetscCheck(error < 1.0e-10, PETSC_COMM_SELF, PETSC_ERR_PLIB, "eigenpair error is too large");

    PetscCall(EPSDestroy(&solver));
    PetscCall(MatDestroy(&matrix));
    PetscCall(SlepcFinalize());
    return 0;
}
