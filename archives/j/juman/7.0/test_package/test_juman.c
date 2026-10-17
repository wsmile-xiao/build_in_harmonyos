/* Consumer test for the packaged juman library.
 *
 * It plays the role of an application that links libjuman and drives its
 * public C API (juman.h): the character helpers and the string utilities that
 * the library exports.  The full morphological analysis path needs the
 * dictionary plus the client/server protocol, so it is covered by the packaged
 * `juman` command instead.
 */
#include <stdio.h>
#include <string.h>

#include <juman.h>

static int checks;
static int failures;

static void check(int condition, const char *name)
{
    checks++;
    if (condition) {
        printf("CHECK-OK: %s\n", name);
    } else {
        failures++;
        printf("CHECK-FAIL: %s\n", name);
    }
}

int main(void)
{
    U_CHAR buffer[32];
    U_CHAR *sample = (U_CHAR *)"juman";

    check(my_strlen(sample) == 5, "my_strlen() counts the characters of a string");

    my_strcpy(buffer, sample);
    check(my_strcmp(buffer, sample) == 0, "my_strcpy()+my_strcmp() round-trip");
    check(my_strcmp(buffer, (U_CHAR *)"jumam") != 0,
          "my_strcmp() distinguishes different strings");

    check(lower('A') == 'a', "lower() folds an upper case letter");
    check(upper('b') == 'B', "upper() folds a lower case letter");

    printf("JUMAN_CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
    if (failures == 0) {
        printf("JUMAN_CONSUMER_OK\n");
    }
    return failures == 0 ? 0 : 1;
}
