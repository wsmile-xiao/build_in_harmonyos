/* test_package/test_consumer.c — consumer-usage test: an application that
 * keeps its business rules in an external .clp file and loads them at
 * runtime through the embedded API.
 *
 * Flow (the way a host application would embed CLIPS):
 *   1. write the rules file next to the test (TMPDIR or cwd)
 *   2. CreateEnvironment
 *   3. EnvBatchStar(env, "<rules.clp>") — load deftemplate/deffunction/
 *      defrule from the FILE (returns FALSE only when the file can't be
 *      opened; command errors are reported but still return TRUE — the
 *      downstream asserts catch semantic failures)
 *   4. assert an order fact, run the engine — the rule loaded from the
 *      file must fire
 *   5. EnvFunctionCall the deffunction loaded from the file and check
 *      its return value
 */
#include <stdio.h>
#include <string.h>

#include "clips.h"

static int failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            printf("PASS: %s\n", msg);                       \
        } else {                                             \
            failures++;                                      \
            fprintf(stderr, "FAIL: %s\n", msg);              \
        }                                                    \
    } while (0)

int main(void)
{
    DATA_OBJECT rv;
    const char *tmp = getenv("TMPDIR");
    char path[512];
    FILE *fh;
    void *env;
    long long fired;

    if (tmp == NULL || tmp[0] == '\0')
        tmp = ".";

    /* 1) The rules file an application would ship. */
    snprintf(path, sizeof(path), "%s/consumer_rules.clp", tmp);
    fh = fopen(path, "w");
    if (fh == NULL) {
        fprintf(stderr, "FAIL: cannot write %s\n", path);
        return 1;
    }
    fputs("(deftemplate order (slot quantity) (slot price))\n"
          "(deftemplate result (slot flag))\n"
          "(deffunction shipping-cost (?q ?p) (+ (* ?q ?p) 5))\n"
          "(defrule large-order \"10+ unit orders get priority handling\"\n"
          "   (order (quantity ?q &: (>= ?q 10)))\n"
          "   =>\n"
          "   (assert (result (flag priority))))\n",
          fh);
    fclose(fh);

    env = CreateEnvironment();
    CHECK(env != NULL, "consumer: CreateEnvironment");

    CHECK(EnvBatchStar(env, "/nonexistent-clips-file.clp") == 0,
        "consumer: EnvBatchStar reports a missing file");

    CHECK(EnvBatchStar(env, path) == 1,
        "consumer: EnvBatchStar loads the external rules file");

    CHECK(EnvAssertString(env, "(order (quantity 10) (price 3))") != NULL,
        "consumer: EnvAssertString asserts the order fact");

    fired = EnvRun(env, -1);
    CHECK(fired == 1, "consumer: rule loaded from file fires exactly once");

    /* shipping-cost(3, 10) = 3*10 + 5 = 35; TRUE means error in the CLIPS
     * convention, FALSE means evaluated cleanly. */
    CHECK(EnvFunctionCall(env, "shipping-cost", "3 10", &rv) == 0 &&
          GetpType(&rv) == INTEGER &&
          ValueToLong(GetpValue(&rv)) == 35,
        "consumer: deffunction loaded from file computes shipping-cost = 35");

    if (failures > 0) {
        fprintf(stderr, "%d consumer assertion(s) failed\n", failures);
        return 1;
    }
    printf("all clips consumer assertions passed\n");
    return 0;
}
