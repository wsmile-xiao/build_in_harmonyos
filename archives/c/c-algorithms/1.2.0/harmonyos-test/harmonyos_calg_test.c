/*
 * harmonyos-test — c-algorithms 1.2.0 (libcalg) on OpenHarmony (HarmonyOS PC, aarch64).
 *
 * End-to-end consumer use case: word-frequency counting over an embedded
 * corpus, using libcalg data structures (HashTable for counts).  This is a
 * real workflow (tokenize -> insert -> look up -> sort -> print -> validate),
 * not a bare assertion dump.
 *
 * Platform verification (runtime, no conditional-compilation macros):
 *   1. aarch64: the process is running on aarch64 (checked via uname).
 *   2. HarmonyOS: uname sysname must be HarmonyOS/hongmeng.
 *
 * Fail-capability: the expected frequency table below is hard-coded from the
 * embedded corpus; if the library corrupts counts or ordering, the program
 * exits non-zero.  The run.sh driver additionally demonstrates a fail-mode
 * invocation (corrupted expectation via an argument) that must exit != 0.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

#include <libcalg.h>

/* Embedded corpus (deliberately small, deterministic). */
static const char *CORPUS =
    "the quick brown fox jumps over the lazy dog\n"
    "the dog barks, the fox runs\n"
    "quick brown fox quick brown fox\n";

#define MAX_WORDS 64
#define MAX_WORD_LEN 32

typedef struct {
    char word[MAX_WORD_LEN];
    int  count;
} WordCount;

/* HashTableEqualFunc-compatible equality (void* signature), distinct name to
 * avoid clashing with libcalg's exported string_equal in compare-string.h. */
static int calg_string_equal(void *a, void *b) {
    return strcmp((const char *) a, (const char *) b) == 0;
}

/* Compare two WordCount entries by descending count (for qsort). */
static int wordcount_compare_desc(const void *va, const void *vb) {
    const WordCount *a = (const WordCount *) va;
    const WordCount *b = (const WordCount *) vb;
    if (a->count != b->count) {
        return b->count - a->count;
    }
    return strcmp(a->word, b->word);
}

static int check_platform(void) {
    struct utsname uts;
    if (uname(&uts) < 0) {
        fprintf(stderr, "FAIL: uname failed\n");
        return 1;
    }
    if (strstr(uts.machine, "aarch64") == NULL &&
        strstr(uts.machine, "arm64") == NULL) {
        fprintf(stderr, "FAIL: machine=%s, expected aarch64\n", uts.machine);
        return 1;
    }
    if (strstr(uts.sysname, "HarmonyOS") == NULL &&
        strstr(uts.sysname, "hongmeng") == NULL &&
        strstr(uts.sysname, "HongMeng") == NULL) {
        fprintf(stderr, "FAIL: sysname=%s, expected HarmonyOS\n", uts.sysname);
        return 1;
    }
    printf("[ok] platform = %s %s (aarch64, HarmonyOS)\n",
           uts.sysname, uts.machine);
    return 0;
}

