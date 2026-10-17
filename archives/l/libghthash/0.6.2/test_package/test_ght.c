#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <ght_hash_table.h>

int main(int argc, char *argv[])
{
    ght_hash_table_t *p_table;
    int *p_data;
    int *p_he;
    int rc;
    int failures = 0;

    /* 1. Create a hash table with 128 buckets */
    p_table = ght_create(128);
    if (!p_table) {
        fprintf(stderr, "FAIL: ght_create returned NULL\n");
        return 1;
    }

    /* 2. Insert a key-value pair (key includes NUL terminator) */
    p_data = (int *)malloc(sizeof(int));
    if (!p_data) {
        fprintf(stderr, "FAIL: malloc failed\n");
        ght_finalize(p_table);
        return 1;
    }
    *p_data = 15;

    rc = ght_insert(p_table, p_data,
                    sizeof(char) * (strlen("blabla") + 1), "blabla");
    if (rc != 0) {
        fprintf(stderr, "FAIL: ght_insert returned %d (expected 0)\n", rc);
        failures++;
    }

    /* 3. Query the key and verify the returned value */
    p_he = (int *)ght_get(p_table,
                          sizeof(char) * (strlen("blabla") + 1), "blabla");
    if (!p_he) {
        fprintf(stderr, "FAIL: ght_get returned NULL for existing key\n");
        failures++;
    } else if (*p_he != 15) {
        fprintf(stderr, "FAIL: ght_get returned %d (expected 15)\n", *p_he);
        failures++;
    } else {
        printf("OK: inserted and retrieved value %d\n", *p_he);
    }

    /* 4. Query a non-existent key — must return NULL */
    p_he = (int *)ght_get(p_table,
                          sizeof(char) * (strlen("missing") + 1), "missing");
    if (p_he != NULL) {
        fprintf(stderr, "FAIL: ght_get returned non-NULL for missing key\n");
        failures++;
    }

    /* 4b. Insert multiple elements and verify size + retrieval */
    {
        static const char *keys[] = {"alpha", "beta", "gamma", "delta"};
        int vals[] = {100, 200, 300, 400};
        size_t nkeys = sizeof(keys) / sizeof(keys[0]);
        size_t k;
        for (k = 0; k < nkeys; k++) {
            int *pv = (int *)malloc(sizeof(int));
            if (!pv) {
                fprintf(stderr, "FAIL: malloc failed in multi-insert\n");
                failures++;
                continue;
            }
            *pv = vals[k];
            rc = ght_insert(p_table, pv,
                            sizeof(char) * (strlen(keys[k]) + 1), keys[k]);
            if (rc != 0) {
                fprintf(stderr,
                        "FAIL: ght_insert(%s) returned %d (expected 0)\n",
                        keys[k], rc);
                failures++;
            }
        }
        /* 1 (blabla) + nkeys = 5 entries now */
        if (ght_size(p_table) != (unsigned int)(1 + nkeys)) {
            fprintf(stderr,
                    "FAIL: ght_size returned %u (expected %u) after "
                    "multi-insert\n",
                    ght_size(p_table), (unsigned int)(1 + nkeys));
            failures++;
        }
        /* Verify each multi-inserted value is retrievable */
        for (k = 0; k < nkeys; k++) {
            p_he = (int *)ght_get(p_table,
                                  sizeof(char) * (strlen(keys[k]) + 1),
                                  keys[k]);
            if (!p_he) {
                fprintf(stderr,
                        "FAIL: ght_get returned NULL for key %s\n", keys[k]);
                failures++;
            } else if (*p_he != vals[k]) {
                fprintf(stderr,
                        "FAIL: ght_get(%s) returned %d (expected %d)\n",
                        keys[k], *p_he, vals[k]);
                failures++;
            }
        }
        if (failures == 0)
            printf("OK: multi-insert of %zu elements verified\n", nkeys);
    }

    /* 5. Remove the original key and verify the removed data is returned */
    p_he = (int *)ght_remove(p_table,
                             sizeof(char) * (strlen("blabla") + 1), "blabla");
    if (!p_he) {
        fprintf(stderr, "FAIL: ght_remove returned NULL for existing key\n");
        failures++;
    } else {
        free(p_he);
        printf("OK: removed key blabla\n");
    }

    /* 6. Query again — must now return NULL */
    p_he = (int *)ght_get(p_table,
                          sizeof(char) * (strlen("blabla") + 1), "blabla");
    if (p_he != NULL) {
        fprintf(stderr, "FAIL: ght_get returned non-NULL after remove\n");
        failures++;
    }

    /* 7. After removing blabla, 4 multi-inserted keys remain → size must be 4 */
    if (ght_size(p_table) != 4) {
        fprintf(stderr, "FAIL: ght_size returned %u (expected 4) after one "
                        "removal\n", ght_size(p_table));
        failures++;
    }

    /* 8. Remove every remaining key, verify each removal, then confirm empty */
    {
        static const char *remain[] = {"alpha", "beta", "gamma", "delta"};
        size_t nrem = sizeof(remain) / sizeof(remain[0]);
        size_t r;
        for (r = 0; r < nrem; r++) {
            p_he = (int *)ght_remove(p_table,
                                     sizeof(char) * (strlen(remain[r]) + 1),
                                     remain[r]);
            if (!p_he) {
                fprintf(stderr,
                        "FAIL: ght_remove returned NULL for key %s\n",
                        remain[r]);
                failures++;
            } else {
                free(p_he);
            }
        }
        if (ght_size(p_table) != 0) {
            fprintf(stderr,
                    "FAIL: ght_size returned %u (expected 0) after clearing "
                    "all keys\n", ght_size(p_table));
            failures++;
        } else if (failures == 0) {
            printf("OK: table empty after removing all keys\n");
        }
    }

    ght_finalize(p_table);

    if (failures == 0) {
        printf("All tests passed\n");
        return 0;
    }
    fprintf(stderr, "%d test(s) failed\n", failures);
    return 1;
}
