#include <stdio.h>
#include <string.h>
#include <crack.h>

/* HarmonyOS consumer test: exercise the full FascistCheckUser engine path
 * with an explicit user (bypasses getpwuid, which has no passwd entry for
 * the app uid on HarmonyOS). Covers three behaviors:
 *   1. pre-rule rejection (too-short password)
 *   2. dictionary-engine rejection (word packed into the test dictionary)
 *   3. acceptance (strong password not in dictionary)
 */
static int failures = 0;

static void expect_reject(const char *pw, const char *dict, const char *label)
{
    const char *msg = FascistCheckUser(pw, dict, "testuser", "Test User");
    if (msg != NULL && msg[0] != '\0') {
        printf("PASS %s: '%s' rejected (%s)\n", label, pw, msg);
    } else {
        printf("FAIL %s: '%s' unexpectedly accepted\n", label, pw);
        failures++;
    }
}

static void expect_accept(const char *pw, const char *dict, const char *label)
{
    const char *msg = FascistCheckUser(pw, dict, "testuser", "Test User");
    if (msg == NULL || msg[0] == '\0') {
        printf("PASS %s: '%s' accepted\n", label, pw);
    } else {
        printf("FAIL %s: '%s' unexpectedly rejected (%s)\n", label, pw, msg);
        failures++;
    }
}

int main(int argc, char **argv)
{
    const char *dict;

    if (argc < 2) {
        printf("FAIL: usage: %s <dictionary-prefix>\n", argv[0]);
        return 1;
    }
    dict = argv[1];

    expect_reject("abc", dict, "too-short-rule");
    expect_reject("orchid", dict, "dictionary-word");
    expect_accept("G7z#kQ9!vX2m", dict, "strong-password");

    if (failures != 0) {
        printf("cracklib2 test: %d failure(s)\n", failures);
        return 1;
    }
    printf("cracklib2 test: 3/3 passed\n");
    printf("test cracklib2 2.9.6: OK (FascistCheckUser engine: rules + dictionary + accept)\n");
    return 0;
}
