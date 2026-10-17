/*
 * Consumer test for the packaged polylib library.
 *
 * Builds the unit square 0 <= x,y <= 1 from its constraint matrix, converts
 * it to the dual (vertex/ray) representation, checks the expected polyhedral
 * invariants and converts it back to constraints.
 *
 * Constraint rows are [flag, constant, coefficients...] where flag 1 marks an
 * inequality (0 marks an equality).
 */
#include <stdio.h>
#include <polylib/polylibgmp.h>

#define MAX_RAYS 200

static int failures = 0;

static void check(int condition, const char *what) {
  if (condition) {
    printf("PASS: %s\n", what);
  } else {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main(void) {
  const int square[4][4] = {
      {1, 0, 1, 0},   /* 0 <= x          */
      {1, -1, 1, 0},  /* x <= 1          */
      {1, 0, 0, 1},   /* 0 <= y          */
      {1, -1, 0, 1},  /* y <= 1          */
  };
  Matrix *C = Matrix_Alloc(4, 4);
  int i, j;

  for (i = 0; i < 4; i++)
    for (j = 0; j < 4; j++)
      value_set_si(C->p[i][j], square[i][j]);

  Polyhedron *P = Constraints2Polyhedron(C, MAX_RAYS);
  Matrix_Free(C);
  if (!P) {
    printf("FAIL: Constraints2Polyhedron returned NULL\n");
    return 1;
  }

  printf("square: dimension=%d constraints=%d rays=%d equations=%d\n",
         (int)P->Dimension, (int)P->NbConstraints, (int)P->NbRays,
         (int)P->NbEq);
  check(P->Dimension == 2, "square has dimension 2");
  check(P->NbConstraints == 4, "square has 4 facets");
  check(P->NbEq == 0, "square is full dimensional (no implicit equalities)");
  check(P->NbRays == 4, "square has the 4 expected vertices/rays");

  Matrix *C2 = Polyhedron2Constraints(P);
  if (!C2) {
    printf("FAIL: Polyhedron2Constraints returned NULL\n");
    Domain_Free(P);
    return 1;
  }
  printf("round trip: %d constraints, %d columns\n", (int)C2->NbRows,
         (int)C2->NbColumns);
  check(C2->NbRows == 4, "constraint round trip keeps the 4 facets");
  check(C2->NbColumns == P->Dimension + 2,
        "constraint round trip keeps the homogeneous width");

  Matrix_Free(C2);
  Domain_Free(P);

  if (failures) {
    printf("FAILED: %d polylib consumer assertion(s)\n", failures);
    return 1;
  }
  printf("OK: polylib consumer API test passed\n");
  return 0;
}
