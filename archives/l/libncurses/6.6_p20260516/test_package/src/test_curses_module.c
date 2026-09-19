#include <curses.h>
#include <term.h>

#include <stdio.h>
#include <string.h>

#define SEQUENCE_SIZE 16

static char emitted[SEQUENCE_SIZE];
static size_t emitted_length;

static int collect_character(int value) {
    if (emitted_length + 1 >= sizeof(emitted)) {
        return ERR;
    }
    emitted[emitted_length++] = (char)value;
    emitted[emitted_length] = '\0';
    return OK;
}

static int fail(const char *message) {
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    FILE *output;
    FILE *input;
    FILE *roundtrip;
    SCREEN *screen;
    WINDOW *window;
    chtype stored;
    int error = 0;

    if (argc != 3) {
        return fail("expected output and input paths");
    }
    if (strstr(curses_version(), "6.6") == NULL) {
        return fail("unexpected curses version");
    }
    if (tputs("abc", 1, collect_character) == ERR || strcmp(emitted, "abc") != 0) {
        return fail("tputs callback contract");
    }

    /* Narrow ABI: setupterm + terminfo lookup must resolve in this build. */
    if (setupterm("xterm", 1, &error) != OK || error != 1) {
        return fail("setupterm with packaged terminfo");
    }
    if (tgetstr("cm", NULL) == NULL || tigetnum("colors") < 0) {
        return fail("terminfo capability lookup");
    }

    output = fopen(argv[1], "w+");
    input = fopen(argv[2], "r");
    if (output == NULL || input == NULL) {
        return fail("open terminal streams");
    }
    screen = newterm("xterm", output, input);
    if (screen == NULL) {
        return fail("newterm with packaged terminfo");
    }
    set_term(screen);
    window = newwin(2, 16, 0, 0);
    if (window == NULL || waddstr(window, "libncurses 6.6") == ERR) {
        return fail("window update");
    }

    /* 8-bit chtype cells are the contract of this package. */
    stored = A_REVERSE | (chtype)'n';
    if (mvwaddch(window, 1, 0, stored) == ERR || wrefresh(window) == ERR) {
        return fail("narrow chtype round trip");
    }
    if ((mvwinch(window, 1, 0) & A_CHARTEXT) != (chtype)'n') {
        return fail("narrow chtype cell extraction");
    }
    delwin(window);
    endwin();
    delscreen(screen);
    fclose(input);
    fclose(output);

    puts("UPSTREAM_CONSUMER_CORE=7/7");
    return 0;
}
