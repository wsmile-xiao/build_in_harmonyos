/*
 * test.c — consumer smoke test for linenoise-ng v1.0.0.
 *
 * Uses ONLY the installed public header and linked library to verify a
 * third-party application can compile, link, call a public API and
 * observe its result: linenoiseHistorySetMaxLen / linenoiseHistoryAdd
 * return 1 on success, 0 on refusal.
 *
 * Regression coverage (patch 0002): the fixed memcpy offset in
 * linenoiseHistorySetMaxLen only runs when the history is NOT full and is
 * shrunk. We add several distinct lines, shrink maxlen (triggers the
 * fixed branch), then Save/Load — this exercises the NULL-deref crash
 * path that v1.0.0 hit (revert 0002 -> this test fails with Signal 11).
 */
#include <stdio.h>
#include "linenoise.h"

static int failures = 0;

static void check(int cond, const char *msg) {
    if (cond) {
        printf("  ok   : %s\n", msg);
    } else {
        printf("  FAIL : %s\n", msg);
        ++failures;
    }
}

int main(void) {
    const char *histfile = "./linenoise-ng-test-history.txt";

    /* 实质调用被测包公开 API（R34）：成功返回 1，失败返回 0 */
    if (linenoiseHistorySetMaxLen(100) != 1) {
        printf("FAIL: linenoiseHistorySetMaxLen\n");
        return 1;
    }
    if (linenoiseHistoryAdd("conan test line") != 1) {
        printf("FAIL: linenoiseHistoryAdd\n");
        return 1;
    }
    if (linenoiseHistoryAdd("conan test line") != 0) {
        printf("FAIL: duplicate must be refused\n");
        return 1;
    }

    /* ── Patch-0002 regression: shrink a NOT-full history then Save ── */
    remove(histfile);
    check(linenoiseHistoryAdd("alpha line") == 1, "linenoiseHistoryAdd('alpha line') == 1");
    check(linenoiseHistoryAdd("beta line") == 1, "linenoiseHistoryAdd('beta line') == 1");
    check(linenoiseHistoryAdd("gamma line") == 1, "linenoiseHistoryAdd('gamma line') == 1");
    /* historyLen=3 < historyMaxLen=100: shrink to 2 must copy last 2 filled
     * entries (tocopy=2, source offset history+1) — the 0002-fixed branch. */
    check(linenoiseHistorySetMaxLen(2) == 1, "linenoiseHistorySetMaxLen(2) shrink == 1");
    check(linenoiseHistorySave(histfile) == 0, "linenoiseHistorySave() == 0 (no NULL deref)");
    {
        FILE *fp = fopen(histfile, "rt");
        check(fp != NULL, "history file exists after shrink+save");
        if (fp != NULL) {
            char buf[256];
            int n = 0;
            while (fgets(buf, sizeof(buf), fp) != NULL) {
                ++n;
            }
            fclose(fp);
            /* kept entries are ["beta line","gamma line"] — both non-empty */
            check(n == 2, "shrunk history saved exactly 2 non-empty lines");
        }
        check(linenoiseHistoryLoad(histfile) == 0, "linenoiseHistoryLoad() round-trip == 0");
    }
    remove(histfile);

    if (failures != 0) {
        printf("FAIL: %d check(s) failed\n", failures);
        return 1;
    }
    printf("linenoise-ng v1.0.0 consumer API test: OK\n");
    return 0;
}