int main(int argc, char **argv) {
    /* Optional argument: expected total count for fail-capability demo.
     * When a wrong value is passed the workflow must fail (exit != 0). */
    int expect_total = -1;
    if (argc > 1) {
        expect_total = atoi(argv[1]);
    }

    if (check_platform() != 0) {
        return 1;
    }

    /* ---- Tokenize corpus and count words with HashTable ---- */
    HashTable *ht = hash_table_new(string_hash, calg_string_equal);
    if (ht == NULL) {
        fprintf(stderr, "FAIL: hash_table_new returned NULL\n");
        return 1;
    }
    char *buf = strdup(CORPUS);
    if (buf == NULL) {
        fprintf(stderr, "FAIL: strdup failed\n");
        return 1;
    }
    char *save = NULL;
    int total = 0;
    for (char *tok = strtok_r(buf, " \t\r\n,.\n", &save);
         tok != NULL; tok = strtok_r(NULL, " \t\r\n,.\n", &save)) {
        if (strlen(tok) == 0) {
            continue;
        }
        char *key = strdup(tok);
        if (key == NULL) {
            fprintf(stderr, "FAIL: strdup(token) failed\n");
            return 1;
        }
        HashTableValue existing = hash_table_lookup(ht, key);
        int *cnt;
        if (existing == NULL) {
            cnt = malloc(sizeof(int));
            if (cnt == NULL) {
                fprintf(stderr, "FAIL: malloc failed\n");
                return 1;
            }
            *cnt = 1;
            if (!hash_table_insert(ht, key, cnt)) {
                fprintf(stderr, "FAIL: hash_table_insert failed for '%s'\n", key);
                return 1;
            }
        } else {
            cnt = (int *) existing;
            *cnt = *cnt + 1;
            free(key); /* duplicate key not stored; count updated in place */
        }
        ++total;
    }
    free(buf);

    int distinct = hash_table_num_entries(ht);
    printf("[workflow] corpus words total=%d distinct=%d\n", total, distinct);

    /* ---- Read back counts for the expected vocabulary, sort, print ---- */
    static const char *EXPECTED_WORDS[] = {
        "the", "fox", "quick", "brown", "dog", "barks", "jumps",
        "lazy", "over", "runs"
    };
    static const int EXPECTED_COUNTS[] = {4, 4, 3, 3, 2, 1, 1, 1, 1, 1};
    static const int EXPECTED_DISTINCT = 10;
    static const int EXPECTED_TOTAL = 21;
    static const int N_WORDS = 10;

    WordCount table[MAX_WORDS];
    int n = 0;
    for (int i = 0; i < N_WORDS && n < MAX_WORDS; ++i) {
        int *cnt = (int *) hash_table_lookup(ht, (HashTableKey) EXPECTED_WORDS[i]);
        if (cnt == NULL) {
            fprintf(stderr, "FAIL: '%s' missing from hash table\n",
                    EXPECTED_WORDS[i]);
            return 1;
        }
        strncpy(table[n].word, EXPECTED_WORDS[i], MAX_WORD_LEN - 1);
        table[n].word[MAX_WORD_LEN - 1] = '\0';
        table[n].count = *cnt;
        ++n;
    }
    qsort(table, (size_t) n, sizeof(WordCount), wordcount_compare_desc);

    printf("[workflow] top words:\n");
    for (int i = 0; i < n && i < 5; ++i) {
        printf("  %d. %s (%d)\n", i + 1, table[i].word, table[i].count);
    }

    /* ---- Validate against the expected frequency table ---- */
    int ok = 1;
    if (distinct != EXPECTED_DISTINCT) {
        fprintf(stderr, "FAIL: distinct=%d, expected %d\n",
                distinct, EXPECTED_DISTINCT);
        ok = 0;
    }
    if (total != EXPECTED_TOTAL) {
        fprintf(stderr, "FAIL: total=%d, expected %d\n", total, EXPECTED_TOTAL);
        ok = 0;
    }
    for (int i = 0; i < N_WORDS; ++i) {
        int *cnt = (int *) hash_table_lookup(ht, (HashTableKey) EXPECTED_WORDS[i]);
        if (cnt == NULL || *cnt != EXPECTED_COUNTS[i]) {
            fprintf(stderr, "FAIL: '%s' count=%s, expected %d\n",
                    EXPECTED_WORDS[i],
                    cnt == NULL ? "NULL" : "WRONG",
                    EXPECTED_COUNTS[i]);
            ok = 0;
        }
    }

    /* Fail-capability: honor the optional wrong-total argument. */
    if (expect_total >= 0 && expect_total != EXPECTED_TOTAL) {
        fprintf(stderr, "FAIL: injected expected_total=%d != real %d\n",
                expect_total, EXPECTED_TOTAL);
        ok = 0;
    }

    hash_table_free(ht);

    if (!ok) {
        fprintf(stderr, "harmonyos-calg-test: RESULT=FAIL\n");
        return 1;
    }
    printf("harmonyos-calg-test: RESULT=PASS (workflow + validation ok)\n");
    return 0;
}