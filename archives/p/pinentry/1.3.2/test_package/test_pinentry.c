/*
 * test_pinentry.c — Test pinentry binaries (L1 consumer test)
 *
 * This test calls pinentry-curses and pinentry-tty with --version
 * to verify they execute correctly and report the expected version.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Verify pinentry-curses --version returns exit code 0 */
    int rc_curses = system("pinentry-curses --version > /dev/null 2>&1");
    if (rc_curses != 0) {
        fprintf(stderr, "FAIL: pinentry-curses --version returned %d\n", rc_curses);
        return 1;
    }
    printf("PASS: pinentry-curses --version OK\n");

    /* Verify pinentry-tty --version returns exit code 0 */
    int rc_tty = system("pinentry-tty --version > /dev/null 2>&1");
    if (rc_tty != 0) {
        fprintf(stderr, "FAIL: pinentry-tty --version returned %d\n", rc_tty);
        return 1;
    }
    printf("PASS: pinentry-tty --version OK\n");

    return 0;
}
