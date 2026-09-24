/*
 * HarmonyOS (aarch64-ohos) consumer test for petsc-complex/3.25.4.
 *
 * The point of this package is the *complex scalar variant*, so every
 * assertion below is an observable behaviour that a real-scalar PETSc could
 * not produce:
 *   - the headers expose PETSC_USE_COMPLEX and a 2x-wide PetscScalar,
 *   - |z| and the vector dot product really use the imaginary part,
 *   - a KSP solve carries a non-zero imaginary part through to the solution.
 * The file would not even preprocess against a real PETSc build, because
 * PETSC_USE_COMPLEX is checked at compile time.
 *
 * TAP-ish output: one "ok N" / "not ok N" line per assertion, then a summary
 * line that CI greps for.
 */
#include <math.h>
#include <stdio.h>

#include <petscksp.h>

#ifndef PETSC_USE_COMPLEX
#error "petsc-complex must be built with --with-scalar-type=complex"
#endif
#ifndef PETSC_USE_REAL_DOUBLE
#error "petsc-complex must be built with --with-precision=double"
#endif

static int checks = 0;
static int failures = 0;

#define CHECK(cond, what)                                          \
  do {                                                             \
    checks++;                                                      \
    if (cond) {                                                    \
      printf("ok %d - %s\n", checks, (what));                      \
    } else {                                                       \
      failures++;                                                  \
      printf("not ok %d - %s\n", checks, (what));                  \
    }                                                              \
  } while (0)

