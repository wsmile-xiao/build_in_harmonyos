#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libdumbtts.h>

/* test_package self-test: exercise the libdumbtts public API.
 * The library reads pronunciation config from /usr/share/dumbtts/,
 * /etc/dumbtts/ then $HOME/.dumbtts_<lang>.conf; the test_package
 * conanfile seeds the bundled conf/en.conf into $HOME before running. */

int main(void)
{
    struct dumbtts_conf *conf;
    char out[256];
    int len, isCap = 0;

    conf = dumbtts_TTSInit("en");
    if (!conf) {
        fprintf(stderr, "dumbtts_TTSInit(\"en\") returned NULL\n");
        return 1;
    }

    /* 1. Convert a wide character to speakable text (assert no error).
     * API contract: 0 = converted OK, >0 = buffer too small, <0 = error. */
    len = dumbtts_WCharString(conf, L'a', out, sizeof(out), 0, &isCap);
    if (len < 0) {
        fprintf(stderr, "dumbtts_WCharString('a') failed: %d\n", len);
        return 1;
    }
    if (!out[0]) {
        fprintf(stderr, "dumbtts_WCharString('a') returned empty output\n");
        return 1;
    }

    /* 2. Convert a UTF-8 string (assert no error, non-empty output). */
    memset(out, 0, sizeof(out));
    len = dumbtts_GetString(conf, "hello", out, sizeof(out), 1, "()[]", ".,!?;:");
    if (len < 0) {
        fprintf(stderr, "dumbtts_GetString(\"hello\") failed: %d\n", len);
        return 1;
    }
    if (!out[0]) {
        fprintf(stderr, "dumbtts_GetString returned empty output\n");
        return 1;
    }

    dumbtts_TTSFree(conf);
    printf("libdumbtts ok (%d)\n", len);
    return 0;
}