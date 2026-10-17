/*
 * L1 smoke test — links against packaged static ncursesw libraries and
 * exercises real ncurses API calls (terminfo + tputs + curses_version).
 */
#include <curses.h>
#include <term.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    /* Verify the linked library reports the expected version. */
    const char *ver = curses_version();
    if (ver == NULL || strstr(ver, "6.4") == NULL) {
        fprintf(stderr, "FAIL: unexpected curses version: %s\n", ver ? ver : "(null)");
        return 1;
    }

    /* Exercise terminfo: setupterm must succeed for a common terminal. */
    int errret = 0;
    if (setupterm("xterm", fileno(stdout), &errret) != OK) {
        fprintf(stderr, "FAIL: setupterm failed (errret=%d)\n", errret);
        return 1;
    }

    /* Exercise tputs with a simple capability. */
    if (tputs(clear_screen, 1, putchar) == ERR) {
        fprintf(stderr, "FAIL: tputs clear_screen failed\n");
        return 1;
    }

    printf("OK: ncurses 6.4 smoke test passed (version=%s)\n", ver);
    return 0;
}
