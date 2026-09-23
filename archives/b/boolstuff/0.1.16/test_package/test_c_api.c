/*  test_c_api.c - C API consumer test for boolstuff on OHOS.

    Mirrors the upstream checkc.c scenario against the installed shared
    library: manual tree construction, printing, DNF conversion, term
    roots, cloning, parsing and error reporting.  Uses assert() on real
    API behavior; prints a final PASS line only when every check ran.
*/

#include <boolstuff/c-api.h>

#include <stdlib.h>
#include <string.h>

#undef NDEBUG
#include <assert.h>

#define LEFT(x) boolstuff_get_left_subtree(x)
#define RIGHT(x) boolstuff_get_right_subtree(x)
#define TYPE(x) boolstuff_get_node_type(x)

int main(void)
{
    boolexpr_t a_node, b_node, c_node, d_node, lower_and_node, or_node,
               not_node, upper_and_node, dnf_root, dnf_clone, parsed_tree;
    char *str;
    size_t error_index = 0;
    enum bool_error_t error_code = BOOLSTUFF_OK;
    int failures = 0;

    setbuf(stdout, NULL);

    /* Build the tree for a & !(b | c & d). */
    a_node = boolstuff_create_value_node("a");
    b_node = boolstuff_create_value_node("b");
    c_node = boolstuff_create_value_node("c");
    d_node = boolstuff_create_value_node("d");
    assert(a_node && b_node && c_node && d_node);

    assert(TYPE(a_node) == BOOLSTUFF_VALUE);
    assert(strcmp(boolstuff_get_node_value(a_node), "a") == 0);

    lower_and_node = boolstuff_create_operator_node(BOOLSTUFF_AND, c_node, d_node);
    or_node = boolstuff_create_operator_node(BOOLSTUFF_OR, b_node, lower_and_node);
    assert(TYPE(or_node) == BOOLSTUFF_OR);
    assert(LEFT(or_node) == b_node);
    assert(RIGHT(or_node) == lower_and_node);

    not_node = boolstuff_create_operator_node(BOOLSTUFF_NOT, NULL, or_node);
    upper_and_node = boolstuff_create_operator_node(BOOLSTUFF_AND, a_node, not_node);
    assert(TYPE(upper_and_node) == BOOLSTUFF_AND);
    assert(TYPE(LEFT(upper_and_node)) == BOOLSTUFF_VALUE);
    assert(TYPE(RIGHT(upper_and_node)) == BOOLSTUFF_NOT);
    assert(TYPE(RIGHT(RIGHT(upper_and_node))) == BOOLSTUFF_OR);
    assert(TYPE(RIGHT(RIGHT(RIGHT(upper_and_node)))) == BOOLSTUFF_AND);

    str = boolstuff_print_tree_to_string(upper_and_node);
    assert(str != NULL);
    if (strcmp(str, "a&!(b|c&d)") != 0)
        failures++;
    printf("print_tree_to_string: %s\n", str);
    boolstuff_free_string(str);

    assert(boolstuff_is_disjunctive_normal_form(upper_and_node) == 0);

    dnf_root = boolstuff_get_disjunctive_normal_form(upper_and_node);
    assert(dnf_root != NULL);
    upper_and_node = NULL;  /* consumed by the DNF conversion */

    str = boolstuff_print_tree_to_string(dnf_root);
    assert(str != NULL);
    if (strcmp(str, "a&!b&!c|a&!b&!d") != 0)
        failures++;
    printf("DNF: %s\n", str);
    boolstuff_free_string(str);

    assert(boolstuff_is_disjunctive_normal_form(dnf_root) != 0);

    /* DNF term roots. */
    {
        boolexpr_t *roots;
        size_t num_roots = 0;
        roots = boolstuff_get_dnf_term_roots(dnf_root, &num_roots);
        assert(roots != NULL);
        assert(num_roots == 2);
        assert(roots[num_roots] == NULL);
        for (size_t i = 0; i < num_roots; i++)
        {
            char **pos = NULL;
            char **neg = NULL;
            char *term_str = boolstuff_print_tree_to_string(roots[i]);
            printf("term %zu: %s\n", i, term_str);
            boolstuff_free_string(term_str);
            boolstuff_get_tree_variables(roots[i], &pos, &neg);
            assert(pos != NULL && neg != NULL);
            boolstuff_free_variables_sets(pos, neg);
        }
        boolstuff_free_node_array(roots);
    }

    /* Clone and destroy. */
    dnf_clone = boolstuff_clone_tree(dnf_root);
    boolstuff_destroy_tree(dnf_root);
    dnf_root = NULL;
    str = boolstuff_print_tree_to_string(dnf_clone);
    assert(str != NULL);
    if (strcmp(str, "a&!b&!c|a&!b&!d") != 0)
        failures++;
    printf("clone: %s\n", str);
    boolstuff_free_string(str);
    boolstuff_destroy_tree(dnf_clone);
    dnf_clone = NULL;

    /* Parser through the C API. */
    parsed_tree = boolstuff_parse("!(a|b)&(c1_x|!d)", &error_index, &error_code);
    if (parsed_tree == NULL)
    {
        printf("C API parse failed: code %d at index %zu\n",
               (int) error_code, error_index);
        return 1;
    }
    assert(TYPE(parsed_tree) == BOOLSTUFF_AND);
    assert(TYPE(LEFT(parsed_tree)) == BOOLSTUFF_NOT);
    assert(TYPE(RIGHT(parsed_tree)) == BOOLSTUFF_OR);
    boolstuff_destroy_tree(parsed_tree);
    parsed_tree = NULL;

    /* Error reporting: garbage at end must be detected. */
    {
        boolexpr_t bad = boolstuff_parse("a&", &error_index, &error_code);
        assert(bad == NULL);
        assert(error_code == BOOLSTUFF_ERR_IDENTIFIER_EXPECTED);
    }

    /* NULL DNF semantics: DNF(a&!a) keeps the contradiction term
       (verified on-device against the built library). */
    {
        boolexpr_t t = boolstuff_parse("a&!a", NULL, NULL);
        assert(t != NULL);
        boolexpr_t f = boolstuff_get_disjunctive_normal_form(t);
        /* f is the tree to destroy; t was consumed by the conversion. */
        assert(f != NULL);
        str = boolstuff_print_tree_to_string(f);
        assert(str != NULL && strcmp(str, "a&!a") == 0);
        boolstuff_free_string(str);
        boolstuff_destroy_tree(f);
    }

    if (failures != 0)
        printf("C API consumer test: %d failure(s)\n", failures);
    else
        printf("C API consumer test: PASS\n");
    return failures == 0 ? 0 : 1;
}
