#define _POSIX_C_SOURCE 200112L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <libjodycode.h>

static int expect_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    int failures = 0;
    char path[JC_PATHBUF_SIZE];
    jodyhash_t data1[4] = {1, 2, 3, 4};
    jodyhash_t data2[4] = {1, 2, 3, 4};
    jodyhash_t hash1 = 0;
    jodyhash_t hash2 = 0;
    time_t epoch;

    failures += expect_true(strcmp(jc_version, "4.1.2") == 0, "runtime version is 4.1.2");
    failures += expect_true(strcmp(jc_verdate, "2026-02-08") == 0, "runtime version date matches");
    failures += expect_true(jc_api_version == 4, "API version is 4");
    failures += expect_true(jc_api_featurelevel >= 5, "API feature level is at least 5");

    failures += expect_true(jc_streq("jody", "jody") == 0, "jc_streq equal strings");
    failures += expect_true(jc_streq("jody", "code") != 0, "jc_streq different strings");
    failures += expect_true(jc_strneq("abcdef", "abcxyz", 3) == 0, "jc_strneq prefix match");
    failures += expect_true(jc_strcaseeq("LibJodyCode", "libjodycode") == 0, "jc_strcaseeq ignores case");
    failures += expect_true(jc_numeric_strcmp("file9", "file10", 0) < 0, "numeric sort orders file9 before file10");

    strcpy(path, "/tmp/libjodycode/./alpha/../beta");
    failures += expect_true(jc_collapse_dotdot(path) == 0, "jc_collapse_dotdot succeeds");
    failures += expect_true(strcmp(path, "/tmp/libjodycode/beta") == 0, "jc_collapse_dotdot normalizes path");

    setenv("TZ", "UTC0", 1);
    tzset();
    epoch = jc_strtoepoch("1970-01-01 00:00:00");
    failures += expect_true(epoch == 0, "jc_strtoepoch parses Unix epoch in UTC");

    failures += expect_true(jc_size_suffix[0].multiplier == 1, "byte suffix multiplier is 1");
    failures += expect_true(strcmp(jc_size_suffix[2].suffix, "KiB") == 0, "KiB suffix is available");
    failures += expect_true(jc_size_suffix[2].shift == 10, "KiB suffix shift is 10");

    failures += expect_true(strcmp(jc_get_errname(1), "null") == 0, "error name lookup returns text");
    failures += expect_true(strcmp(jc_get_errdesc(1), "function received a bad NULL parameter") == 0,
                            "error description lookup returns text");

    failures += expect_true(jc_block_hash(NORMAL, data1, &hash1, 4) == 0, "normal block hash succeeds");
    failures += expect_true(jc_block_hash(NORMAL, data2, &hash2, 4) == 0, "repeat block hash succeeds");
    failures += expect_true(hash1 == hash2, "block hash is deterministic");

    if (failures != 0) {
        fprintf(stderr, "libjodycode test failed: %d checks failed\n", failures);
        return 1;
    }

    printf("libjodycode 4.1.2 consumer API test: OK\n");
    return 0;
}
