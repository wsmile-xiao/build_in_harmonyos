#include <petscksp.h>

int main(int argc, char **argv) {
    Vec x;
    PetscScalar value = 2.0;
    PetscReal norm = 0.0;

    PetscCall(PetscInitialize(&argc, &argv, NULL, NULL));
    PetscCall(VecCreateSeq(PETSC_COMM_SELF, 3, &x));
    PetscCall(VecSet(x, value));
    PetscCall(VecNorm(x, NORM_2, &norm));
    PetscCheck(norm > 3.46 && norm < 3.47, PETSC_COMM_SELF, PETSC_ERR_PLIB, "unexpected vector norm");
    PetscCall(VecDestroy(&x));
    PetscCall(PetscFinalize());
    return 0;
}
