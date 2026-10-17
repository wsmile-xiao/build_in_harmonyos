/*
 * test_zlog_ohos.c — HarmonyOS-specific functional test for zlog 1.2.18.
 *
 * Verifies real OHOS-platform behavior of the adapted library, not a
 * print-only shell:
 *   1. zlog_init_from_string + rule writing to a FILE in the current
 *      working directory (on OHOS /tmp is read-only; the file output path
 *      must be a writable workspace path — this is the OHOS adaptation
 *      path exercised by the recipe, which never relies on /tmp).
 *   2. Level filtering: an INFO-level rule with a DEBUG-level category
 *      threshold must drop DEBUG records (actual behavior check).
 *   3. File content round-trip: read back the written log file and assert
 *      the expected formatted record exists (verifies real disk output,
 *      not just stdout echo).
 *   4. zlog_fini flush + dzlog default-category flow.
 *
 * Runs on aarch64-linux-ohos; exit 0 = all assertions pass.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "zlog.h"

static int rc_global = 0;
#define CHECK(cond, msg) \
    do { if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); rc_global = 1; } } while (0)

int main(int argc, char **argv) {
    char conf[512];
    char logpath[256];
    FILE *fp;
    char line[1024];
    int found = 0;
    zlog_category_t *zc;
    (void)argc; (void)argv;

    /* CWD-relative file output: on OHOS /tmp is read-only, so the recipe's
       file-output path must resolve inside the writable workspace. */
    snprintf(logpath, sizeof(logpath), "ohos-test.log");
    unlink(logpath);

    snprintf(conf, sizeof(conf),
        "[formats]\n"
        "simple = \"%%V %%m%%n\"\n"
        "[rules]\n"
        "ohos_cat.INFO \"%s\";simple\n",
        logpath);

    CHECK(zlog_init_from_string(conf) == 0, "zlog_init_from_string");
    zc = zlog_get_category("ohos_cat");
    CHECK(zc != NULL, "zlog_get_category(ohos_cat)");

    zlog_info(zc, "ohos-write-1");
    zlog_debug(zc, "ohos-debug-must-drop"); /* below default INFO threshold */
    zlog_fini();

    /* Assert the file was really created in CWD and contains the INFO
       record but NOT the DEBUG record (level filtering on OHOS). */
    fp = fopen(logpath, "r");
    CHECK(fp != NULL, "log file not created in CWD (OHOS writable path)");
    if (fp) {
        while (fgets(line, sizeof(line), fp)) {
            if (strstr(line, "ohos-write-1")) found++;
            if (strstr(line, "ohos-debug-must-drop")) rc_global = 1; /* DEBUG leaked */
        }
        fclose(fp);
    }
    CHECK(found == 1, "expected INFO record missing from file");

    /* dzlog default-category flow: dzlog_init takes a config FILE path;
       write the config into CWD (writable on OHOS, unlike /tmp). */
    {
        char confpath[256];
        FILE *cf;
        snprintf(confpath, sizeof(confpath), "ohos-test.conf");
        cf = fopen(confpath, "w");
        CHECK(cf != NULL, "cannot write config to CWD (OHOS writable path)");
        if (cf) {
            fprintf(cf, "%s", conf);
            fclose(cf);
        }
        CHECK(dzlog_init(confpath, "default") == 0, "dzlog_init failed");
        dzlog_info("ohos-dzlog-write");
        zlog_fini();
        unlink(confpath);
    }

    if (rc_global == 0) {
        printf("test_zlog_ohos:OK\n");
    }
    return rc_global;
}
