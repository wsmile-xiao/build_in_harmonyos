/*
 * Consumer test for libpll 0.3.2 (Phylogenetic Likelihood Library).
 *
 * Exercises the public Newick API from pll.h as a library user:
 *   - pll_utree_parse_newick_string(): parse an unrooted Newick string
 *   - pll_utree_check_integrity(): structural integrity of the parsed tree
 *   - pll_utree_destroy(): release the tree
 *
 * Verifiable behavior asserted below:
 *   1. parsing "((A:0.1,B:0.2):0.3,(C:0.4,D:0.5):0.6);" must yield a tree
 *      with exactly 4 tips, 2 inner nodes and 5 edges;
 *   2. the structural integrity check must pass;
 *   3. the tip labels must be exactly A, B, C, D;
 *   4. a malformed Newick string must be rejected (NULL + error message).
 */
#include <stdio.h>
#include <string.h>
#include <libpll/pll.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

int main(void)
{
    /* libpll parses UNROOTED trees: the basal node must be a trifurcation */
    const char *newick = "(A:0.1,B:0.2,(C:0.3,D:0.4):0.5);";
    const char *labels[4] = { "A", "B", "C", "D" };

    pll_utree_t *tree = pll_utree_parse_newick_string(newick);
    if (!tree) {
        fprintf(stderr, "FAIL: parse_newick_string returned NULL (err: %s)\n",
                pll_errmsg);
        return 1;
    }

    check(tree->tip_count == 4, "tip_count == 4");
    check(tree->inner_count == 2, "inner_count == 2");
    check(tree->edge_count == 5, "edge_count == 5");
    check(pll_utree_check_integrity(tree) == 1, "tree integrity check");

    int matched = 0;
    for (unsigned int i = 0; i < tree->tip_count; ++i) {
        const char *lab = tree->nodes[i]->label;
        for (int j = 0; j < 4; ++j) {
            if (lab && strcmp(lab, labels[j]) == 0) {
                matched++;
                break;
            }
        }
    }
    check(matched == 4, "tip labels are exactly A, B, C, D");

    pll_utree_destroy(tree, NULL);

    /* malformed input must be rejected */
    pll_utree_t *bad = pll_utree_parse_newick_string("((A:0.1,B:0.2;");
    check(bad == NULL, "malformed Newick string rejected");
    check(pll_errmsg[0] != '\0', "error message set for malformed input");

    if (failures == 0) {
        printf("test_libpll: all assertions passed\n");
        return 0;
    }
    fprintf(stderr, "test_libpll: %d assertion(s) failed\n", failures);
    return 1;
}
