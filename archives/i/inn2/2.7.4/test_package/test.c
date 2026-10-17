/*
**  Consumer test for inn2/2.7.4 -- exercises libinn's public API.
**
**  Linking against libinn proves the packaged library and headers are usable;
**  the assertions below verify four independent subsystems at run time
**  (doubly-linked lists, the generic hash table, MD5, string concat).
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <inn/concat.h>
#include <inn/hashtab.h>
#include <inn/list.h>
#include <inn/md5.h>

static int failures = 0;

#define CHECK(cond, what)                                              \
    do {                                                               \
        if (cond) {                                                    \
            printf("ok   - %s\n", (what));                             \
        } else {                                                       \
            printf("FAIL - %s\n", (what));                             \
            failures++;                                                \
        }                                                              \
    } while (0)

/* A list node carries a payload: libinn's standard embedding idiom, relying
   on `struct node` being the first member so the two pointers alias. */
struct item {
    struct node node;
    int value;
};

static struct item *
item_of(struct node *node)
{
    return (struct item *) node;
}

/* Hash entries embed their own key: libinn recovers the key from the stored
   datum through the hash_key_func callback, so the datum must outlive the
   table and must not be replaced by a different key. */
struct entry {
    const char *name;
    int value;
};

/* --- generic hash table callbacks ---------------------------------------- */

static unsigned long
t_hash_string(const void *key)
{
    const unsigned char *p = key;
    unsigned long h = 5381;

    while (*p != '\0')
        h = ((h << 5) + h) + *p++;
    return h;
}

static const void *
hash_key_string(const void *datum)
{
    return ((const struct entry *) datum)->name;
}

/* libinn calls this as equal(key, stored_datum); the datum is a struct entry,
   so the comparison has to reach its embedded name. */
static bool
hash_equal_string(const void *a, const void *b)
{
    return strcmp(a, ((const struct entry *) b)->name) == 0;
}

static void
hash_delete_noop(void *datum)
{
    (void) datum;
}

/* --- helpers ------------------------------------------------------------- */

static void
to_hex(const unsigned char *digest, char *out)
{
    static const char hex[] = "0123456789abcdef";
    int i;

    for (i = 0; i < MD5_DIGESTSIZE; i++) {
        out[i * 2] = hex[digest[i] >> 4];
        out[i * 2 + 1] = hex[digest[i] & 0x0f];
    }
    out[MD5_DIGESTSIZE * 2] = '\0';
}

/* --- list ---------------------------------------------------------------- */

static void
test_list(void)
{
    struct list list;
    struct item a, b, c;
    struct node *node;

    list_new(&list);
    CHECK(list_isempty(&list), "list_new yields an empty list");

    a.value = 1;
    b.value = 2;
    c.value = 3;
    list_addtail(&list, &a.node);
    list_addtail(&list, &b.node);
    list_addhead(&list, &c.node);

    CHECK(!list_isempty(&list), "list reports non-empty after inserts");
    CHECK(item_of(list_head(&list))->value == 3, "list_addhead puts node at head");
    CHECK(item_of(list_tail(&list))->value == 2, "list_addtail builds in order");

    /* Head -> tail walk must yield 3, 1, 2. */
    node = list_head(&list);
    CHECK(item_of(node)->value == 3, "list_head returns first node");
    node = list_succ(node);
    CHECK(node != NULL && item_of(node)->value == 1, "list_succ walks forward");
    node = list_succ(node);
    CHECK(node != NULL && item_of(node)->value == 2, "list_succ reaches last node");
    CHECK(list_succ(node) == NULL, "list_succ past tail returns NULL");

    /* Tail -> head walk must yield 2, 1, 3. */
    node = list_tail(&list);
    CHECK(item_of(node)->value == 2, "list_tail returns last node");
    node = list_pred(node);
    CHECK(node != NULL && item_of(node)->value == 1, "list_pred walks backward");
    node = list_pred(node);
    CHECK(node != NULL && item_of(node)->value == 3, "list_pred reaches first node");
    CHECK(list_pred(node) == NULL, "list_pred before head returns NULL");

    list_remove(&b.node);
    CHECK(item_of(list_tail(&list))->value == 1, "list_remove unlinks the middle node");

    list_remhead(&list);
    list_remhead(&list);
    CHECK(list_isempty(&list), "list_remhead drains the list back to empty");
}

