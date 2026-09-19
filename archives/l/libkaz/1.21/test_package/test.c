/* Consumer test for the packaged kazlib 1.21.
 *
 * Exercises the public API of three modules through the installed headers,
 * including the dict strict-bound lookups introduced in 1.21. Every step
 * asserts its postcondition; a successful run prints one summary line.
 *
 * Release profiles compile with -DNDEBUG, which would compile every assert()
 * away and turn this into an assertion-free smoke run. Keep the checks
 * mandatory: this file must always validate, in every build type.
 */
#undef NDEBUG
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include <kazlib/dict.h>
#include <kazlib/hash.h>
#include <kazlib/list.h>

static int str_compare(const void *left, const void *right)
{
    return strcmp((const char *) left, (const char *) right);
}

static void test_list(void)
{
    static const char *const values[] = { "charlie", "alpha", "bravo" };
    list_t *list;
    size_t i;

    list = list_create(LISTCOUNT_T_MAX);
    assert(list != NULL);

    for (i = 0; i < sizeof values / sizeof values[0]; i++) {
        lnode_t *node = lnode_create((void *) values[i]);
        assert(node != NULL);
        list_append(list, node);
    }

    assert(list_count(list) == 3);
    assert(list_find(list, "bravo", str_compare) != NULL);
    assert(list_find(list, "delta", str_compare) == NULL);

    list_destroy_nodes(list);
    list_destroy(list);
}

static void test_dict(void)
{
    dict_t *dict;
    dnode_t *node;

    dict = dict_create(DICTCOUNT_T_MAX, str_compare);
    assert(dict != NULL);

    assert(dict_alloc_insert(dict, "1", "one"));
    assert(dict_alloc_insert(dict, "2", "two"));
    assert(dict_alloc_insert(dict, "3", "three"));
    assert(dict_count(dict) == 3);

    node = dict_lookup(dict, "2");
    assert(node != NULL && strcmp(dnode_get(node), "two") == 0);
    assert(dict_lookup(dict, "9") == NULL);

    /* 1.21 headline feature. Note the upstream naming is inverted relative
     * to C++ STL: dict_strict_lower_bound() returns the lowest key that is
     * GREATER than the given key, and dict_strict_upper_bound() the greatest
     * key that is LOWER than it (see dict.c comments). */
    node = dict_strict_lower_bound(dict, "2");
    assert(node != NULL && strcmp(dnode_getkey(node), "3") == 0);
    node = dict_strict_upper_bound(dict, "2");
    assert(node != NULL && strcmp(dnode_getkey(node), "1") == 0);
    assert(dict_strict_lower_bound(dict, "3") == NULL);
    assert(dict_strict_upper_bound(dict, "1") == NULL);

    dict_free_nodes(dict);
    dict_destroy(dict);
}

static void test_hash(void)
{
    static const char *const pairs[][2] = {
        { "k1", "v1" }, { "k2", "v2" }, { "k3", "v3" },
    };
    hash_t *hash;
    hnode_t *node;
    size_t i;

    /* NULL hash function selects the built-in default. */
    hash = hash_create(HASHCOUNT_T_MAX, str_compare, NULL);
    assert(hash != NULL);

    for (i = 0; i < sizeof pairs / sizeof pairs[0]; i++) {
        assert(hash_alloc_insert(hash, pairs[i][0], (void *) pairs[i][1]));
    }

    assert(hash_count(hash) == 3);
    node = hash_lookup(hash, "k2");
    assert(node != NULL && strcmp(hnode_get(node), "v2") == 0);
    assert(hash_lookup(hash, "missing") == NULL);

    hash_free_nodes(hash);
    hash_destroy(hash);
}

int main(void)
{
    test_list();
    test_dict();
    test_hash();
    printf("kazlib consumer test passed: list/dict/hash with 1.21 strict bounds\n");
    return 0;
}
