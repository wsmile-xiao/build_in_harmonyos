#include <curses.h>
#include <term.h>

#include <stddef.h>

#if defined(NCURSES_METADATA_FORM)
#include <form.h>
static FIELD *(*volatile component_api)(int, int, int, int, int, int) =
    new_field;
#elif defined(NCURSES_METADATA_MENU)
#include <menu.h>
static ITEM *(*volatile component_api)(const char *, const char *) = new_item;
#elif defined(NCURSES_METADATA_PANEL)
#include <panel.h>
static PANEL *(*volatile component_api)(WINDOW *) = new_panel;
#endif

static int discard_character(int value) {
    return value;
}

int main(void) {
    int error = 0;
    const char *clear;

#if defined(NCURSES_METADATA_FORM) || defined(NCURSES_METADATA_MENU) || \
    defined(NCURSES_METADATA_PANEL)
    if (component_api == NULL) {
        return 4;
    }
#endif

    if (setupterm("xterm", 1, &error) != OK || error != 1) {
        return 1;
    }
    clear = tigetstr("clear");
    if (clear == NULL || clear == (const char *)-1) {
        return 2;
    }
    return tputs(clear, 1, discard_character) == ERR ? 3 : 0;
}
