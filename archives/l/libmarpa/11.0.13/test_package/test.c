/* Consumer test for libmarpa/11.0.13 (R34: real API calls, real assertions).
 *
 * Builds a real BNF grammar with the public marpa.h API, runs a parse
 * through the full recognize -> bocage -> order -> tree -> value chain,
 * checks the version contract, and verifies one documented error path.
 * API usage follows the upstream tests/simple/*.c patterns.
 */
#include <stdio.h>

#include "marpa.h"

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            fprintf(stderr, "FAIL: %s\n", msg);                 \
            failures++;                                         \
        }                                                       \
    } while (0)

int main(void) {
    /* --- version contract (library vs consumer expectation) --- */
    CHECK(marpa_major_version == 11, "marpa_major_version == 11");
    CHECK(marpa_minor_version == 0, "marpa_minor_version == 0");
    CHECK(marpa_micro_version == 13, "marpa_micro_version == 13");
    CHECK(marpa_check_version(11, 0, 13) == MARPA_ERR_NONE,
          "marpa_check_version(11,0,13) == MARPA_ERR_NONE");
    CHECK(marpa_check_version(99, 0, 0) != MARPA_ERR_NONE,
          "marpa_check_version(99,0,0) is an error");

    /* marpa_version() writes major/minor/micro into an int[3] */
    int v3[3] = { 0, 0, 0 };
    CHECK(marpa_version(v3) == MARPA_ERR_NONE, "marpa_version() ok");
    CHECK(v3[0] == 11 && v3[1] == 0 && v3[2] == 13,
          "marpa_version() components 11.0.13");

    /* --- build the grammar (tests/simple/trivial.c shape) --- */
    Marpa_Config config;
    CHECK(marpa_c_init(&config) == MARPA_ERR_NONE, "marpa_c_init ok");

    Marpa_Grammar g = marpa_g_new(&config);
    CHECK(g != NULL, "marpa_g_new returned a grammar");

    CHECK(marpa_g_force_valued(g) >= 0, "marpa_g_force_valued ok");

    Marpa_Symbol_ID S_top = marpa_g_symbol_new(g);
    Marpa_Symbol_ID S_A1  = marpa_g_symbol_new(g);
    Marpa_Symbol_ID S_A2  = marpa_g_symbol_new(g);
    CHECK(S_top == 0, "first symbol id is 0");
    CHECK(S_A1 == 1 && S_A2 == 2, "sequential symbol ids");

    CHECK(marpa_g_start_symbol_set(g, S_top) >= 0, "start symbol set");
    CHECK(marpa_g_start_symbol(g) == S_top, "start symbol read back");

    /* rules: top ::= A1 A2  |  A1 A2 A2 */
    Marpa_Symbol_ID rhs[3];
    rhs[0] = S_A1; rhs[1] = S_A2;
    Marpa_Rule_ID r1 = marpa_g_rule_new(g, S_top, rhs, 2);
    rhs[2] = S_A2;
    Marpa_Rule_ID r2 = marpa_g_rule_new(g, S_top, rhs, 3);
    CHECK(r1 == 0, "first rule id is 0");
    CHECK(r2 == 1, "sequential rule ids");
    CHECK(marpa_g_rule_length(g, r1) == 2, "rule 1 length 2");
    CHECK(marpa_g_rule_length(g, r2) == 3, "rule 2 length 3");

    /* documented error path: malformed (negative) rule id */
    CHECK(marpa_g_rule_length(g, -1) == -2, "malformed rule id fails");
    CHECK(marpa_g_error(g, NULL) == MARPA_ERR_INVALID_RULE_ID,
          "error code is MARPA_ERR_INVALID_RULE_ID");
    CHECK(marpa_g_error_clear(g) >= 0, "error cleared");

    CHECK(marpa_g_precompute(g) >= 0, "marpa_g_precompute ok");
    CHECK(marpa_g_is_precomputed(g) == 1, "grammar reports precomputed");

    /* --- recognize the 2-token input "A1 A2" --- */
    Marpa_Recce r = marpa_r_new(g);
    CHECK(r != NULL, "marpa_r_new returned a recce");

    CHECK(marpa_r_start_input(r) >= 0, "marpa_r_start_input ok");
    CHECK(marpa_r_alternative(r, S_A1, 1, 1) >= 0, "alternative A1");
    CHECK(marpa_r_earleme_complete(r) >= 0, "earleme complete 1");
    CHECK(marpa_r_alternative(r, S_A2, 2, 1) >= 0, "alternative A2");
    CHECK(marpa_r_earleme_complete(r) >= 0, "earleme complete 2");
    CHECK(marpa_r_is_exhausted(r) == 0, "recce not exhausted");

    /* --- full parse chain: bocage -> order -> tree -> value --- */
    Marpa_Bocage bocage = marpa_b_new(r, -1);
    CHECK(bocage != NULL, "marpa_b_new latest earleme");

    Marpa_Order order = marpa_o_new(bocage);
    CHECK(order != NULL, "marpa_o_new ok");

    Marpa_Tree tree = marpa_t_new(order);
    CHECK(tree != NULL, "marpa_t_new ok");
    CHECK(marpa_t_next(tree) >= 0, "marpa_t_next ok");

    Marpa_Value value = marpa_v_new(tree);
    CHECK(value != NULL, "marpa_v_new ok");

    /* step through the valuation: collect tokens and rules */
    int tokens = 0, rule_steps = 0;
    Marpa_Step_Type step_type;
    while ((step_type = marpa_v_step(value)) != MARPA_STEP_INACTIVE) {
        if (step_type == MARPA_STEP_TOKEN)
            tokens++;
        else if (step_type == MARPA_STEP_RULE)
            rule_steps++;
    }
    /* input A1 A2 against top::=A1 A2: 2 token steps + 1 rule step */
    CHECK(tokens == 2, "2 token steps in valuation");
    CHECK(rule_steps == 1, "1 rule step in valuation");

    marpa_v_unref(value);
    marpa_t_unref(tree);
    marpa_o_unref(order);
    marpa_b_unref(bocage);
    marpa_r_unref(r);
    marpa_g_unref(g);

    if (failures == 0) {
        printf("libmarpa 11.0.13 consumer test: all assertions passed\n");
        return 0;
    }
    fprintf(stderr, "%d assertion(s) failed\n", failures);
    return 1;
}
