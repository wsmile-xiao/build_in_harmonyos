#include <curses.h>
#include <panel.h>

/* Minimal pkg-config linked consumer: forces panel and curses core symbols
 * so the -Wl,-t link trace must select the packaged static archives. */

int main(void) {
    SCREEN *screen;
    WINDOW *window;
    PANEL *panel;
    int code = 1;

    screen = newterm("xterm", stdout, stdin);
    if (screen == NULL) {
        return 2;
    }
    window = newwin(1, 8, 0, 0);
    panel = window == NULL ? (PANEL *)0 : new_panel(window);
    if (panel != (PANEL *)0) {
        update_panels();
        if (doupdate() == OK && del_panel(panel) == OK) {
            code = 0;
        }
    }
    endwin();
    delscreen(screen);
    if (window != NULL) {
        delwin(window);
    }
    return code;
}
