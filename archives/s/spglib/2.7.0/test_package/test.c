#include <stdio.h>
#include <string.h>

#include "spglib.h"

/* Consumer test: single-atom simple-cubic cell must resolve to
 * space group Pm-3m (No. 221). Each passing assertion prints one
 * CHECK-OK: line; the conanfile counts them for the
 * HMBS_TEST_PACKAGE_RESULT marker (7 lines required).
 */
int main(void) {
    double lattice[3][3] = {{1.0, 0.0, 0.0}, {0.0, 1.0, 0.0}, {0.0, 0.0, 1.0}};
    double position[1][3] = {{0.0, 0.0, 0.0}};
    int types[1] = {1};
    int num_atom = 1;
    double symprec = 1e-5;
    int checked = 0;

    const char *version = spg_get_version();
    if (version == NULL || version[0] == '\0') {
        fprintf(stderr, "spg_get_version returned empty\n");
        return 1;
    }
    printf("CHECK-OK: version=%s\n", version);
    checked++;

    const char *version_full = spg_get_version_full();
    if (version_full == NULL || version_full[0] == '\0') {
        fprintf(stderr, "spg_get_version_full returned empty\n");
        return 1;
    }
    printf("CHECK-OK: version_full=%s\n", version_full);
    checked++;

    SpglibDataset *dataset =
        spg_get_dataset(lattice, position, types, num_atom, symprec);
    if (dataset == NULL) {
        fprintf(stderr, "spg_get_dataset returned NULL\n");
        return 1;
    }
    printf("CHECK-OK: dataset non-null\n");
    checked++;

    if (dataset->spacegroup_number != 221) {
        fprintf(stderr, "unexpected spacegroup_number=%d (want 221)\n",
                dataset->spacegroup_number);
        spg_free_dataset(dataset);
        return 1;
    }
    printf("CHECK-OK: spacegroup_number=221\n");
    checked++;

    if (dataset->n_operations <= 0) {
        fprintf(stderr, "n_operations=%d (want >0)\n", dataset->n_operations);
        spg_free_dataset(dataset);
        return 1;
    }
    printf("CHECK-OK: n_operations=%d\n", dataset->n_operations);
    checked++;

    if (dataset->international_symbol[0] == '\0') {
        fprintf(stderr, "international_symbol is empty\n");
        spg_free_dataset(dataset);
        return 1;
    }
    printf("CHECK-OK: international_symbol=%s\n", dataset->international_symbol);
    checked++;

    if (strstr(dataset->international_symbol, "Pm-3m") == NULL &&
        strstr(dataset->international_symbol, "Pm3m") == NULL &&
        strstr(dataset->international_symbol, "Pm") == NULL) {
        fprintf(stderr, "unexpected international_symbol=%s\n",
                dataset->international_symbol);
        spg_free_dataset(dataset);
        return 1;
    }
    printf("CHECK-OK: symbol sanity ok\n");
    checked++;

    spg_free_dataset(dataset);

    if (checked != 7) {
        fprintf(stderr, "checked=%d (want 7)\n", checked);
        return 1;
    }
    printf("spglib consumer test: OK (%d checks)\n", checked);
    return 0;
}
