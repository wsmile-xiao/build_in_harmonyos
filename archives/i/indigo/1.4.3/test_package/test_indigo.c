#include <stdio.h>
#include <string.h>

#include "indigo.h"

static int checks_run = 0;
static int checks_passed = 0;

#define CHECK(expression, message)                                              \
    do {                                                                        \
        ++checks_run;                                                           \
        if (!(expression)) {                                                    \
            fprintf(stderr, "check %d failed: %s (last error: %s)\n",           \
                    checks_run, message, indigoGetLastError());                 \
            return 1;                                                           \
        }                                                                       \
        ++checks_passed;                                                        \
    } while (0)

int main(void)
{
    const char *version;
    int mol;
    const char *smiles;
    int reaction;
    int formula;
    const char *formula_str;

    version = indigoVersion();
    CHECK(version != 0 && version[0] != '\0', "indigoVersion must return a version string");

    mol = indigoLoadMoleculeFromString("CCO");
    CHECK(mol >= 0, "ethanol SMILES must load");
    smiles = indigoCanonicalSmiles(mol);
    CHECK(smiles != 0 && strcmp(smiles, "CCO") == 0, "ethanol canonical SMILES must round-trip");
    indigoFree(mol);

    mol = indigoLoadMoleculeFromString("c1ccccc1");
    CHECK(mol >= 0, "benzene aromatic SMILES must load");
    indigoFree(mol);

    reaction = indigoLoadReactionFromString("C.CC>>CC.C");
    CHECK(reaction >= 0, "simple reaction SMILES must load");
    formula = indigoGrossFormula(reaction);
    CHECK(formula >= 0, "gross formula handle must be valid");
    formula_str = indigoToString(formula);
    CHECK(formula_str != 0 && formula_str[0] != '\0', "gross formula string must be non-empty");
    indigoFree(formula);
    indigoFree(reaction);

    printf("Indigo consumer checks: %d/%d passed (version %s)\n",
           checks_passed, checks_run, version);
    return 0;
}
