/*
 * ohos_test.c — HarmonyOS-specific test for linenoise-ng v1.0.0.
 *
 * Exercises the public API (include/linenoise.h only) in a
 * non-interactive way that is valid on HarmonyOS:
 *   - history add / duplicate rejection / empty-line handling
 *   - history max-len trimming (regression: linenoise-ng v1.0.0
 *     copied from the wrong offset on shrink, NULL-deref on save)
 *   - history save -> load round trip (observable file content)
 *   - history free and version macros
 *
 * This test deliberately avoids linenoise() (which requires a real
 * PTY), so it can run headless on OHOS CI.
 */
#include "linenoise.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
static int checks = 0;

static void check(int cond, const char *msg) {
    ++checks;
    if (cond) {
        printf("  ok   : %s\n", msg);
    } else {
        printf("  FAIL : %s\n", msg);
        ++failures;
    }
}

static int count_lines(const char *path) {
    FILE *fp = fopen(path, "rt");
    int n = 0;
    char buf[4096];
    if (fp == NULL) {
        return -1;
    }
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        ++n;
    }
    fclose(fp);
    return n;
}

int main(void) {
    const char *histfile = "./linenoise-ng-ohos-test-history.txt";
    FILE *fp;
    char first[4096] = {0};

    remove(histfile);

    printf("linenoise-ng OHOS test: header version = %s\n", LINENOISE_VERSION);
    check(strcmp(LINENOISE_VERSION, "1.0.0") == 0, "LINENOISE_VERSION macro == 1.0.0");
    check(LINENOISE_VERSION_MAJOR >= 1, "LINENOISE_VERSION_MAJOR >= 1");

    /* History add works with the default history max len. */
    check(linenoiseHistoryAdd("first line") == 1, "linenoiseHistoryAdd('first line') == 1");
    /* Immediate duplicate is refused (returns 0). */
    check(linenoiseHistoryAdd("first line") == 0, "immediate duplicate refused (0)");
    check(linenoiseHistoryAdd("second line") == 1, "linenoiseHistoryAdd('second line') == 1");
    /* Embedded newline is folded to a space when stored. */
    check(linenoiseHistoryAdd("multi\nline") == 1, "embedded newline accepted");
    check(linenoiseHistoryAdd("") == 1, "empty line accepted by history API");

    /* Max-len handling: SetMaxLen(0) is rejected. */
    check(linenoiseHistorySetMaxLen(0) == 0, "linenoiseHistorySetMaxLen(0) rejected");

    /* Shrink max len to 2 -> keeps last 2 filled entries and Save works
     * (regression test for the v1.0.0 NULL-deref on shrink). */
    check(linenoiseHistorySetMaxLen(2) == 1, "shrink maxlen to 2 == 1");
    check(linenoiseHistorySave(histfile) == 0, "linenoiseHistorySave() == 0");

    /* After shrink to 2, filled history is ["multi line", ""]; save skips
     * empty entries, so exactly 1 line "multi line" must be on disk. */
    check(count_lines(histfile) == 1, "history file has exactly 1 line after shrink");
    fp = fopen(histfile, "rt");
    check(fp != NULL, "history file exists after save");
    if (fp != NULL) {
        if (fgets(first, sizeof(first), fp) != NULL) {
            size_t len = strlen(first);
            if (len > 0 && first[len - 1] == '\n') {
                first[len - 1] = '\0';
            }
        }
        fclose(fp);
        check(strcmp(first, "multi line") == 0,
              "last kept entry is 'multi line' (newline space-folded)");
    }

    /* Round trip: load into fresh state and re-save, content must match. */
    linenoiseHistoryFree();
    check(linenoiseHistoryLoad(histfile) == 0, "linenoiseHistoryLoad() == 0");
    check(count_lines(histfile) == 1, "re-save after load keeps 1 line");

    linenoiseHistoryFree();
    remove(histfile);

    printf("\nRESULT: %d/%d checks passed\n", checks - failures, checks);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
