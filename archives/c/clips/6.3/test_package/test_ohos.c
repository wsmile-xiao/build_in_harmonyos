/* test_package/test_ohos.c — HarmonyOS-specific platform integration tests.
 *
 * These cover the two places where the clips build actually meets OHOS:
 *   1. the -DLINUX code path in core/sysdep.c — gentime() reaches
 *      clock_gettime/gettimeofday through musl on HarmonyOS. The engine's
 *      (time) function returns that value, so a plausible epoch timestamp
 *      proves the POSIX clock path works on this platform.
 *   2. CLIPS file I/O on the HarmonyOS user storage (HMDFS on devices):
 *      save-facts writes a facts file and load-facts restores it in a
 *      fresh environment — a full round trip through the filesystem the
 *      recipe's TMPDIR points at.
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
    char path[512], quoted[530];
    FILE *probe;
    long fsize;
    void *env, *env2, *factPtr;
    int found_hello = 0, found_world = 0;

    if (tmp == NULL || tmp[0] == '\0')
        tmp = ".";

    /* ── OHOS case 1: POSIX clock path (-DLINUX sysdep.c / musl) ── */
    env = CreateEnvironment();
    CHECK(env != NULL, "ohos: CreateEnvironment");

    CHECK(EnvFunctionCall(env, "time", "", &rv) == 0 &&
          GetpType(&rv) == FLOAT &&
          ValueToDouble(GetpValue(&rv)) > 1700000000.0,
        "ohos: (time) returns a plausible epoch via the LINUX-branch gentime (clock_gettime/gettimeofday on musl)");

    /* ── OHOS case 2: save-facts / load-facts round trip on user storage ── */
    EnvBuild(env, "(deftemplate claim (slot content))");
    CHECK(EnvAssertString(env, "(claim (content hello))") != NULL &&
          EnvAssertString(env, "(claim (content world))") != NULL,
        "ohos: two claim facts asserted before saving");

    snprintf(path, sizeof(path), "%s/ohos-facts.dat", tmp);
    snprintf(quoted, sizeof(quoted), "\"%s\"", path);
    CHECK(EnvFunctionCall(env, "save-facts", quoted, &rv) == 0,
        "ohos: save-facts writes the facts file (HMDFS user storage)");

    probe = fopen(path, "rb");
    if (probe != NULL) {
        fseek(probe, 0, SEEK_END);
        fsize = ftell(probe);
        fclose(probe);
    } else {
        fsize = -1;
    }
    CHECK(fsize > 0, "ohos: facts file exists and is non-empty");

    env2 = CreateEnvironment();
    EnvBuild(env2, "(deftemplate claim (slot content))");
    CHECK(EnvFunctionCall(env2, "load-facts", quoted, &rv) == 0,
        "ohos: load-facts restores the file into a fresh environment");

    for (factPtr = EnvGetNextFact(env2, NULL);
         factPtr != NULL;
         factPtr = EnvGetNextFact(env2, factPtr)) {
        if (EnvGetFactSlot(env2, factPtr, "content", &rv) &&
            GetpType(&rv) == SYMBOL) {
            const char *v = ValueToString(GetpValue(&rv));
            if (strcmp(v, "hello") == 0)
                found_hello = 1;
            if (strcmp(v, "world") == 0)
                found_world = 1;
        }
    }
    CHECK(found_hello && found_world,
        "ohos: both facts round-trip with correct slot values");

    if (failures > 0) {
        fprintf(stderr, "%d ohos-specific assertion(s) failed\n", failures);
        return 1;
    }
    printf("all clips ohos-specific assertions passed\n");
    return 0;
}
