/* test_package/test.c — exercises the CLIPS 6.3 embedded C API.
 *
 * Builds a small expert system (deftemplate + defrule), asserts a fact,
 * runs the inference engine, and verifies:
 *   - the parser accepts valid / rejects invalid constructs (EnvBuild)
 *   - exactly one rule fires (EnvRun return value)
 *   - the rule's side-effect fact is in the fact list (EnvGetNextFact +
 *     EnvGetFactSlot slot query)
 *   - the embedded evaluation path works (EnvFunctionCall)
 *   - environment teardown works (DestroyEnvironment on a fresh env —
 *     upstream 6.30 hangs tearing down an env with pending activations)
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

    void *env = CreateEnvironment();
    CHECK(env != NULL, "CreateEnvironment returns an environment");

    /* EnvBuild parses exactly ONE construct per call (strngfun.c: it reads
     * "(", reads the construct type, parses that construct, returns) — no
     * looping over multiple constructs in one string. */
    CHECK(EnvBuild(env, "(deftemplate claim (slot content))") == 1,
        "EnvBuild defines the claim deftemplate");

    CHECK(EnvBuild(env, "(deftemplate result (slot value))") == 1,
        "EnvBuild defines the result deftemplate");

    CHECK(EnvBuild(env,
        "(defrule r-fire \"claim hello produces result ok\""
        "   (claim (content hello))"
        "   =>"
        "   (assert (result (value ok))))") == 1,
        "EnvBuild parses the defrule");

    CHECK(EnvBuild(env, "(defrule broken ( => )") == 0,
        "EnvBuild rejects invalid syntax");

    EnvReset(env);

    CHECK(EnvAssertString(env, "(claim (content hello))") != NULL,
        "EnvAssertString asserts the trigger fact");

    CHECK(EnvRun(env, -1) == 1,
        "EnvRun fires exactly one rule");

    /* Scan the fact list for the (result (value ok)) fact the rule asserted.
     * Only facts of the result template carry a "value" slot, so the slot
     * query doubles as a template check. */
    {
        void *factPtr;
        int found = 0;
        for (factPtr = EnvGetNextFact(env, NULL);
             factPtr != NULL;
             factPtr = EnvGetNextFact(env, factPtr)) {
            if (EnvGetFactSlot(env, factPtr, "value", &rv)) {
                if (GetpType(&rv) == SYMBOL &&
                    strcmp(ValueToString(GetpValue(&rv)), "ok") == 0) {
                    found = 1;
                }
            }
        }
        CHECK(found, "fact list contains (result (value ok)) after run");
    }

    /* Embedded evaluation path a host application would use.
     * EnvFunctionCall's return value follows CLIPS error convention:
     * TRUE (1) = error occurred, FALSE (0) = evaluated cleanly. */
    CHECK(EnvFunctionCall(env, "+", "2 3", &rv) == 0 &&
          GetpType(&rv) == INTEGER &&
          ValueToLong(GetpValue(&rv)) == 5,
        "EnvFunctionCall evaluates (+ 2 3) = 5");

    /* Upstream 6.30 limitation (characterized on device, 2026-09-08):
     * DestroyEnvironment spins forever when the agenda still holds
     * activations (fresh env destroys fine; env with a defined but
     * unactivated rule destroys fine; env with a pending or fired
     * activation hangs). The shipped clips CLI never destroys its
     * environment either (main.c: control does not return from
     * CommandLoop), so this matches real-world usage. Do NOT destroy
     * the exercised environment here; validate the teardown API on a
     * fresh environment instead. See notes.md for the A/B/C/D matrix. */
    {
        void *env2 = CreateEnvironment();
        CHECK(env2 != NULL && DestroyEnvironment(env2) == 1,
            "DestroyEnvironment tears down a fresh environment");
    }

    if (failures > 0) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("all clips test_package assertions passed\n");
    return 0;
}
