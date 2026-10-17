#include <cmph.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Test cmph library: create a minimal perfect hash function and verify search results */
int main(void)
{
    const char *keys[] = {
        "alpha", "beta", "gamma", "delta", "epsilon",
        "zeta", "eta", "theta", "iota", "kappa"
    };
    unsigned int nkeys = 10;
    int found[10] = {0};
    unsigned int i;
    int ok = 1;

    /* Create key source from in-memory vector */
    cmph_io_adapter_t *source = cmph_io_vector_adapter((char **)keys, nkeys);
    if (source == NULL) {
        fprintf(stderr, "FAIL: cmph_io_vector_adapter returned NULL\n");
        return 1;
    }

    /* Configure and create minimal perfect hash function */
    cmph_config_t *config = cmph_config_new(source);
    if (config == NULL) {
        fprintf(stderr, "FAIL: cmph_config_new returned NULL\n");
        cmph_io_vector_adapter_destroy(source);
        return 1;
    }
    cmph_config_set_algo(config, CMPH_CHD);
    cmph_t *hash = cmph_new(config);
    cmph_config_destroy(config);

    if (hash == NULL) {
        fprintf(stderr, "FAIL: cmph_new returned NULL\n");
        cmph_io_vector_adapter_destroy(source);
        return 1;
    }

    /* Search for all keys and verify uniqueness */
    for (i = 0; i < nkeys; i++) {
        unsigned int id = cmph_search(hash, keys[i], (cmph_uint32)strlen(keys[i]));
        if (id >= nkeys) {
            fprintf(stderr, "FAIL: key %s mapped to out-of-range id %u\n", keys[i], id);
            ok = 0;
        } else if (found[id]) {
            fprintf(stderr, "FAIL: collision at id %u\n", id);
            ok = 0;
        } else {
            found[id] = 1;
        }
    }

    /* Verify all slots were filled */
    for (i = 0; i < nkeys; i++) {
        if (!found[i]) {
            fprintf(stderr, "FAIL: slot %u not filled\n", i);
            ok = 0;
        }
    }

    cmph_destroy(hash);
    cmph_io_vector_adapter_destroy(source);

    if (ok) {
        printf("test cmph 2.0: OK (all %u keys mapped uniquely)\n", nkeys);
        return 0;
    } else {
        printf("test cmph 2.0: FAILED\n");
        return 1;
    }
}
