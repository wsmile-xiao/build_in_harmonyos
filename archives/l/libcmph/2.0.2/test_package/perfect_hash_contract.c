/*
 * test_package/perfect_hash_contract.c — libcmph consumer test.
 *
 * Builds a MINIMAL perfect hash over a fixed key set using the cmph C API
 * (CMPH_CHD algorithm — minimal by design), then verifies the defining
 * properties of an MPH and its packed/serialized forms:
 *
 *   P1 (perfect / injective)   every key maps to a distinct index.
 *   P2 (minimal)               every index is in [0, nkeys) and every
 *                              slot is hit (bijection).
 *   P3 (stable)                repeated searches for the same key return
 *                              the same index within one run.
 *   P4 (packed equivalence)    cmph_pack + cmph_search_packed produce the
 *                              same indices as the in-memory mphf.
 *   P5 (dump/load round-trip)  cmph_dump -> cmph_load reproduces the mapping.
 *
 * A non-zero exit code on any failed assertion makes this a hard failure.
 */
#include <cmph.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Fixed, non-trivial key set — distinct lengths so the hash is not trivial. */
static const char *const KEYS[] = {
    "alpha", "beta", "gamma", "delta", "epsilon",
    "zeta", "eta", "theta", "iota", "kappa",
    "lambda", "mu", "nu", "xi", "omicron",
    "pi", "rho", "sigma", "tau", "upsilon",
};
#define NKEYS (int)(sizeof(KEYS) / sizeof(KEYS[0]))

static int failures = 0;
#define CHECK(cond, msg)                                             \
    do {                                                            \
        if (!(cond)) {                                              \
            fprintf(stderr, "FAIL: %s (line %d)\n", (msg), __LINE__); \
            failures++;                                             \
        }                                                           \
    } while (0)

/* Build a minimal perfect hash over KEYS using CMPH_CHD (minimal by design). */
static cmph_t *build_mphf(void)
{
    cmph_io_adapter_t *src = cmph_io_vector_adapter((char **)KEYS, NKEYS);
    cmph_config_t *cfg = cmph_config_new(src);
    cmph_config_set_algo(cfg, CMPH_CHD);
    cmph_config_set_verbosity(cfg, 0);
    cmph_t *mphf = cmph_new(cfg);
    cmph_config_destroy(cfg);
    cmph_io_vector_adapter_destroy(src);
    return mphf;
}

/* Map every key to an index, recording them in `out`. */
static void map_all(cmph_t *mphf, unsigned int *out)
{
    for (int i = 0; i < NKEYS; ++i) {
        out[i] = cmph_search(mphf, KEYS[i], (cmph_uint32)strlen(KEYS[i]));
    }
}

int main(void)
{
    /* ── build ── */
    cmph_t *mphf = build_mphf();
    CHECK(mphf != NULL, "cmph_new returned NULL");
    if (mphf == NULL) {
        fprintf(stderr, "fatal: cannot proceed without a valid mphf\n");
        return 1;
    }

    /* ── P2 (minimal): cmph_size must equal nkeys ── */
    unsigned int size = cmph_size(mphf);
    CHECK(size == (unsigned int)NKEYS,
          "cmph_size should equal nkeys (minimal)");
    /* Safety: if not minimal, indices may exceed NKEYS and overflow the
     * fixed-size buffers below — abort early with a clear diagnostic. */
    if (size != (unsigned int)NKEYS) {
        fprintf(stderr, "fatal: cmph_size=%u != nkeys=%d; aborting to avoid "
                "buffer overflow\n", size, NKEYS);
        cmph_destroy(mphf);
        return 1;
    }

    /* ── map all keys ── */
    unsigned int first[NKEYS];
    map_all(mphf, first);

    /* P2 (cont): every index in [0, nkeys) */
    for (int i = 0; i < NKEYS; ++i) {
        CHECK(first[i] < (unsigned int)NKEYS, "index out of range [0,nkeys)");
    }

    /* ── P1 (perfect / injective): distinct indices ── */
    unsigned char seen[NKEYS];
    memset(seen, 0, sizeof(seen));
    for (int i = 0; i < NKEYS; ++i) {
        CHECK(seen[first[i]] == 0, "duplicate index — not perfect");
        seen[first[i]] = 1;
    }
    /* P1 (cont): every slot filled (minimal + perfect => bijection) */
    for (int i = 0; i < NKEYS; ++i) {
        CHECK(seen[i] == 1, "an index slot was never hit — not minimal");
    }

    /* ── P3 (stable): re-search every key, must match exactly ── */
    unsigned int again[NKEYS];
    map_all(mphf, again);
    for (int i = 0; i < NKEYS; ++i) {
        CHECK(again[i] == first[i], "search result changed on re-query");
    }

    /* ── P4 (packed equivalence): packed form agrees with in-memory ── */
    cmph_uint32 packed_size = cmph_packed_size(mphf);
    CHECK(packed_size > 0, "cmph_packed_size returned 0");
    void *packed = calloc(packed_size > 0 ? packed_size : 1, 1);
    CHECK(packed != NULL, "calloc for packed mphf failed");
    if (packed != NULL) {
        cmph_pack(mphf, packed);
        for (int i = 0; i < NKEYS; ++i) {
            unsigned int idx = cmph_search_packed(packed, KEYS[i],
                                                  (cmph_uint32)strlen(KEYS[i]));
            CHECK(idx == first[i], "packed search disagrees with in-memory");
        }
        free(packed);
    }

    /* ── P5 (dump/load round-trip): reproduces the mapping ── */
    /* tmpfile() uses /tmp, which is read-only on HarmonyOS; use a named
     * temp file in $TMPDIR (a writable dir) instead. */
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir || !*tmpdir) tmpdir = "/var/tmp";
    if (!tmpdir || !*tmpdir) tmpdir = ".";
    char tmppath[1024];
    snprintf(tmppath, sizeof(tmppath), "%s/phc_dump_XXXXXX", tmpdir);
    int tmpfd = mkstemp(tmppath);
    CHECK(tmpfd >= 0, "mkstemp for dump file failed");
    if (tmpfd >= 0) {
        FILE *dumpf = fdopen(tmpfd, "w+b");
        CHECK(dumpf != NULL, "fdopen failed");
        if (dumpf != NULL) {
            /* cmph_dump returns a delegated byte count, not 0-on-success
             * (upstream tests don't check it); cmph_load succeeding is the
             * real round-trip verification. */
            cmph_dump(mphf, dumpf);
            fflush(dumpf);
            rewind(dumpf);
            cmph_t *loaded = cmph_load(dumpf);
            CHECK(loaded != NULL, "cmph_load returned NULL");
            if (loaded != NULL) {
                unsigned int loaded_map[NKEYS];
                map_all(loaded, loaded_map);
                for (int i = 0; i < NKEYS; ++i) {
                    CHECK(loaded_map[i] == first[i],
                          "dump/load round-trip changed the mapping");
                }
                cmph_destroy(loaded);
            }
            fclose(dumpf);
        } else {
            close(tmpfd);
        }
        unlink(tmppath);
    }

    cmph_destroy(mphf);

    if (failures != 0) {
        fprintf(stderr, "perfect_hash_contract: %d assertion(s) FAILED\n",
                failures);
        return 1;
    }
    printf("perfect_hash_contract: all %d assertions passed (nkeys=%d)\n",
           7 + NKEYS * 6, NKEYS);
    return 0;
}