/* --- hash table ---------------------------------------------------------- */

static void
test_hashtab(void)
{
    struct hash *hash;
    struct entry one = { "one", 1 };
    struct entry two = { "two", 2 };
    struct entry three = { "three", 3 };
    struct entry one_repl = { "one", 99 };
    struct entry *found;

    hash = hash_create(8, t_hash_string, hash_key_string, hash_equal_string,
                       hash_delete_noop);
    CHECK(hash != NULL, "hash_create returns a usable table");

    CHECK(hash_insert(hash, one.name, &one), "hash_insert accepts a new key");
    CHECK(hash_insert(hash, two.name, &two), "hash_insert accepts a second key");
    CHECK(!hash_insert(hash, one.name, &three), "hash_insert rejects a duplicate key");
    CHECK(hash_count(hash) == 2, "hash_count tracks the number of entries");

    found = hash_lookup(hash, one.name);
    CHECK(found == &one && found->value == 1, "hash_lookup returns the stored datum");
    CHECK(hash_lookup(hash, three.name) == NULL, "hash_lookup misses an absent key");

    /* The replacement must keep its own key ("one"), which is what makes the
       entry still findable through the original key afterwards. */
    CHECK(hash_replace(hash, one.name, &one_repl), "hash_replace swaps the datum");
    found = hash_lookup(hash, one.name);
    CHECK(found == &one_repl && found->value == 99,
          "hash_lookup sees the replaced datum");
    CHECK(hash_count(hash) == 2, "hash_replace does not change the count");

    CHECK(hash_delete(hash, one.name), "hash_delete removes an existing key");
    CHECK(hash_lookup(hash, one.name) == NULL, "deleted key is no longer found");
    CHECK(hash_count(hash) == 1, "hash_count drops after delete");
    CHECK(!hash_delete(hash, one.name), "hash_delete reports a missing key");

    hash_free(hash);
}

/* --- md5 ----------------------------------------------------------------- */

static void
test_md5(void)
{
    unsigned char digest[MD5_DIGESTSIZE];
    char hex[MD5_DIGESTSIZE * 2 + 1];
    struct md5_context ctx;

    /* RFC 1321 test vectors. */
    md5_hash((const unsigned char *) "", 0, digest);
    to_hex(digest, hex);
    CHECK(strcmp(hex, "d41d8cd98f00b204e9800998ecf8427e") == 0,
          "md5_hash matches the MD5 of the empty string");

    md5_hash((const unsigned char *) "abc", 3, digest);
    to_hex(digest, hex);
    CHECK(strcmp(hex, "900150983cd24fb0d6963f7d28e17f72") == 0,
          "md5_hash matches RFC 1321 'abc' vector");

    md5_hash((const unsigned char *) "message digest", 14, digest);
    to_hex(digest, hex);
    CHECK(strcmp(hex, "f96b697d7cb7938d525a2f31aaf161d0") == 0,
          "md5_hash matches RFC 1321 'message digest' vector");

    /* The incremental interface must agree with the one-shot helper. */
    md5_init(&ctx);
    md5_update(&ctx, (const unsigned char *) "ab", 2);
    md5_update(&ctx, (const unsigned char *) "c", 1);
    md5_final(&ctx);
    to_hex(ctx.digest, hex);
    CHECK(strcmp(hex, "900150983cd24fb0d6963f7d28e17f72") == 0,
          "md5_update/md5_final agrees with md5_hash");
}

/* --- concat -------------------------------------------------------------- */

static void
test_concat(void)
{
    char *joined;
    char *path;

    joined = concat("inn", "-", "test", (char *) NULL);
    CHECK(joined != NULL && strcmp(joined, "inn-test") == 0,
          "concat joins variadic segments");
    free(joined);

    path = concatpath("/usr/local", "etc");
    CHECK(path != NULL && strcmp(path, "/usr/local/etc") == 0,
          "concatpath joins a directory and a file name");
    free(path);
}

int
main(void)
{
    printf("# libinn consumer test\n");

    test_list();
    test_hashtab();
    test_md5();
    test_concat();

    if (failures == 0) {
        printf("# all checks passed\n");
        return 0;
    }
    printf("# %d check(s) failed\n", failures);
    return 1;
}