int main(int argc, char **argv) {
  PetscErrorCode ierr;
  Vec x, y, xtrue, b, sol;
  Mat A;
  KSP ksp;
  PetscScalar z, s0;
  PetscReal nrm, err;
  PetscInt r0 = 0, c1 = 1, i0 = 0;

  PetscCall(PetscInitialize(&argc, &argv, NULL, NULL));

  /* ---- 1. package identity: this really is the complex variant -------- */
  CHECK(sizeof(PetscScalar) == 2 * sizeof(PetscReal),
        "sizeof(PetscScalar) == 2 * sizeof(PetscReal)");
  CHECK(sizeof(PetscReal) == sizeof(double),
        "PetscReal is double precision");
  CHECK(PETSC_VERSION_MAJOR == 3 && PETSC_VERSION_MINOR == 25 &&
            PETSC_VERSION_SUBMINOR == 4,
        "headers report PETSc 3.25.4");

  /* ---- 2. scalar level: both components survive ----------------------- */
  z = PetscCMPLX(2.5, -1.25);
  CHECK(PetscRealPart(z) == 2.5 && PetscImaginaryPart(z) == -1.25,
        "PetscCMPLX / PetscRealPart / PetscImaginaryPart round-trip");
  CHECK(fabs(PetscAbsScalar(PetscCMPLX(3.0, 4.0)) - 5.0) < 1e-12,
        "PetscAbsScalar(3+4i) == 5 (magnitude uses the imaginary part)");

  /* ---- 3. vector level: complex arithmetic ---------------------------- */
  PetscCall(VecCreateSeq(PETSC_COMM_SELF, 3, &x));
  PetscCall(VecSet(x, PetscCMPLX(2.0, 1.0)));
  PetscCall(VecNorm(x, NORM_2, &nrm));
  CHECK(fabs(nrm - sqrt(15.0)) < 1e-12,
        "VecNorm of (2+1i)*[1,1,1] is sqrt(15), not 2*sqrt(3)");
  CHECK(PetscIsNormalReal(nrm), "the vector norm is a finite normal number");

  PetscCall(VecDuplicate(x, &y));
  PetscCall(VecSet(y, PetscCMPLX(0.0, 1.0)));
  PetscCall(VecPointwiseMult(y, y, x)); /* y = i * x */

  { /* VecDot(x, i*x) has magnitude |x|^2 = 15 and a purely imaginary value */
    PetscScalar dot = 0.0;
    PetscReal mag;
    PetscCall(VecDot(x, y, &dot));
    mag = PetscSqrtReal(PetscRealPart(dot) * PetscRealPart(dot) +
                        PetscImaginaryPart(dot) * PetscImaginaryPart(dot));
    CHECK(fabs(mag - 15.0) < 1e-12,
          "|VecDot(x, i*x)| == |x|^2 == 15");
    CHECK(fabs(PetscImaginaryPart(dot)) > 1e-12,
          "VecDot(x, i*x) is genuinely complex (non-zero imaginary part)");
  }

  /* ---- 4. matrix level: complex entries round-trip -------------------- */
  PetscCall(MatCreateSeqAIJ(PETSC_COMM_SELF, 2, 2, 2, NULL, &A));
  PetscCall(MatSetValue(A, 0, 0, PetscCMPLX(1.0, 1.0), INSERT_VALUES));
  PetscCall(MatSetValue(A, 0, 1, PetscCMPLX(1.0, -1.0), INSERT_VALUES));
  PetscCall(MatSetValue(A, 1, 0, PetscCMPLX(2.0, 0.0), INSERT_VALUES));
  PetscCall(MatSetValue(A, 1, 1, PetscCMPLX(3.0, 1.0), INSERT_VALUES));
  PetscCall(MatAssemblyBegin(A, MAT_FINAL_ASSEMBLY));
  PetscCall(MatAssemblyEnd(A, MAT_FINAL_ASSEMBLY));

  { /* MatSetValue/MatGetValue really store both components */
    PetscScalar a01 = 0.0;
    PetscCall(MatGetValue(A, r0, c1, &a01));
    CHECK(PetscRealPart(a01) == 1.0 && PetscImaginaryPart(a01) == -1.0,
          "MatGetValue returns the complex entry 1 - 1i");
  }

  /* ---- 5. end-to-end: complex Krylov solve ---------------------------- */
  PetscCall(VecCreateSeq(PETSC_COMM_SELF, 2, &xtrue));
  PetscCall(VecSetValue(xtrue, 0, PetscCMPLX(1.0, 1.0), INSERT_VALUES));
  PetscCall(VecSetValue(xtrue, 1, PetscCMPLX(-1.0, 2.0), INSERT_VALUES));
  PetscCall(VecAssemblyBegin(xtrue));
  PetscCall(VecAssemblyEnd(xtrue));

  PetscCall(VecDuplicate(xtrue, &b));
  PetscCall(MatMult(A, xtrue, b)); /* b is computed, not hand-written */

  PetscCall(VecDuplicate(xtrue, &sol));
  PetscCall(KSPCreate(PETSC_COMM_SELF, &ksp));
  PetscCall(KSPSetOperators(ksp, A, A));
  PetscCall(KSPSetType(ksp, KSPGMRES));
  PetscCall(KSPSetTolerances(ksp, 1e-14, PETSC_DEFAULT, PETSC_DEFAULT, 4));
  PetscCall(KSPSetFromOptions(ksp));
  PetscCall(KSPSolve(ksp, b, sol));

  PetscCall(VecGetValues(sol, 1, &i0, &s0));
  CHECK(fabs(PetscRealPart(s0) - 1.0) < 1e-10 &&
            fabs(PetscImaginaryPart(s0) - 1.0) < 1e-10,
        "KSP solution[0] == 1 + 1i (imaginary part survives the solve)");

  PetscCall(VecAXPY(sol, -1.0, xtrue)); /* sol <- sol - x_true */
  PetscCall(VecNorm(sol, NORM_2, &err));
  CHECK(err < 1e-10, "||KSP solution - x_true||_2 < 1e-10");

  PetscCall(KSPDestroy(&ksp));
  PetscCall(MatDestroy(&A));
  PetscCall(VecDestroy(&x));
  PetscCall(VecDestroy(&y));
  PetscCall(VecDestroy(&xtrue));
  PetscCall(VecDestroy(&b));
  PetscCall(VecDestroy(&sol));

  ierr = PetscFinalize();
  if (ierr) return (int)ierr;

  printf("assertions: %d, failures: %d\n", checks, failures);
  return failures ? 1 : 0;
}
