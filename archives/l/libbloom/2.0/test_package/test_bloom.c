#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bloom.h"

static const char *save_path(void) {
    const char *tmp = getenv("TMPDIR");
    static char buf[1024];
    if (tmp == NULL || tmp[0] == '\0') {
        tmp = getenv("TMP");
    }
    if (tmp == NULL || tmp[0] == '\0') {
        tmp = getenv("TEMP");
    }
    if (tmp == NULL || tmp[0] == '\0') {
        return "libbloom_test_save.bf";
    }
    snprintf(buf, sizeof(buf), "%s/libbloom_test_save.bf", tmp);
    return buf;
}

/* Case 1: init/add/check round-trip on the shared/static lib. */
static int case_basic(void) {
    struct bloom bloom;
    memset(&bloom, 0, sizeof(bloom));
    if (bloom_init2(&bloom, 10000, 0.01) != 0) {
        printf("[FAIL] basic: bloom_init2 failed\n");
        return 1;
    }
    if (bloom_check(&bloom, "hello world", 11) != 0) {
        printf("[FAIL] basic: unexpected hit before add\n");
        bloom_free(&bloom);
        return 1;
    }
    if (bloom_add(&bloom, "hello world", 11) != 0) {
        printf("[FAIL] basic: bloom_add reported present before insert\n");
        bloom_free(&bloom);
        return 1;
    }
    if (bloom_check(&bloom, "hello world", 11) != 1) {
        printf("[FAIL] basic: bloom_check missed inserted element\n");
        bloom_free(&bloom);
        return 1;
    }
    if (bloom_add(&bloom, "hello world", 11) <= 0) {
        printf("[FAIL] basic: second add should report already present\n");
        bloom_free(&bloom);
        return 1;
    }
    if (bloom.ready != 1) {
        printf("[FAIL] basic: filter not marked ready after init\n");
        bloom_free(&bloom);
        return 1;
    }
    printf("[INFO] basic: entries=%u bits=%lu version=%s\n",
           bloom.entries, bloom.bits, bloom_version());
    printf("[PASS] basic: init/add/check round-trip\n");
    bloom_free(&bloom);
    return 0;
}

/* Case 2: save/load persistence round-trip. */
static int case_save_load(void) {
    struct bloom bloom;
    struct bloom loaded;
    const char *path = save_path();
    int i;
    char key[64];

    memset(&bloom, 0, sizeof(bloom));
    memset(&loaded, 0, sizeof(loaded));
    if (bloom_init2(&bloom, 10000, 0.01) != 0) {
        printf("[FAIL] save_load: bloom_init2 failed\n");
        return 1;
    }
    for (i = 0; i < 500; i++) {
        snprintf(key, sizeof(key), "persist-key-%d", i);
        bloom_add(&bloom, key, (int)strlen(key));
    }
    if (bloom_save(&bloom, (char *)path) != 0) {
        printf("[FAIL] save_load: bloom_save failed for %s\n", path);
        bloom_free(&bloom);
        return 1;
    }
    bloom_free(&bloom);
    if (bloom_load(&loaded, (char *)path) != 0) {
        printf("[FAIL] save_load: bloom_load failed for %s\n", path);
        remove(path);
        return 1;
    }
    for (i = 0; i < 500; i++) {
        snprintf(key, sizeof(key), "persist-key-%d", i);
        if (bloom_check(&loaded, key, (int)strlen(key)) != 1) {
            printf("[FAIL] save_load: element %d missing after load\n", i);
            bloom_free(&loaded);
            remove(path);
            return 1;
        }
    }
    printf("[PASS] save_load: 500 elements survive save/load via %s\n", path);
    bloom_free(&loaded);
    remove(path);
    return 0;
}

/* Case 3: merge two compatible filters. */
static int case_merge(void) {
    struct bloom dest;
    struct bloom src;
    char key[64];
    int i;

    memset(&dest, 0, sizeof(dest));
    memset(&src, 0, sizeof(src));
    if (bloom_init2(&dest, 10000, 0.01) != 0 || bloom_init2(&src, 10000, 0.01) != 0) {
        printf("[FAIL] merge: bloom_init2 failed\n");
        bloom_free(&dest);
        bloom_free(&src);
        return 1;
    }
    for (i = 0; i < 200; i++) {
        snprintf(key, sizeof(key), "dest-key-%d", i);
        bloom_add(&dest, key, (int)strlen(key));
        snprintf(key, sizeof(key), "src-key-%d", i);
        bloom_add(&src, key, (int)strlen(key));
    }
    if (bloom_merge(&dest, &src) != 0) {
        printf("[FAIL] merge: bloom_merge failed on compatible filters\n");
        bloom_free(&dest);
        bloom_free(&src);
        return 1;
    }
    for (i = 0; i < 200; i++) {
        snprintf(key, sizeof(key), "dest-key-%d", i);
        if (bloom_check(&dest, key, (int)strlen(key)) != 1) {
            printf("[FAIL] merge: dest element %d missing after merge\n", i);
            bloom_free(&dest);
            bloom_free(&src);
            return 1;
        }
        snprintf(key, sizeof(key), "src-key-%d", i);
        if (bloom_check(&dest, key, (int)strlen(key)) != 1) {
            printf("[FAIL] merge: src element %d missing after merge\n", i);
            bloom_free(&dest);
            bloom_free(&src);
            return 1;
        }
    }
    printf("[PASS] merge: 400 elements visible after bloom_merge\n");
    bloom_free(&dest);
    bloom_free(&src);
    return 0;
}

int main(void) {
    int failed = 0;

    printf("libbloom consumer tests (version %s)\n", bloom_version());
    failed += case_basic();
    failed += case_save_load();
    failed += case_merge();

    if (failed == 0) {
        printf("RESULT: 3 passed, 0 failed\n");
        return 0;
    }
    printf("RESULT: %d failed\n", failed);
    return 1;
}
