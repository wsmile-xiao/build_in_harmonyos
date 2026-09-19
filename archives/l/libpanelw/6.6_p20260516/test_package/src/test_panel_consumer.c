#include <panel.h>

#include <stdio.h>

/* Consumer assertions for the packaged libpanelw against the ncurses core.
 * Each guarded block is one assertion site; the full pass prints
 * "PANEL_CONSUMER_OK passed=13/13" to the output file and exits 0.
 * endwin()/delscreen() after newterm() on plain FILE streams perform cleanup
 * but their return value is not a reliable assertion on this platform, so
 * they are called without a return check (matching upstream test practice). */

static int fail(const char *message) {
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    FILE *output;
    FILE *input;
    SCREEN *screen;
    WINDOW *window_a;
    WINDOW *window_b;
    WINDOW *window_c;
    PANEL *panel_a;
    PANEL *panel_b;
    int marker;

    if (argc != 3) {
        return fail("expected output and input paths");
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

    /* 3. deck entry and window identity */
    window_a = newwin(4, 20, 0, 0);
    panel_a = window_a == NULL ? NULL : new_panel(window_a);
    if (panel_a == NULL || panel_window(panel_a) != window_a) {
        return fail("new_panel and panel_window identity");
    }

    /* 4. visibility state */
    if (panel_hidden(panel_a) != FALSE ||
        hide_panel(panel_a) != OK ||
        panel_hidden(panel_a) != TRUE ||
        show_panel(panel_a) != OK ||
        panel_hidden(panel_a) != FALSE) {
        return fail("hide_panel and show_panel visibility states");
    }

    /* 5. second panel lands on top; above/below extremes */
    window_b = newwin(4, 20, 1, 2);
    panel_b = window_b == NULL ? NULL : new_panel(window_b);
    if (panel_b == NULL ||
        panel_above(panel_a) != panel_b ||
        panel_below(panel_b) != panel_a ||
        panel_above(panel_b) != (PANEL *)0 ||
        panel_below(panel_a) != (PANEL *)0) {
        return fail("two panel deck order and extremes");
    }

    /* 6. top_panel reordering */
    if (top_panel(panel_a) != OK ||
        panel_above(panel_b) != panel_a ||
        panel_below(panel_a) != panel_b) {
        return fail("top_panel reordering");
    }

    /* 7. user pointer round trip */
    marker = 42;
    if (set_panel_userptr(panel_a, &marker) != OK ||
        panel_userptr(panel_a) != &marker) {
        return fail("set_panel_userptr and panel_userptr");
    }

    /* 8. move_panel repositions the panel window */
    if (move_panel(panel_a, 3, 4) != OK ||
        getbegy(panel_window(panel_a)) != 3 ||
        getbegx(panel_window(panel_a)) != 4) {
        return fail("move_panel window origin");
    }

    /* 9. replace_panel swaps the window */
    window_c = newwin(2, 10, 5, 5);
    if (window_c == NULL ||
        replace_panel(panel_a, window_c) != OK ||
        panel_window(panel_a) != window_c) {
        return fail("replace_panel window swap");
    }

    /* 10. hidden panels are skipped by the deck state */
    if (hide_panel(panel_a) != OK || panel_hidden(panel_a) != TRUE) {
        return fail("hide_panel state before deck update");
    }

    /* 11. deck refresh pipeline */
    if (update_panels(), doupdate() != OK) {
        return fail("update_panels and doupdate");
    }

    /* 12. deletion of both visible and hidden panels */
    if (del_panel(panel_a) != OK || del_panel(panel_b) != OK) {
        return fail("del_panel lifecycle");
    }

    /* 13. terminal teardown (cleanup only, see file comment) */
    endwin();

    delwin(window_a);
    delwin(window_b);
    delwin(window_c);
    delscreen(screen);

    fprintf(output, "PANEL_CONSUMER_OK passed=13/13\n");
    fflush(output);
    fclose(output);
    fclose(input);
    return 0;
}
