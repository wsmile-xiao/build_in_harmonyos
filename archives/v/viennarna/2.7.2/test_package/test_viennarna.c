/*
 * test_package consumer smoke test — actually calls the ViennaRNA RNAlib API.
 *
 * Folds a short GC-rich RNA sequence with the modern fold-compound API
 * (vrna_fold_compound + vrna_mfe) and checks physical invariants:
 *   - the MFE dot-bracket structure has the same length as the sequence,
 *   - it contains only valid dot-bracket characters,
 *   - the MFE free energy is negative (a real fold happened),
 *   - the structure matches the upstream reference fold for this sequence.
 *
 * The test self-reports a deterministic PASS/FAIL tally and returns a
 * nonzero exit code on any failure.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <ViennaRNA/data_structures.h>
#include <ViennaRNA/fold.h>

static int assertions = 0;
static int failures = 0;

static void check(int cond, const char *name)
{
    assertions++;
    if (cond) {
        printf("PASS: %s\n", name);
    } else {
        failures++;
        printf("FAIL: %s\n", name);
    }
}

static int valid_dotbracket(const char *s)
{
    for (; *s; ++s) {
        if (*s != '.' && *s != '(' && *s != ')' && *s != ',')
            return 0;
    }
    return 1;
}

int main(void)
{
    const char *seq      = "CGCAGGGAUACCCGCG";
    const char *expected = "(((.(((...))))))";
    size_t      n        = strlen(seq);
    char       *structure = (char *)calloc(n + 1, 1);
    vrna_fold_compound_t *vc;
    double      mfe;

    if (!structure) {
        printf("FAIL: memory allocation\n");
        return 1;
    }

    vc = vrna_fold_compound(seq, NULL, VRNA_OPTION_DEFAULT);
    check(vc != NULL, "vrna_fold_compound() returns a valid fold compound");

    if (vc) {
        mfe = (double)vrna_mfe(vc, structure);
        vrna_fold_compound_free(vc);
    } else {
        mfe = 999.0;
    }

    check(strlen(structure) == n, "MFE structure has the sequence length");
    check(valid_dotbracket(structure), "MFE structure uses valid dot-bracket characters");
    check(mfe < 0.0, "MFE free energy is negative");
    check(strcmp(structure, expected) == 0, "MFE structure matches upstream reference fold");
    printf("info: seq=%s mfe=%s (%.2f kcal/mol)\n", seq, structure, mfe);

    free(structure);

    printf("RESULT: %d/%d assertions passed\n", assertions - failures, assertions);
    return failures ? 1 : 0;
}
