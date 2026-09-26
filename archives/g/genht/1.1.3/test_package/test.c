/* test_package consumer test for genht 1.1.3 on HarmonyOS PC (aarch64).
 *
 * Scope
 *  1. Mirror the upstream regression scenario (src/mainsi.c + src/mainsi.ref):
 *     the same str->int operations and the same expected values are asserted
 *     through consumer-visible public headers instead of diffing stdout.
 *  2. Exercise a second type instance (htss: str->str) to prove that the
 *     macro-instantiated variants built into libgenht are usable from a
 *     downstream consumer.
 *  3. Check the bundled hash helpers and the generated version macros.
 *
 * Notes
 *  - A local CHECK() macro is used instead of <cassert>/<assert.h>: the CI
 *    profile builds Release, so -DNDEBUG would strip every assert() and the
 *    test would silently degenerate into a no-op.
 *  - Exits non-zero (therefore breaks `conan create`) on any failed check.
 */
#include <stdio.h>
#include <string.h>

#include "genht/hash.h"
#include "genht/htsi.h"
#include "genht/htss.h"
#include "genht/version.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        checks++;                                                            \
        if (!(cond)) {                                                       \
            failures++;                                                      \
            fprintf(stderr, "CHECK FAILED: %s (test.c:%d)\n", #cond,         \
                    __LINE__);                                               \
        }                                                                    \
    } while (0)


static void test_htsi(void)
{
    htsi_t *ht = htsi_alloc(strhash, strkeyeq);
    htsi_entry_t *e;
    int iterated = 0;

    CHECK(ht != NULL);
    if (ht == NULL)
        return;

    /* Same population order as upstream src/mainsi.c */
    htsi_set(ht, "a", 1);
    htsi_set(ht, "b", 2);
    htsi_set(ht, "asdf", -3);
    htsi_set(ht, "qw", 4);
    htsi_set(ht, "v", 5);
    htsi_set(ht, "df", 6);
    htsi_set(ht, "x", 7);

    CHECK(htsi_has(ht, "a") != 0);
    CHECK(htsi_has(ht, "1") == 0);

    /* insert() returns NULL for a fresh key, the existing entry otherwise */
    CHECK(htsi_insert(ht, "y", 8) == NULL);
    e = htsi_insert(ht, "x", 9);
    CHECK(e != NULL);
    CHECK(e != NULL && e->value == 7);

    /* pop() returns the old value; the entry then must be gone */
    CHECK(htsi_pop(ht, "b") == 2);
    CHECK(htsi_getentry(ht, "b") == NULL);
    CHECK(htsi_popentry(ht, "b") == NULL);
    CHECK(htsi_popentry(ht, "c") == NULL);

    CHECK(htsi_get(ht, "a") == 1);
    CHECK(htsi_get(ht, "asdf") == -3);
    CHECK(htsi_get(ht, "qw") == 4);
    CHECK(htsi_get(ht, "v") == 5);
    CHECK(htsi_get(ht, "df") == 6);
    CHECK(htsi_get(ht, "x") == 7);
    CHECK(htsi_get(ht, "y") == 8);
    CHECK(htsi_get(ht, "b") == 0);

    for (e = htsi_first(ht); e != NULL; e = htsi_next(ht, e)) {
        iterated++;
        CHECK(htsi_get(ht, e->key) == e->value);
    }
    CHECK(iterated == 7);

    /* clear() must empty the table without leaking for follow-up use */
    htsi_clear(ht);
    CHECK(htsi_first(ht) == NULL);
    htsi_free(ht);
}


static void test_htss(void)
{
    htss_t *ht = htss_alloc(strhash, strkeyeq);
    htss_entry_t *e;
    int found = 0;

    CHECK(ht != NULL);
    if (ht == NULL)
        return;

    htss_set(ht, "alpha", "one");
    htss_set(ht, "beta", "two");
    htss_set(ht, "gamma", "three");

    CHECK(htss_has(ht, "beta") != 0);
    CHECK(htss_get(ht, "delta") == NULL);
    CHECK(strcmp(htss_get(ht, "alpha"), "one") == 0);
    CHECK(strcmp(htss_get(ht, "gamma"), "three") == 0);

    /* destructive pop must return the stored pointer and remove the key */
    e = htss_popentry(ht, "beta");
    CHECK(e != NULL);
    CHECK(e != NULL && strcmp(e->value, "two") == 0);
    CHECK(htss_has(ht, "beta") == 0);

    for (e = htss_first(ht); e != NULL; e = htss_next(ht, e))
        found++;
    CHECK(found == 2);

    htss_free(ht);
}


static void test_hash_and_version(void)
{
    CHECK(strhash("genht") == strhash("genht"));
    CHECK(strhash("genht") != strhash("genhu"));
    CHECK(genht_strcasecmp("ABc", "abc") == 0);
    CHECK(GENHT_VER_MAJOR == 1);
    CHECK(GENHT_VER_MINOR == 1);
    CHECK(GENHT_VER_PATCH == 3);
    CHECK(strcmp(GENHT_VER_STR, "1.1.3") == 0);
}


int main(void)
{
    test_htsi();
    test_htss();
    test_hash_and_version();

    printf("genht test_package: %d checks, %d failures\n", checks, failures);
    if (failures > 0) {
        fprintf(stderr, "FAILED: %d/%d checks failed\n", failures, checks);
        return 1;
    }
    printf("PASS: all %d checks succeeded\n", checks);
    return 0;
}
