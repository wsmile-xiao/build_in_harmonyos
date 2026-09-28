/* Consumer test for libexplain/1.4.d001: exercises the explanation API
 * on a deliberately failing open(2), asserting the explanation mentions
 * the errno text.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libexplain/open.h>

int main(void) {
    int failures = 0;

    errno = 0;
    int fd = open("/nonexistent/definitely-not-there", O_RDONLY);
    if (fd >= 0) {
        printf("FAIL: open unexpectedly succeeded\n");
        failures++;
    }
    const char *msg = explain_open("/nonexistent/definitely-not-there",
                                   O_RDONLY, 0);
    printf("explanation: %.200s\n", msg ? msg : "(null)");
    if (!msg || !strstr(msg, "No such file or directory")) {
        printf("FAIL: explanation lacks errno text\n");
        failures++;
    } else {
        printf("ok: explanation contains errno text\n");
    }
    /* a good explanation adds the failing operation and path context */
    if (msg && strstr(msg, "open")) {
        printf("ok: explanation names the syscall\n");
    } else {
        printf("FAIL: explanation lacks syscall name\n");
        failures++;
    }

    printf("failed=%d\n", failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
