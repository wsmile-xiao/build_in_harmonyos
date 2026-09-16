#include <stdio.h>
#include <stdlib.h>
#include "qdpll.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond, msg) \
    do { \
        checks++; \
        if (!(cond)) { \
            fprintf(stderr, "FAIL [%d]: %s\n", checks, msg); \
            failures++; \
        } else { \
            printf("PASS [%d]: %s\n", checks, msg); \
        } \
    } while (0)

int main(void)
{
    /* --- Case 1: propositional SAT via API: exists x1, clause (x1) --- */
    QDPLL *s1 = qdpll_create();
    CHECK(s1 != NULL, "qdpll_create returns non-NULL (SAT case)");
    CHECK(qdpll_configure(s1, "--dep-man=simple") == NULL,
          "qdpll_configure --dep-man=simple succeeds");
    qdpll_new_scope_at_nesting(s1, QDPLL_QTYPE_EXISTS, 1);
    qdpll_add(s1, 1);
    qdpll_add(s1, 0);
    CHECK(qdpll_is_var_declared(s1, 1), "x1 declared after scope setup");
    CHECK(!qdpll_is_var_declared(s1, 99), "x99 not declared");
    CHECK(qdpll_get_scope_type(s1, 1) == QDPLL_QTYPE_EXISTS,
          "scope 1 is existential");
    CHECK(qdpll_get_max_declared_var_id(s1) == 1, "max declared var id is 1");
    qdpll_add(s1, 1);
    qdpll_add(s1, 0);
    QDPLLResult r1 = qdpll_sat(s1);
    CHECK(r1 == QDPLL_RESULT_SAT, "single-clause formula is SAT (10)");
    CHECK(qdpll_get_value(s1, 1) == QDPLL_ASSIGNMENT_TRUE,
          "model assigns x1 true");
    qdpll_delete(s1);

    /* --- Case 2: propositional UNSAT: exists x1, clauses (x1), (-x1) --- */
    QDPLL *s2 = qdpll_create();
    CHECK(s2 != NULL, "qdpll_create returns non-NULL (UNSAT case)");
    qdpll_new_scope_at_nesting(s2, QDPLL_QTYPE_EXISTS, 1);
    qdpll_add(s2, 1);
    qdpll_add(s2, 0);
    qdpll_add(s2, 1);
    qdpll_add(s2, 0);
    qdpll_add(s2, -1);
    qdpll_add(s2, 0);
    QDPLLResult r2 = qdpll_sat(s2);
    CHECK(r2 == QDPLL_RESULT_UNSAT, "contradictory formula is UNSAT (20)");
    qdpll_delete(s2);

    /* --- Case 3: quantified prefix inspection + UNSAT QBF ---
       exists x1 forall x2 exists x3, clauses: (x3), (-x1 -x2), (x1 x2).
       Universal reduction removes x2, remaining core is UNSAT. */
    QDPLL *s3 = qdpll_create();
    CHECK(s3 != NULL, "qdpll_create returns non-NULL (QBF case)");
    CHECK(qdpll_configure(s3, "--dep-man=simple") == NULL,
          "qdpll_configure --dep-man=simple succeeds (QBF case)");
    CHECK(qdpll_configure(s3, "--incremental-use") == NULL,
          "qdpll_configure --incremental-use succeeds");
    qdpll_new_scope_at_nesting(s3, QDPLL_QTYPE_EXISTS, 1);
    qdpll_add(s3, 1);
    qdpll_add(s3, 0);
    qdpll_new_scope_at_nesting(s3, QDPLL_QTYPE_FORALL, 2);
    qdpll_add(s3, 2);
    qdpll_add(s3, 0);
    qdpll_new_scope_at_nesting(s3, QDPLL_QTYPE_EXISTS, 3);
    qdpll_add(s3, 3);
    qdpll_add(s3, 0);
    CHECK(qdpll_get_max_scope_nesting(s3) == 3, "three scopes created");
    CHECK(qdpll_get_nesting_of_var(s3, 1) == 1, "x1 at nesting 1");
    CHECK(qdpll_get_nesting_of_var(s3, 2) == 2, "x2 at nesting 2");
    CHECK(qdpll_get_nesting_of_var(s3, 3) == 3, "x3 at nesting 3");
    CHECK(qdpll_get_scope_type(s3, 2) == QDPLL_QTYPE_FORALL,
          "scope 2 is universal");
    qdpll_add(s3, 3);
    qdpll_add(s3, 0);
    qdpll_push(s3);
    qdpll_add(s3, -1);
    qdpll_add(s3, -2);
    qdpll_add(s3, 0);
    qdpll_add(s3, 1);
    qdpll_add(s3, 2);
    qdpll_add(s3, 0);
    QDPLLResult r3 = qdpll_sat(s3);
    CHECK(r3 == QDPLL_RESULT_UNSAT, "QBF case is UNSAT (20)");
    qdpll_delete(s3);

    printf("test_qdpll: %d checks, %d failures\n", checks, failures);
    if (failures != 0) {
        fprintf(stderr, "test_qdpll FAILED\n");
        return 1;
    }
    printf("All libqdpll consumer tests passed.\n");
    return 0;
}
