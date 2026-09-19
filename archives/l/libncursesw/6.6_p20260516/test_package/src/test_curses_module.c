#include <curses.h>
#include <term.h>

#include <stdio.h>
#include <string.h>
#include <wchar.h>

static char emitted[16];
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
    cchar_t cell;
    wchar_t actual[8] = {0};
    const wchar_t expected[] = L"\u00e9";
    attr_t attrs = 0;
    short pair = 0;
    FILE *output;
    FILE *input;
    SCREEN *screen;
    WINDOW *window;

    if (argc != 3) {
        return fail("expected output and input paths");
    }
    if (strstr(curses_version(), "6.6") == NULL) {
        return fail("unexpected curses version");
    }
    if (setcchar(&cell, expected, A_BOLD, 0, NULL) != OK ||
        getcchar(&cell, actual, &attrs, &pair, NULL) != OK ||
        wcscmp(actual, expected) != 0 || attrs != A_BOLD) {
        return fail("wide-character round trip");
    }
    if (tputs("abc", 1, collect_character) == ERR || strcmp(emitted, "abc") != 0) {
        return fail("tputs callback contract");
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
    if (window == NULL || waddstr(window, "ncurses 6.6") == ERR ||
        wrefresh(window) == ERR) {
        return fail("window update");
    }
    delwin(window);
    endwin();
    delscreen(screen);
    fclose(input);
    fclose(output);

    puts("UPSTREAM_CONSUMER_CORE=6/6");
    return 0;
}
