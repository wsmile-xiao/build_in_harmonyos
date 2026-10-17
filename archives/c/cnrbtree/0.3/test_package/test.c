// cnrbtree consumer verification test (HarmonyOS)
// Simulates a business upper-layer component that uses cnrbtree ONLY through
// its installed public header (cnrbtree.h) and public API: template
// instantiation, create/access/get/remove/destroy, RBA/RBHAS/RBFOREACH/
// RBDESTROY, and the built-in cnstrset / cnstrstrmap convenience types.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define CNRBTREE_IMPLEMENTATION
#include "cnrbtree.h"

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("PASS: %s\n", msg); } \
} while (0)

// Business payload: a small object as a consumer would define.
typedef struct record_t {
    int id;
    long score;
} record;
typedef char * keystr;

CNRBTREETEMPLATE(keystr, record, RBstrcmp, RBstrcpy, RBstrdel)

// ---- Consumer scenario 1: string-set (built-in cnstrset) ----
static void test_strset(void) {
    cnstrset * set = cnstrset_create();
    CHECK(set != NULL, "cnstrset_create returns non-NULL");

    cnstrset_insert(set, "apple");
    cnstrset_insert(set, "banana");
    cnstrset_insert(set, "cherry");
    CHECK(RBHAS(set, "apple") != 0, "RBHAS apple after insert");
    CHECK(RBHAS(set, "banana") != 0, "RBHAS banana after insert");
    CHECK(RBHAS(set, "cherry") != 0, "RBHAS cherry after insert");
    CHECK(RBHAS(set, "durian") == 0, "RBHAS durian absent");

    int count = 0;
    char * si;
    cnstrset_foreach(set, si) {
        count++;
    }
    CHECK(count == 3, "foreach counts 3 inserted keys");

    cnstrset_remove(set, "banana");
    CHECK(RBHAS(set, "banana") == 0, "RBHAS banana after remove");
    CHECK(RBHAS(set, "apple") != 0, "RBHAS apple remains");
    cnstrset_destroy(set);
    printf("test_strset done\n");
}

// ---- Consumer scenario 2: string->string dictionary (built-in cnstrstrmap) ----
static void test_strstrmap(void) {
    cnstrstrmap * dict = cnstrstrmap_create();
    CHECK(dict != NULL, "cnstrstrmap_create returns non-NULL");

    RBA(dict, "key1") = "value1";
    RBA(dict, "key2") = "value2";
    RBA(dict, "key3") = "value3";
    CHECK(RBHAS(dict, "key2") != 0, "RBHAS key2");
    CHECK(strcmp(RBA(dict, "key1"), "value1") == 0, "RBA key1 == value1");
    CHECK(strcmp(RBA(dict, "key3"), "value3") == 0, "RBA key3 == value3");

    int count = 0;
    char * k, * v;
    cnstrstrmap_foreach(dict, k, v) {
        count++;
        CHECK(k != NULL && v != NULL, "foreach yields non-NULL key/value");
    }
    CHECK(count == 3, "dict foreach counts 3 entries");

    cnstrstrmap_remove(dict, "key2");
    CHECK(RBHAS(dict, "key2") == 0, "key2 removed");
    cnstrstrmap_destroy(dict);
    printf("test_strstrmap done\n");
}

// ---- Consumer scenario 3: custom templated tree (str -> record) ----
static void test_custom_tree(void) {
    cnrbtree_keystrrecord * tree = cnrbtree_keystrrecord_create();
    CHECK(tree != NULL, "cnrbtree_keystrrecord_create returns non-NULL");

    RBA(tree, "alice").id = 1;   RBA(tree, "alice").score = 95;
    RBA(tree, "bob").id = 2;     RBA(tree, "bob").score = 87;
    RBA(tree, "carol").id = 3;   RBA(tree, "carol").score = 91;

    CHECK(RBHAS(tree, "alice") != 0, "RBHAS alice");
    CHECK(RBA(tree, "alice").score == 95, "RBA alice score == 95");
    CHECK(RBA(tree, "carol").id == 3, "RBA carol id == 3");
    CHECK(RBGET(tree, "dave") == NULL, "RBGET dave is NULL");

    // In-place update, then re-read.
    RBA(tree, "bob").score = 100;
    CHECK(RBA(tree, "bob").score == 100, "RBA bob score updated to 100");

    long total = 0;
    int n = 0;
    cnrbtree_keystrrecord_node * i;
    RBFOREACH(keystrrecord, tree, i) {
        total += i->data.score;
        n++;
    }
    CHECK(n == 3, "custom tree foreach counts 3");
    CHECK(total == 286, "custom tree score total == 286");

    // Ordering sanity: keys come back sorted.
    const char * expect[3] = {"alice", "bob", "carol"};
    int idx = 0;
    RBFOREACH(keystrrecord, tree, i) {
        CHECK(strcmp(i->key, expect[idx]) == 0, "foreach key order sorted");
        idx++;
    }

    cnrbtree_keystrrecord_remove(tree, (keystr)"bob");
    CHECK(RBHAS(tree, "bob") == 0, "bob removed");
    RBDESTROY(tree);
    printf("test_custom_tree done\n");
}

// ---- Consumer scenario 4: numeric keys (int -> int) with random ops ----
#define intcomp(x, y) ((x) - (y))
#define intcopy(x, y, z) ((x) = (y), (z) = 0)
#define intdelete(x, y) ((void)(x), (void)(y))
CNRBTREETEMPLATE(int, int, intcomp, intcopy, intdelete)

static void test_int_tree(void) {
    cnrbtree_intint * tree = cnrbtree_intint_create();
    CHECK(tree != NULL, "cnrbtree_intint_create returns non-NULL");

    srand(0);
    const int N = 500;
    int keys[N];
    int i;
    for (i = 0; i < N; i++) {
        keys[i] = rand() % 100000;
        if (RBHAS(tree, keys[i])) { i--; continue; }
        RBA(tree, keys[i]) = keys[i] * 2;
    }
    CHECK(tree->size == N, "int tree size == N after inserts");

    for (i = 0; i < N; i++) {
        CHECK(RBGET(tree, keys[i]) != NULL, "int key present");
        CHECK(RBA(tree, keys[i]) == keys[i] * 2, "int value == key*2");
    }

    for (i = 0; i < N; i++) {
        cnrbtree_intint_remove(tree, keys[i]);
    }
    CHECK(tree->size == 0, "int tree empty after removal");
    cnrbtree_intint_destroy(tree);
    printf("test_int_tree done\n");
}

int main(void) {
    printf("cnrbtree consumer verification (HarmonyOS) starting\n");
    test_strset();
    test_strstrmap();
    test_custom_tree();
    test_int_tree();
    if (failures == 0) {
        printf("cnrbtree consumer verification: ALL PASSED (exit 0)\n");
        return 0;
    }
    fprintf(stderr, "cnrbtree consumer verification: %d FAILURES\n", failures);
    return 1;
}
