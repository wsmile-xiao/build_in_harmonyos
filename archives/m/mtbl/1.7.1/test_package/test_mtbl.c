/* test_package for mtbl 1.7.1 — exercises the installed library through its
 * real API: writer → completed file → reader → exact get, iterator order,
 * prefix/range iteration, missing-key behavior and negative/boundary cases.
 * Every step asserts concrete data; never just exit 0. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>

#include <mtbl.h>

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
        exit(1); \
    } \
    printf("ok: %s\n", msg); \
} while (0)

static const char tmp_path[] = "mtbl-test-package.sst";
static const char tmp_path_neg[] = "mtbl-test-package.neg.sst";

/* deterministic key/value: key = "k%05u", val = "v%05u-0123456789abcdef" */
static void
make_kv(char *kbuf, char *vbuf, unsigned i)
{
    snprintf(kbuf, 16, "k%05u", i);
    snprintf(vbuf, 32, "v%05u-0123456789abcdef", i);
}

int main(void)
{
    enum { NKEYS = 200 };
    char kbuf[16], vbuf[32];
    const uint8_t *key, *val;
    size_t len_key, len_val;
    mtbl_res res;
    struct mtbl_writer_options *wopt = mtbl_writer_options_init();
    struct mtbl_writer *w = mtbl_writer_init(tmp_path, wopt);
    CHECK(w != NULL, "writer init");

    /* 1. write 200 sorted keys (writer requires strictly ascending order) */
    for (unsigned i = 0; i < NKEYS; i++) {
        make_kv(kbuf, vbuf, i);
        res = mtbl_writer_add(w, (const uint8_t *)kbuf, strlen(kbuf),
                                 (const uint8_t *)vbuf, strlen(vbuf));
        CHECK(res == mtbl_res_success, "writer add");
    }
    mtbl_writer_destroy(&w);
    CHECK(w == NULL, "writer destroy finalizes file");

    /* negative: adding out-of-order keys must fail (writer requires strictly
     * ascending keys; separate path since writer_init refuses to overwrite
     * an existing file) */
    w = mtbl_writer_init(tmp_path_neg, wopt);
    CHECK(w != NULL, "second writer init");
    res = mtbl_writer_add(w, (const uint8_t *)"zzz", 3, (const uint8_t *)"1", 1);
    CHECK(res == mtbl_res_success, "add zzz");
    res = mtbl_writer_add(w, (const uint8_t *)"aaa", 3, (const uint8_t *)"1", 1);
    CHECK(res == mtbl_res_failure, "out-of-order add must fail");
    mtbl_writer_destroy(&w);
    unlink(tmp_path_neg);
    mtbl_writer_options_destroy(&wopt);

    /* 2. reader: verify the canonical table written above (200 keys).
     * tmp_path still exists — mtbl_writer_init refuses to overwrite an
     * existing file, which we also assert as a boundary behavior. */
    wopt = mtbl_writer_options_init();
    w = mtbl_writer_init(tmp_path, wopt);
    CHECK(w == NULL, "writer init on existing file returns NULL");
    mtbl_writer_options_destroy(&wopt);

    /* 3. reader: exact point queries */
    struct mtbl_reader_options *ropt = mtbl_reader_options_init();
    struct mtbl_reader *r = mtbl_reader_init(tmp_path, ropt);
    CHECK(r != NULL, "reader init");
    const struct mtbl_source *src = mtbl_reader_source(r);
    CHECK(src != NULL, "reader source");

    for (unsigned i = 0; i < NKEYS; i++) {
        make_kv(kbuf, vbuf, i);
        struct mtbl_iter *it = mtbl_source_get(src, (const uint8_t *)kbuf, strlen(kbuf));
        CHECK(it != NULL, "source_get returns iter");
        res = mtbl_iter_next(it, &key, &len_key, &val, &len_val);
        CHECK(res == mtbl_res_success, "iter_next for exact key");
        CHECK(len_key == strlen(kbuf) && memcmp(key, kbuf, len_key) == 0,
              "exact key bytes match");
        CHECK(len_val == strlen(vbuf) && memcmp(val, vbuf, len_val) == 0,
              "exact value bytes match");
        /* iter exhausted after the single match */
        res = mtbl_iter_next(it, &key, &len_key, &val, &len_val);
        CHECK(res == mtbl_res_failure, "iter exhausted after exact match");
        mtbl_iter_destroy(&it);
    }
    printf("ok: %d exact point queries verified\n", NKEYS);

    /* 4. missing key semantics (upstream GET semantics: the iterator seeks to
     * the first key >= the requested key; NULL is returned only when the
     * requested key sorts after the last key). For an absent in-range key
     * the first next() yields the *next* existing key and marks the iter
     * invalid — the follow-up next() must fail. */
    {
        /* k00123.5 sorts between existing keys k00123 and k00124 and does
         * not exist: GET semantics make the first next() fail */
        struct mtbl_iter *it = mtbl_source_get(src, (const uint8_t *)"k00123.5", 8);
        CHECK(it != NULL, "absent in-range key returns seek iter (GET semantics)");
        res = mtbl_iter_next(it, &key, &len_key, &val, &len_val);
        CHECK(res == mtbl_res_failure, "absent key: first next() fails");
        mtbl_iter_destroy(&it);
    }

    /* boundary: a key before the first seek-positions at the first entry but
     * GET reports no match (res failure); a key sorting after the last key
     * returns NULL */
    {
        struct mtbl_iter *it = mtbl_source_get(src, (const uint8_t *)"a00000", 6);
        CHECK(it != NULL, "key before first returns iter");
        res = mtbl_iter_next(it, &key, &len_key, &val, &len_val);
        CHECK(res == mtbl_res_failure, "key before first: no exact match");
        mtbl_iter_destroy(&it);
        it = mtbl_source_get(src, (const uint8_t *)"zzzzzz", 6);
        CHECK(it == NULL, "key after last returns NULL");
    }

    /* 5. full iteration in sorted order */
    {
        struct mtbl_iter *it = mtbl_source_iter(src);
        CHECK(it != NULL, "source_iter");
        unsigned i = 0;
        while ((res = mtbl_iter_next(it, &key, &len_key, &val, &len_val)) == mtbl_res_success) {
            make_kv(kbuf, vbuf, i);
            if (len_key != strlen(kbuf) || memcmp(key, kbuf, len_key) != 0 ||
                len_val != strlen(vbuf) || memcmp(val, vbuf, len_val) != 0) {
                fprintf(stderr, "FAIL: iteration order/value mismatch at %u\n", i);
                exit(1);
            }
            i++;
        }
        CHECK(i == NKEYS, "full iteration yields all 200 keys in order");
        mtbl_iter_destroy(&it);
    }

    /* 6. prefix iteration: "k0001" matches k00010..k00019 (10 keys) */
    {
        struct mtbl_iter *it = mtbl_source_get_prefix(src, (const uint8_t *)"k0001", 5);
        CHECK(it != NULL, "prefix iter not NULL");
        unsigned i = 0;
        while ((res = mtbl_iter_next(it, &key, &len_key, &val, &len_val)) == mtbl_res_success)
            i++;
        CHECK(i == 10, "prefix 'k0001' yields 10 keys");
        mtbl_iter_destroy(&it);
    }

    /* 7. range iteration [k00100, k00105] — mtbl ranges are inclusive on
     * both endpoints (reader_get_range seeks at key0, valid while key <= key1) */
    {
        struct mtbl_iter *it = mtbl_source_get_range(src,
            (const uint8_t *)"k00100", 6, (const uint8_t *)"k00105", 6);
        CHECK(it != NULL, "range iter not NULL");
        unsigned i = 0;
        char first[16] = {0}, last[16] = {0};
        while ((res = mtbl_iter_next(it, &key, &len_key, &val, &len_val)) == mtbl_res_success) {
            if (i == 0) { memcpy(first, key, len_key < 15 ? len_key : 15); }
            memcpy(last, key, len_key < 15 ? len_key : 15);
            i++;
        }
        CHECK(i == 6, "range [k00100,k00105] yields 6 keys (inclusive)");
        CHECK(strcmp(first, "k00100") == 0 && strcmp(last, "k00105") == 0,
              "range endpoints exact");
        mtbl_iter_destroy(&it);
    }

    /* 8. metadata sanity: data block size > 0 and compression reported */
    const struct mtbl_metadata *meta = mtbl_reader_metadata(r);
    CHECK(meta != NULL, "reader metadata");
    uint64_t dbs = mtbl_metadata_data_block_size(meta);
    CHECK(dbs > 0, "metadata data_block_size > 0");
    uint64_t comp = mtbl_metadata_compression_algorithm(meta);
    CHECK(comp == MTBL_COMPRESSION_NONE || comp == MTBL_COMPRESSION_SNAPPY ||
          comp == MTBL_COMPRESSION_ZLIB || comp == MTBL_COMPRESSION_LZ4 ||
          comp == MTBL_COMPRESSION_LZ4HC || comp == MTBL_COMPRESSION_ZSTD,
          "metadata compression algorithm valid");
    uint64_t cnt = mtbl_metadata_count_entries(meta);
    CHECK(cnt == NKEYS, "metadata count_entries == 200");

    /* 9. negative: reader must reject a nonexistent file */
    {
        struct mtbl_reader *bad = mtbl_reader_init("no-such-file.sst", ropt);
        CHECK(bad == NULL, "reader init on missing file returns NULL");
    }

    mtbl_reader_destroy(&r);
    mtbl_reader_options_destroy(&ropt);
    unlink(tmp_path);
    printf("ALL MTBL TESTS PASSED\n");
    return 0;
}
